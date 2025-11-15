# 1688 Negotiation Agent

A production-ready, full-stack system for automated B2B negotiation with 1688.com suppliers, powered by AI and browser automation.

## Quick Start

```bash
# Clone and start
docker compose up --build

# Access interfaces
# Frontend: http://localhost:9001
# Backend API: http://localhost:8888 (OpenAPI docs at /docs)
```

## Features

- 🤖 **AI-Powered Negotiation** - Google AI integration with intelligent fallback responses
- 🔐 **Manual Login Support** - Secure manual login with session persistence
- 📊 **Real-Time Progress** - Live state machine visualization with WebSocket logs
- 📸 **Screenshot Documentation** - Automatic screenshots at every key step
- 🔄 **Robust State Machine** - Complete negotiation flow with error recovery
- 🌐 **Modern Web Interface** - Professional React frontend with live updates
- 🐳 **Dockerized** - Single command deployment with health checks

## Architecture

### State Machine Flow
```
S0: ENSURE_LOGIN_VIA_TAOBAO → S1: OPEN_PRODUCT_AND_CHAT →
S2: SEND_OPENING_MESSAGE → S3: WAIT_FOR_SUPPLIER_REPLY ↔
S4: AI_GENERATE_AND_REPLY (loop) → S_DONE / S_ERROR
```

### Core Components
- **Backend**: Python FastAPI with Playwright automation
- **Frontend**: Vite + React with WebSocket integration
- **AI**: Google Gemini 2.5 Flash with intelligent fallbacks
- **Persistence**: Structured logs, screenshots, and chat transcripts

## Usage

### Web Interface
1. Navigate to `http://localhost:9001`
2. Enter a 1688 product URL
3. Configure negotiation goals (price, MOQ, lead time)
4. Click "Start Negotiation"
5. Manual login required on first run
6. Monitor progress in real-time

### API
- `POST /api/negotiate/start` - Start negotiation session
- `GET /api/status` - Check system status
- `WS /ws/logs` - Real-time log streaming
- `GET /api/artifacts/:run_id` - Access session artifacts

## Configuration

Environment variables in `backend/.env`:
```env
GOOGLE_MODEL=gemini-2.5-flash
GOOGLE_API_KEY=AIzaSyAtBTek7scCjgJSMg3-_3JQGGzyGxWj3y0
```

## Development

```bash
# Start development environment
docker compose up --build

# View logs
docker compose logs -f backend
docker compose logs -f frontend
```

## Artifacts

All negotiation sessions are stored in `backend/data/<run_id>/`:
- `screens/` - Screenshot documentation
- `transcript.json` - Complete chat history
- `summary.json` - Extracted negotiation outcomes
- `logs.txt` - Session logs

## Security

- **Manual Login Only** - No credential automation
- **Environment Variables** - Secure configuration management
- **Rate Limiting** - Built-in delays and timeouts
- **Audit Trail** - Complete session documentation

## Browser Compatibility

- Chromium-based browser automation
- Persistent session storage
- Anti-detection measures
- Multiple selector fallbacks

---

**Built for professional B2B automation on 1688.com**

==============================================================
import os, asyncio
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from playwright.async_api import async_playwright
import time

# ========= ENV & PATHS =========
if not os.environ.get('DISPLAY'):
    os.environ['DISPLAY'] = ':99'

STATE_JSON = '/app/data/user_data_dir/playwright_context/state.json'
SCREEN_DIR = '/app/screenshots'
Path(STATE_JSON).parent.mkdir(parents=True, exist_ok=True)
Path(SCREEN_DIR).mkdir(parents=True, exist_ok=True)

# ========= Helpers =========
async def _shot(page, tag):
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    p = f'{SCREEN_DIR}/{tag}_{ts}.png'
    try:
        await page.screenshot(path=p, full_page=True)
    except Exception:
        pass
    return p
# --- Login & Captcha helpers ---

async def is_logged_in(page) -> bool:
    try:
        u = page.url or ""
        if "work.1688.com/home/seller.htm" in u:
            return True
        cookies = await page.context.cookies()
        names = {c.get("name") for c in cookies}
        # các cookie phổ biến sau login (mang tính gợi ý, không tuyệt đối)
        if "UC1" in names and "cna" in names:
            return True
        # UI dấu hiệu đã đăng nhập
        if await page.query_selector('a[href*="logout"], a[aria-label*="退出"], [data-role="userinfo"]'):
            return True
    except Exception:
        pass
    return False

