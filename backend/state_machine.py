# state_machine.py
import asyncio
import json
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace as _SNS

from playwright_driver import playwright_driver
import logging
import os

# ============== Paths & Data dirs ==============
DATA_DIR = Path("/app/data")
SESS_DIR = DATA_DIR / "sessions"
SESS_DIR.mkdir(parents=True, exist_ok=True)

# ============== Auto-advance Gates Configuration ==============
AUTO_ADVANCE = os.getenv("AUTO_ADVANCE_GATES", "0").lower() in ("1","true","yes")
AUTO_ADVANCE_TIMEOUT = float(os.getenv("AUTO_ADVANCE_TIMEOUT","1.0"))

# ============== In-memory state ==============
# _state: trạng thái nội bộ (dict nhẹ)
_state = {
    "session_id": None,
    "status": "idle",  # idle | running | done | error | cancelled
    "step": None,
    "turn": 0,
    "max_turns": 6,
    "product_url": None,
    "opener_text": None,
    "last_error": None,
    "reply": None,
    "started_at": None,
    "finished_at": None,
}
_lock = asyncio.Lock()

logger = logging.getLogger(__name__)

# === Manual gates so FE/operator can confirm before next step ===
_gates = {}  # name -> asyncio.Event

def _get_gate(name: str):
    ev = _gates.get(name)
    if not ev:
        ev = asyncio.Event()
        _gates[name] = ev
    return ev

async def _wait_gate(name: str, timeout: float | None = None):
    ev = _get_gate(name)
    if AUTO_ADVANCE:
        try:
            await asyncio.wait_for(ev.wait(), timeout=AUTO_ADVANCE_TIMEOUT)
        except asyncio.TimeoutError:
            logger.info(f"[GATE] Auto-advance '{name}' after {AUTO_ADVANCE_TIMEOUT}s")
        return
    if timeout:
        await asyncio.wait_for(ev.wait(), timeout=timeout)
    else:
        await ev.wait()

def open_gate(name: str):
    _get_gate(name).set()

def reset_gate(name: str):
    ev = _get_gate(name)
    if ev.is_set():
        _gates[name] = asyncio.Event()

# current_session_obj: đối tượng *để app.py truy cập như thuộc tính*
# (app.py gọi: state_machine.current_session.id / .current_state ...)
current_session_obj = _SNS(
    id=None,
    status="idle",
    current_state=None,   # alias của _state["step"]
    turn=0,
    max_turns=6,
    product_url=None,
    opener_text=None,
    last_error=None,
    reply=None,
    started_at=None,
    finished_at=None,
    session_dir=None,
)

def _new_session_id() -> str:
    return f"session_{int(datetime.now().timestamp())}"

def _sync_current_session_obj():
    """Đồng bộ _state -> current_session_obj để app.py dùng dạng thuộc tính."""
    sid = _state.get("session_id")
    session_dir = str((SESS_DIR / sid).resolve()) if sid else None
    current_session_obj.id = sid
    current_session_obj.status = _state.get("status")
    current_session_obj.current_state = _state.get("step")
    current_session_obj.turn = _state.get("turn")
    current_session_obj.max_turns = _state.get("max_turns")
    current_session_obj.product_url = _state.get("product_url")
    current_session_obj.opener_text = _state.get("opener_text")
    current_session_obj.last_error = _state.get("last_error")
    current_session_obj.reply = _state.get("reply")
    current_session_obj.started_at = _state.get("started_at")
    current_session_obj.finished_at = _state.get("finished_at")
    current_session_obj.session_dir = session_dir

def _save_session_snapshot():
    sid = _state.get("session_id")
    if not sid:
        return
    out_dir = SESS_DIR / sid
    out_dir.mkdir(parents=True, exist_ok=True)
    snap = {k: v for k, v in _state.items() if not k.startswith("_")}
    with open(out_dir / "status.json", "w", encoding="utf-8") as f:
        json.dump(snap, f, ensure_ascii=False, indent=2)
    _sync_current_session_obj()  # luôn đồng bộ sau mỗi lần lưu