async def detect_and_wait_captcha(page, timeout_ms: int = 180_000) -> bool:
    """Phát hiện trang captcha 'unusual traffic' và chờ bạn xử lý trong noVNC"""
    try:
        html = (await page.content()).lower()
        if ("unusual traffic" in html or
            "captcha" in html or
            "请拖动滑块" in html or
            "slide to verify" in html):
            await _shot(page, "captcha_detected")
            # chờ cho đến khi captcha biến mất
            await page.wait_for_function(
                """() => {
                    const t = document.body.innerText || '';
                    return !t.includes('unusual traffic')
                           && !t.includes('请拖动滑块')
                           && !t.includes('slide to verify');
                }""",
                timeout=timeout_ms
            )
            await _shot(page, "captcha_solved")
            # lưu state để lần sau giảm xác suất bị hỏi lại
            try:
                await page.context.storage_state(path=STATE_JSON)
            except Exception:
                pass
            return True
    except Exception:
        pass
    return False

# ========= CORE (launch/close + aliases start/stop) =========
async def launch_browser():
    pw = await async_playwright().start()
    try:
        browser = await pw.chromium.launch(
            headless=False,
            args=[
                '--no-sandbox','--disable-setuid-sandbox',
                '--disable-dev-shm-usage','--disable-gpu',
                '--disable-accelerated-2d-canvas','--no-zygote'
            ],
        )
        if Path(STATE_JSON).exists():
            context = await browser.new_context(
                storage_state=STATE_JSON,
                locale="zh-CN",
                timezone_id="Asia/Shanghai",
                user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                            "AppleWebKit/537.36 (KHTML, like Gecko) "
                            "Chrome/122.0 Safari/537.36"),
            )
        else:
            context = await browser.new_context(
                locale="zh-CN",
                timezone_id="Asia/Shanghai",
                user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                            "AppleWebKit/537.36 (KHTML, like Gecko) "
                            "Chrome/122.0 Safari/537.36"),
            )
        await context.add_init_script("""
        Object.defineProperty(navigator,'webdriver',{get:()=>undefined});
        Object.defineProperty(navigator,'languages',{get:()=>['zh-CN','zh','en']});
        Object.defineProperty(navigator,'platform',{get:()=> 'Win32'});
        window.chrome = { runtime: {} };
        """)
        page = await context.new_page()
        return pw, browser, context, page
    except Exception:
        try:
            await pw.stop()
        except Exception:
            pass
        raise

async def persist_state(context):
    await context.storage_state(path=STATE_JSON)

async def close_browser(pw, browser):
    try:
        await browser.close()
    finally:
        try:
            await pw.stop()
        except Exception:
            pass

# Backward compatibility
async def start():
    return await launch_browser()

async def stop(pw, browser):
    return await close_browser(pw, browser)

# ========= Canonical Actions =========
# ------------------ ROBUST LOGIN FOR 1688 ------------------
LOGIN_HOME = "https://work.1688.com/home/seller.htm"
LOGIN_PAGE = "https://login.1688.com/member/login.htm?lang=en_US&Done=https://work.1688.com/home/seller.htm"