# ============== Internal steps ==============
async def _s0_ensure_login(page):
    _state["step"] = "S0_ENSURE_LOGIN_VIA_TAOBAO"
    _save_session_snapshot()
    await playwright_driver.ensure_login_via_taobao(page)

async def _s1_open_product_and_open_chat(page, product_url: str):
    _state["step"] = "S1_OPEN_PRODUCT_AND_OPEN_CHAT"
    _save_session_snapshot()
    await playwright_driver.open_chat_from_product_canonical(page, product_url)

    # Chờ thấy ô chat trước khi sang S2 để tránh "No chat input found"
    await playwright_driver.wait_for_chat_ready(page, timeout_s=25)

async def _s2_send_opener(page, opener_text: str):
    _state["step"] = "S2_SEND_OPENER"
    _save_session_snapshot()
    await playwright_driver.send_on_chat_precise_canonical(page, opener_text)

async def _s3_wait_reply(page):
    """
    Wait for supplier reply and return text.
    This function uses the enhanced DOM-based detection with message counting.
    """
    _state["step"] = "S3_WAIT_SUPPLIER_REPLY"
    _save_session_snapshot()

    # Use the new enhanced supplier reply detection
    reply_text = await playwright_driver.wait_for_supplier_reply_canonical(page, timeout_s=180)

    # Store reply in both old and new formats for backward compatibility
    _state["reply"] = {"new_messages": [reply_text], "supplier_replied": True}
    _state["supplier_reply"] = reply_text
    _save_session_snapshot()

    return reply_text