async def ensure_login_via_taobao(page, timeout_s: int = 600):
    """Đảm bảo người dùng đã đăng nhập vào 1688 (qua Taobao hoặc QR)."""
    LOGIN_PAGE = "https://login.1688.com/member/login.htm?lang=en_US&Done=https://work.1688.com/home/seller.htm"
    LOGIN_HOME = "https://work.1688.com/home/seller.htm"

    # Nếu đã login rồi → thoát luôn
    if await is_logged_in(page):
        return True

    # Nếu đang ở trang login → KHÔNG goto nữa, chỉ ép English 1 lần
    u = (page.url or "").lower()
    if any(dom in u for dom in ["login.1688.com", "login.taobao.com", "member/login.htm", "member/jump.htm"]):
        await page.evaluate("""
          try {
            if (!window.__langForced) {
              const url = new URL(location.href);
              if (url.hostname.endsWith('1688.com')
                  && url.pathname.includes('/member/login.htm')
                  && url.searchParams.get('lang') !== 'en_US') {
                url.searchParams.set('lang', 'en_US');
                window.__langForced = true;
                if (url.toString() !== location.href)
                  location.replace(url.toString());
              }
            }
          } catch(e){}
        """)
        return await wait_until_logged_in(page, timeout_s)

    # Còn lại → ép về trang login
    await page.goto(LOGIN_PAGE, wait_until="domcontentloaded")

    # Vòng lặp chờ login
    start_t = time.time()
    last_shot_t = 0
    while time.time() - start_t < timeout_s:
        if await is_logged_in(page):
            return True

        u = (page.url or "").lower()
        # Nếu bị quăng sai trang -> kéo về login
        if ("wrongpage.html" in u) or ("marketsigninjump" in u) or ("/404" in u):
            try:
                await page.evaluate("""
                  try {
                    document.querySelectorAll('meta[http-equiv="refresh"]').forEach(m => m.remove());
                    const id = setInterval(()=>{}, 9999);
                    for (let i=0;i<=id;i++){clearInterval(i);clearTimeout(i);}
                  } catch(e){}
                """)
            except:
                pass
            await page.goto(LOGIN_PAGE, wait_until="domcontentloaded")
            continue

        html = (await page.content()).lower()
        if "unusual traffic" in html or "captcha" in html:
            await detect_and_wait_captcha(page, timeout_ms=60_000)

        if time.time() - last_shot_t > 10:
            await _shot(page, "login_waiting")
            last_shot_t = time.time()

        await asyncio.sleep(1)

    return False


async def bounce_from_wrongpage(page):
    """Nếu đang ở wrongpage/404 thì tắt auto-redirect và quay về trang login 1688."""
    try:
        await page.evaluate("""
          try {
            // tắt meta refresh / countdown
            document.querySelectorAll('meta[http-equiv="refresh"]').forEach(m=>m.remove());
            // clear mọi timer đơn giản
            const id = setInterval(()=>{}, 9999);
            for (let i=0; i<=id; i++) { clearInterval(i); clearTimeout(i); }
          } catch(e) {}
        """)
    except Exception:
        pass
    await page.goto(LOGIN_PAGE, wait_until="domcontentloaded")

async def wait_until_logged_in(page, timeout_s: int = 300):
    import time, asyncio
    LOGIN_HOME = "https://work.1688.com/home/seller.htm"
    deadline = time.time() + timeout_s
    last_shot = 0
    while time.time() < deadline:
        if await is_logged_in(page):
            # về đúng trang home seller nếu đang ở trang khác
            if "work.1688.com/home/seller.htm" not in (page.url or ""):
                await page.goto(LOGIN_HOME, wait_until="domcontentloaded")
            try:
                await page.context.storage_state(path=STATE_JSON)
            except:
                pass
            return True

        # nếu lạc sang wrongpage/404/marketSigninJump -> kéo về home
        u = (page.url or "").lower()
        if any(x in u for x in ["wrongpage.html", "marketsigninjump", "/404"]):
            await page.goto(LOGIN_HOME, wait_until="domcontentloaded")

        # nếu hiện captcha "unusual traffic" -> chờ bạn xử lý trong noVNC
        try:
            html = (await page.content()).lower()
            if "unusual traffic" in html or "captcha" in html:
                await detect_and_wait_captcha(page, timeout_ms=60_000)
        except:
            pass

        if time.time() - last_shot > 10:
            try: await _shot(page, "login_waiting")
            except: pass
            last_shot = time.time()
        await asyncio.sleep(1.0)

    raise RuntimeError("Login not completed in time")