# ============== Public API expected by app.py ==============
async def start(product_url: str, opener_text: str, max_turns: int = 6, style: str = "Aggressive"):
    """Bắt đầu 1 phiên thương lượng (one-shot)."""
    logger.info(f"[STATE] Starting negotiation - Product: {product_url}, Style: {style}")

    async with _lock:
        if _state["status"] == "running":
            logger.warning("[STATE] Another session is already running")
            raise RuntimeError("A session is already running")

        # init state
        _state.update({
            "session_id": _new_session_id(),
            "status": "running",
            "step": "INIT",
            "turn": 0,
            "max_turns": int(max_turns or 6),
            "product_url": product_url,
            "opener_text": opener_text,
            "style": style,  # Lưu style vào state
            "last_error": None,
            "reply": None,
            "started_at": datetime.utcnow().isoformat() + "Z",
            "finished_at": None,
        })
        (SESS_DIR / _state["session_id"]).mkdir(parents=True, exist_ok=True)
        _save_session_snapshot()

    # ngoài lock để tránh block /status
    try:
        # 1) Get or create managed page
        _state["step"] = "LAUNCH_BROWSER"
        _save_session_snapshot()

        # Get managed page with auto-recovery
        try:
            page = await playwright_driver.get_or_new_page()
            _state["_page"] = page
            _save_session_snapshot()
        except Exception as e:
            logger.error(f"[STATE] Failed to get managed page: {e}")
            raise

        # 2) Ensure login with page lifecycle management
        # Check page status before proceeding
        try:
            if not page or page.is_closed():
                logger.warning("[STATE] Page closed, reopening...")
                page = await playwright_driver.reopen_page()
                _state["_page"] = page
                _save_session_snapshot()
        except Exception as e:
            logger.error(f"[STATE] Page check failed: {e}")
            page = await playwright_driver.reopen_page()
            _state["_page"] = page
            _save_session_snapshot()

        # 2) Ensure login with new flow: login page first, then product
        offer_url = playwright_driver.normalize_1688_product_url(product_url)
        logger.info(f"[STATE] Starting refined login process for product: {offer_url}")

        res = await playwright_driver.ensure_login_via_taobao(
            page,
            product_url=offer_url,
            timeout_login=120_000  # 120 seconds for login
        )
        logger.info(f"[STATE] Login result: {res}")

        # Handle structured response from new login flow
        ok = bool(res.get("ok"))
        reason = res.get("reason")
        error_type = res.get("type")

        if not ok:
            # Handle specific error types with clear user messages
            if error_type == "login_timeout":
                error_msg = f"Login timeout: {reason if reason else 'User did not complete login in time'}"
                logger.error(f"[STATE] Login timeout: {reason if reason else 'User did not complete login in time'}")
                # Emit specific timeout error message via WebSocket
                try:
                    from app import manager
                    import json
                    await manager.broadcast(json.dumps({
                        "message": "⏰ User did not complete login in time. Please log in in the browser window and press Retry.",
                        "phase": "blocked",
                        "need_user_action": True,
                        "error_type": "login_timeout"
                    }))
                except Exception:
                    pass
                raise RuntimeError(f"Login not settled: {reason if reason else 'User did not complete login in time'}")
            elif error_type == "proxy_tunnel_failed":
                error_msg = f"Proxy tunnel failed: {reason if reason else 'Unable to reach product URL through proxy'}"
                logger.error(f"[STATE] Proxy tunnel failed: {reason if reason else 'Unknown reason'}")
                # Emit specific error message via WebSocket
                try:
                    from app import manager
                    import json
                    await manager.broadcast(json.dumps({
                        "message": "🚫 Proxy line cannot open the product page (detail.1688.com). Please change to another proxy or try again later.",
                        "phase": "blocked",
                        "need_user_action": True,
                        "error_type": "proxy_tunnel_failed"
                    }))
                except Exception:
                    pass
                raise RuntimeError(f"Login not settled: proxy tunnel failed - {reason if reason else 'Please change proxy line or disable proxy'}")
            else:
                error_msg = f"Login failed{': '+reason if reason else ''}"
                logger.error(f"[STATE] Login failed: {reason if reason else 'Unknown reason'}")
                # Emit generic login error via WebSocket
                try:
                    from app import manager
                    import json
                    await manager.broadcast(json.dumps({
                        "message": "⚠️ Login process failed. Please complete login in the browser window and press Retry.",
                        "phase": "blocked",
                        "need_user_action": True,
                        "error_type": "login_failed"
                    }))
                except Exception:
                    pass
                raise RuntimeError(f"Login not settled: {reason if reason else 'Unknown reason'}")

        logger.info(f"[STATE] Refined login flow completed successfully for product: {offer_url}")

        # Gate sau khi login xong
        _state["step"] = "S0_DONE"
        _save_session_snapshot()
        reset_gate("CONFIRM_AFTER_LOGIN")       # yêu cầu xác nhận
        # Chờ xác nhận từ FE hoặc auto-timeout (120s)
        await _wait_gate("CONFIRM_AFTER_LOGIN", timeout=120)

        # 3) Product + Chat - Đợi trang sản phẩm sẵn sàng
        logger.info("[STATE] Navigating to product and opening chat")

        # Đợi trang sản phẩm sẵn sàng để không "đứng im"
        try:
            ok_offer = await playwright_driver._wait_offer_ready(page, timeout_ms=15000)
            if not ok_offer:
                logger.warning("[STATE] Offer page not ready, reloading...")
                await page.reload(wait_until="domcontentloaded")
                ok_offer = await playwright_driver._wait_offer_ready(page, timeout_ms=12000)

            if not ok_offer:
                logger.warning("[STATE] Offer page not ready, continuing anyway (URL looks correct)")
                # Don't block - continue to click kefu anyway

            logger.info("✅ Offer ready – tiếp tục mở chat…")

            # đảm bảo đang ở đầu trang để hiện thanh shop
            try:
                await page.evaluate("window.scrollTo(0,0)")
                for hsel in ["header", ".detail-header", ".shop-header", ".store-header", ".nav-header"]:
                    loc = page.locator(hsel)
                    if await loc.count():
                        try:
                            await loc.first.hover()
                        except:
                            pass
                        break
            except:
                pass

            # >>> ENSURE PRODUCT PAGE AND CHAT ARE READY <<<
            from playwright_driver import ensure_product_and_chat_open, dismiss_offer_overlays
            logger.info("[STATE] Ensuring product page and chat are ready...")

            chat_status = await ensure_product_and_chat_open(
                page,
                offer_url,
                logger=logger
            )

            # Null-safe validation of chat_status
            if not chat_status or not isinstance(chat_status, dict):
                logger.error("[STATE] Invalid chat_status returned from ensure_product_and_chat_open")
                # Emit WebSocket message
                try:
                    from app import manager
                    import json
                    await manager.broadcast(json.dumps({
                        "phase": "blocked",
                        "error_type": "chat_error",
                        "message": "Error opening chat: Invalid response from chat detection system",
                        "need_user_action": True
                    }))
                except Exception:
                    pass
                return

            if chat_status.get("ok"):
                # chat_ready -> proceed as before
                logger.info("[STATE] Chat is ready, continuing negotiation flow")
                logger.info("[STATE] found kefu: %d", chat_status.get("kefu_count", 0))
                chat_page = chat_status.get("page", page)

                # Additional overlay dismiss as safety measure
                await dismiss_offer_overlays(chat_page)

                # Gate sau khi vào sản phẩm và mở chat
                _state["step"] = "S1_DONE"; _save_session_snapshot()
                reset_gate("CONFIRM_PRODUCT_AND_CHAT")
                await _wait_gate("CONFIRM_PRODUCT_AND_CHAT", timeout=90)
            else:
                status_type = chat_status.get("type")
                if status_type == "blocked_by_captcha":
                    # We hit a captcha interception page.
                    logger.error("[STATE] Blocked by Alibaba captcha interception at %s", chat_status.get("url"))
                    # Emit WebSocket message
                    try:
                        from app import manager
                        import json
                        await manager.broadcast(json.dumps({
                            "phase": "blocked",
                            "error_type": "blocked_by_captcha",
                            "message": "Alibaba blocked this product page due to unusual traffic. Please solve the slider captcha in the browser or change proxy, then click Retry."
                        }))
                    except Exception:
                        pass
                    # stay in the current state and do NOT auto-advance
                    return
                elif status_type == "captcha_block":
                    # Legacy captcha detection (fallback)
                    logger.error("[STATE] Captcha / unusual-traffic block detected at %s", chat_status.get("url"))
                    # Emit WebSocket message
                    try:
                        from app import manager
                        import json
                        await manager.broadcast(json.dumps({
                            "message": "⚠️ 1688 is showing a captcha / unusual-traffic screen. Please solve it in the browser window, then click Retry.",
                            "phase": "blocked",
                            "need_user_action": True,
                            "error_type": "captcha_block"
                        }))
                    except Exception:
                        pass
                    # stay in the current state and do NOT auto-advance
                    return
                elif status_type == "chat_not_found":
                    logger.error("[STATE] Chat entry not found on product page: %s", chat_status.get("url"))
                    # Emit WebSocket message
                    try:
                        from app import manager
                        import json
                        await manager.broadcast(json.dumps({
                            "message": "⚠️ Cannot find the chat entry (kefu) on this product page. Please open the chat manually in the browser, then click Retry.",
                            "phase": "blocked",
                            "need_user_action": True,
                            "error_type": "chat_not_found"
                        }))
                    except Exception:
                        pass
                    # also stay in current state
                    return
                else:
                    # fallback: treat as error
                    logger.error("[STATE] Unexpected chat_status: %r", chat_status)
                    # Emit WebSocket message
                    try:
                        from app import manager
                        import json
                        await manager.broadcast(json.dumps({
                            "message": "❌ Failed to open chat for this product. Please check the browser window.",
                            "phase": "error",
                            "need_user_action": True,
                            "error_type": "chat_error"
                        }))
                    except Exception:
                        pass
                    return

            # Đợi ô chat sẵn sàng (đã hỗ trợ <pre.edit contenteditable="true">)
            try:
                await playwright_driver.wait_for_chat_ready(chat_page, timeout_s=25)
                logger.info("[STATE] Chat interface is ready for messaging")
            except RuntimeError as chat_error:
                logger.error(f"[STATE] Chat interface failed to load: {str(chat_error)}")
                _state["step"] = "S1_ERROR"
                _save_session_snapshot()
                raise RuntimeError(
                    f"Chat interface did not load. The 1688 page may be loading slowly or the chat service is unavailable. "
                    f"Please try refreshing the page and clicking the chat (客服) button manually, then retry. "
                    f"Error details: {str(chat_error)}"
                )

            # ===== S1: gửi opener do AI sinh =====
            # opener_text đã được tạo ở trên (generate_opener / từ config)
            await playwright_driver.send_on_chat_precise_canonical(chat_page, opener_text)

            # Gate (nếu bạn đang dùng auto-advance có thể giữ nguyên)
            _state["step"] = "S1_DONE"; _save_session_snapshot()
            reset_gate("CONFIRM_AFTER_SEND")
            await _wait_gate("CONFIRM_AFTER_SEND", timeout=30)

            # ===== S2: chờ supplier reply rồi sinh trả lời và gửi =====
            from playwright_driver import wait_for_supplier_reply_canonical, send_on_chat_precise_canonical

            # 1) Chờ supplier trả lời (text)
            supplier_reply = await wait_for_supplier_reply_canonical(chat_page, timeout_s=180)
            _state["supplier_reply"] = supplier_reply; _save_session_snapshot()

            # 2) Gọi AI sinh câu trả lời dựa trên supplier_reply
            try:
                from ai_client import ai_client

                # Xây dựng conversation history cho AI
                history = [
                    {"role": "user", "text": opener_text},
                    {"role": "assistant", "text": supplier_reply}
                ]

                # Generate AI reply với style từ request
                negotiation_style = _state.get("style", "Aggressive")
                goals = {"style": negotiation_style}

                ai_result = await ai_client.generate_next_reply(
                    history=history,
                    supplier_text=supplier_reply,
                    goals=goals,
                    product_url=_state.get("product_url", ""),
                    locale="zh"
                )

                if ai_result and ai_result.get("text"):
                    ai_reply = ai_result["text"]

                    # 3) Gửi lại qua chat
                    await send_on_chat_precise_canonical(chat_page, ai_reply)

                    # Lưu AI reply vào state
                    _state["ai_reply"] = ai_reply
                    _state["ai_reply_used_model"] = ai_result.get("used_model", "unknown")
                    _state["ai_reply_is_mock"] = ai_result.get("is_mock", False)
                else:
                    # Fallback if AI generation fails
                    ai_reply = "感谢您的回复，我们会尽快与您联系。"
                    await send_on_chat_precise_canonical(chat_page, ai_reply)
                    _state["ai_reply"] = ai_reply
                    _state["ai_reply_used_model"] = "fallback"

            except Exception as e:
                # Fallback if AI client fails
                logger.error(f"[AI_REPLY] Failed to generate AI reply: {e}")
                ai_reply = "感谢您的回复，我们会尽快与您联系。"
                await send_on_chat_precise_canonical(chat_page, ai_reply)
                _state["ai_reply"] = ai_reply
                _state["ai_reply_error"] = str(e)

            # 6) Persist storage state
            try:
                # Try to get context from page if available
                if hasattr(chat_page, 'context'):
                    await playwright_driver.persist_state(chat_page.context)
                else:
                    # Fallback: try to get context from global page
                    global_page = _state.get("_page")
                    if global_page and hasattr(global_page, 'context'):
                        await playwright_driver.persist_state(global_page.context)
            except Exception as e:
                logger.warning(f"[STATE] Failed to persist storage state: {e}")

            # ===== Finish & return dict để app.py không .get trên None =====
            _state["status"] = "done"; _state["step"] = "DONE"
            _state["finished_at"] = datetime.utcnow().isoformat() + "Z"
            _save_session_snapshot()
            return {"session_id": _state["session_id"], "status": _state["status"], "reply": _state.get("supplier_reply")}
        except Exception as e:
            logger.error(f"[STATE] Error checking offer readiness: {e}")
            raise

    except Exception as e:
        _state["status"] = "error"
        _state["last_error"] = f"{type(e).__name__}: {e}"
        _state["finished_at"] = datetime.utcnow().isoformat() + "Z"
        _save_session_snapshot()
        raise
    finally:
        # cleanup state references (browser manager handles lifecycle)
        try:
            for k in ("_pw", "_browser", "_context", "_page"):
                _state.pop(k, None)
            _save_session_snapshot()
        except Exception:
            pass

def get_status():
    """Dùng cho /api/status."""
    out = {k: v for k, v in _state.items() if not k.startswith("_")}
    return out

def is_running() -> bool:
    return _state.get("status") == "running"

def get_current_session():
    """Trả về snapshot chi tiết (dạng dict) nếu muốn call như hàm."""
    sid = _state.get("session_id")
    info = {k: v for k, v in _state.items() if not k.startswith("_")}
    return {
        "active": _state.get("status") == "running",
        "session": info if sid else None,
        "session_dir": str((SESS_DIR / sid).resolve()) if sid else None,
    }

async def start_login_only():
    """Start login-only session that stops at Work Home."""
    async with _lock:
        if _state["status"] == "running":
            raise RuntimeError("A session is already running")

        # init state
        _state.update({
            "session_id": _new_session_id(),
            "status": "running",
            "step": "LOGIN_ONLY_INIT",
            "turn": 0,
            "max_turns": 0,
            "product_url": None,
            "opener_text": None,
            "last_error": None,
            "reply": None,
            "started_at": datetime.utcnow().isoformat() + "Z",
            "finished_at": None,
        })
        (SESS_DIR / _state["session_id"]).mkdir(parents=True, exist_ok=True)
        _save_session_snapshot()

    # outside lock to avoid blocking /status
    try:
        # Launch browser/context/page
        _state["step"] = "LAUNCH_BROWSER_FOR_LOGIN"
        _save_session_snapshot()
        pw, browser, context, page = await playwright_driver.start()
        _state["_pw"] = pw
        _state["_browser"] = browser
        _state["_context"] = context
        _state["_page"] = page
        _save_session_snapshot()

        # Ensure login and navigate to Work Home
        _state["step"] = "ENSURE_LOGIN_TO_WORK_HOME"
        _save_session_snapshot()
        login_result = await playwright_driver.ensure_login_via_taobao(
            page,
            product_url="https://work.1688.com/?tracelog=login_target_is_blank_1688",
            timeout_login=120_000  # 120 seconds for login
        )

        # Handle login result for start_login_only
        # Null-safe validation of login_result
        if not login_result or not isinstance(login_result, dict):
            logger.error("[STATE] Invalid login_result returned from login function")
            raise RuntimeError("Login failed: Invalid response from login system")

        if not login_result.get("ok"):
            error_type = login_result.get("type")
            reason = login_result.get("reason")
            if error_type == "login_timeout":
                raise RuntimeError(f"Login timeout: {reason if reason else 'User did not complete login in time'}")
            elif error_type == "proxy_tunnel_failed":
                raise RuntimeError(f"Proxy tunnel failed: {reason if reason else 'Unable to reach work.1688.com through proxy'}")
            else:
                raise RuntimeError(f"Login failed: {reason if reason else 'Unknown reason'}")

        # Persist storage state
        await playwright_driver.persist_state(_state["_context"])

        _state["step"] = "READY_FOR_PRODUCT"
        _save_session_snapshot()

        return {
            "session_id": _state["session_id"],
            "status": _state["status"],
            "step": _state["step"]
        }

    except Exception as e:
        _state["status"] = "error"
        _state["last_error"] = f"{type(e).__name__}: {e}"
        _state["finished_at"] = datetime.utcnow().isoformat() + "Z"
        _save_session_snapshot()
        raise
    finally:
        # Don't close browser - keep it open for goto_product
        _save_session_snapshot()