async def open_chat_from_product_canonical(page, product_url: str, timeout_s: int = 90):
    """Mở chat từ trang sản phẩm sau khi login ổn định."""
    LOGIN_HOME = "https://work.1688.com/home/seller.htm"

    # 🚫 Nếu chưa login -> không làm gì cả (chặn mở product khi bạn còn đang login)
    if not await is_logged_in(page):
        await _shot(page, "blocked_open_product_need_login")
        return False

    # Ổn định session
    await page.goto(LOGIN_HOME, wait_until="domcontentloaded")
    await page.wait_for_timeout(1000)

    tries = 0
    while tries < 3:
        tries += 1
        await page.goto(product_url, wait_until="domcontentloaded", referer=LOGIN_HOME)
        u = (page.url or "").lower()

        # Nếu rơi vào trang lỗi/wrongpage
        if any(x in u for x in ["wrongpage.html", "marketsigninjump", "/404"]):
            try:
                await page.evaluate("""
                  try {
                    document.querySelectorAll('meta[http-equiv="refresh"]').forEach(m=>m.remove());
                    const id = setInterval(()=>{}, 9999);
                    for (let i=0;i<=id;i++){clearInterval(i);clearTimeout(i);}
                  } catch(e){}
                """)
            except:
                pass
            await page.goto(LOGIN_HOME, wait_until="domcontentloaded")
            await page.wait_for_timeout(800)
            continue

        await detect_and_wait_captcha(page)
        break

    # Tìm nút chat
    await _shot(page, "product_opened")
    selectors = [
        'text=客服','text=联系','text=咨询','text=联系供应商',
        'button:has-text("客服")','[data-title*=客服]',
        '[aria-label*=客服]', '.contact-supplier,.customer-service,.im-chat,.im-btn'
    ]
    for sel in selectors:
        try:
            btn = await page.wait_for_selector(sel, timeout=3000)
            await btn.click()
            await _shot(page, "chat_clicked")
            break
        except Exception:
            continue

    # Kiểm tra iframe chat
    try:
        await page.wait_for_timeout(1000)
        for f in page.frames:
            if any(k in (f.url or '') for k in ['im','chat','message']):
                await _shot(page, 'chat_iframe_detected')
                return True
    except:
        pass

    await _shot(page, "chat_open_attempted")
    return True



async def send_on_chat_precise_canonical(page, text: str):
    input_selectors = [
        'textarea','[contenteditable="true"]','div[role="textbox"]',
        '.im-textarea,.msg-editor textarea,.chat-input textarea'
    ]
    send_selectors = [
        'text=发送','text=Send','button:has-text("发送")','button:has-text("Send")',
        '.send-btn,.im-send-btn,.chat-send-btn'
    ]

    typed = False
    for sel in input_selectors:
        try:
            el = await page.wait_for_selector(sel, timeout=2000)
            await el.click(); await el.fill(''); await el.type(text)
            await _shot(page, 'chat_text_typed'); typed = True; break
        except Exception:
            continue
    if not typed:
        raise RuntimeError('No chat input found')

    for sel in send_selectors:
        try:
            btn = await page.wait_for_selector(sel, timeout=1500)
            await btn.click(); await _shot(page, 'chat_text_sent_btn'); return True
        except Exception:
            continue

    try:
        await page.keyboard.press('Enter')
        await _shot(page, 'chat_text_sent_enter')
        return True
    except Exception:
        pass

    raise RuntimeError('Could not send message (send_on_chat_precise_canonical)')

async def wait_for_supplier_reply_canonical(page, timeout_s: int = 180):
    end = asyncio.get_event_loop().time() + timeout_s
    last_shot_t = 0
    known_texts = set()
    while asyncio.get_event_loop().time() < end:
        try:
            bubbles = await page.query_selector_all('.message,.msg-bubble,.chat-msg,.message-item')
            texts = []
            for b in bubbles[:50]:
                try:
                    t = (await b.inner_text())[:200].strip()
                    if t:
                        texts.append(t)
                except Exception:
                    pass
            new_ones = [t for t in texts if t not in known_texts]
            if new_ones:
                known_texts.update(new_ones)
                await _shot(page, 'reply_detected')
                return {'new_messages': new_ones[:5]}
        except Exception:
            pass

        now = asyncio.get_event_loop().time()
        if now - last_shot_t > 10:
            await _shot(page, 'reply_waiting')
            last_shot_t = now
        await asyncio.sleep(1.0)
    raise TimeoutError('No supplier reply in time (wait_for_supplier_reply_canonical)')

# ========= Namespace cho state_machine =========
playwright_driver = SimpleNamespace()
for _n in [
    'launch_browser','persist_state','close_browser','start','stop',
    'ensure_login_via_taobao','open_chat_from_product_canonical',
    'send_on_chat_precise_canonical','wait_for_supplier_reply_canonical'
]:
    setattr(playwright_driver, _n, globals()[_n])