async def goto_product(product_url_raw: str):
    """Navigate to product URL with existing session."""
    async with _lock:
        if _state["status"] != "running" or _state.get("step") != "READY_FOR_PRODUCT":
            raise RuntimeError("No active ready session. Call login-only first.")

    try:
        # Normalize product URL
        product_url = playwright_driver.normalize_1688_product_url(product_url_raw)

        # Get managed page with auto-recovery
        page = await playwright_driver.get_or_new_page()
        _state["_page"] = page

        # Page lifecycle check before navigation
        if page.is_closed():
            logger.warning("[STATE] Page closed in goto_product, reopening...")
            page = await playwright_driver.reopen_page()
            _state["_page"] = page

        # Set safe headers and navigate with recovery
        _state["step"] = "NAVIGATING_TO_PRODUCT"
        _save_session_snapshot()

        try:
            page = await playwright_driver.safe_goto(page, product_url, wait="domcontentloaded")
        except Exception as e:
            logger.warning(f"[STATE] Navigation failed, retrying with new page: {e}")
            page = await playwright_driver.reopen_page()
            _state["_page"] = page
            page = await playwright_driver.safe_goto(page, product_url, wait="domcontentloaded")

        # Wait for product page to be ready
        ok = await playwright_driver._wait_offer_ready(page, timeout_ms=15000)
        if not ok:
            logger.warning("[STATE] Product page not ready, reloading...")
            await page.reload(wait_until="domcontentloaded")
            ok = await playwright_driver._wait_offer_ready(page, timeout_ms=12000)

        if not ok:
            logger.error("[STATE] Product page not ready after navigation")
            raise RuntimeError("Product page not ready after navigation")

        # Update state
        _state["product_url"] = product_url
        _state["step"] = "AT_PRODUCT"
        _save_session_snapshot()

        return {
            "ok": True,
            "normalized_url": product_url,
            "step": _state["step"]
        }

    except Exception as e:
        _state["status"] = "error"
        _state["last_error"] = f"{type(e).__name__}: {e}"
        _save_session_snapshot()
        raise

async def cancel():
    async with _lock:
        try:
            if _state.get("_pw") and _state.get("_browser"):
                await playwright_driver.stop(_state["_pw"], _state["_browser"])
        finally:
            for k in ("_pw", "_browser", "_context", "_page"):
                _state.pop(k, None)
            _state["status"] = "cancelled"
            _state["step"] = "CANCELLED"
            _state["finished_at"] = datetime.utcnow().isoformat() + "Z"
            _save_session_snapshot()

# ============== Export object that app.py imports ==============
# Lưu ý: app.py dùng state_machine.<attr> như *thuộc tính*.
# Nên ta export:
#   - start (async function)
#   - get_status (function)
#   - is_running (function)    -> app.py đang dùng truthy check, vẫn ok
#   - current_session (OBJECT) -> có .id, .current_state, ...
#   - get_current_session (function) -> ai muốn gọi hàm thì dùng cái này
#   - cancel (async function)
_sync_current_session_obj()
async def stop_negotiation():
    return await cancel()
state_machine = _SNS(
    start=start,
    get_status=get_status,
    is_running=is_running,
    current_session=current_session_obj,
    get_current_session=get_current_session,
    cancel=cancel,
    stop_negotiation=stop_negotiation,  # <— thêm dòng này
    start_login_only=start_login_only,
    goto_product=goto_product,
    # Gate functions for manual control
    open_gate=open_gate,
    reset_gate=reset_gate,
)

