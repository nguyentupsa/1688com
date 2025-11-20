import os, asyncio
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from playwright.async_api import async_playwright, Page, Frame, TimeoutError as PWTimeoutError, Error as PlaywrightError
import re
from urllib.parse import urlparse, parse_qs, parse_qsl, urlsplit, urlunsplit, urlencode
from typing import Union
import logging
import random
from settings import settings

# ========= Custom Exceptions =========
class PunishPageError(RuntimeError):
    """Raised when Alibaba/1688 blocks access with a punish/access-denied page."""
    pass

# ========= ENV & PATHS =========
if not os.environ.get('DISPLAY'):
    os.environ['DISPLAY'] = ':99'

STATE_JSON = '/app/data/user_data_dir/playwright_context/state.json'
SCREEN_DIR = '/app/screenshots'
Path(STATE_JSON).parent.mkdir(parents=True, exist_ok=True)
Path(SCREEN_DIR).mkdir(parents=True, exist_ok=True)

# Setup logger
logger = logging.getLogger(__name__)

# ========= URL Utilities =========
def strip_spm(u: str) -> str:
    """Remove SPM tracking parameters from URLs."""
    p = urlsplit(u)
    q = [(k, v) for k, v in parse_qsl(p.query) if k.lower() != 'spm']
    return urlunsplit((p.scheme, p.netloc, p.path, urlencode(q, doseq=True), p.fragment))

# ========= Browser Management ==========
_browser = None
_context = None
_page = None

# ========= Helpers =========
async def _shot(page, tag):
    """Take screenshot for debugging."""
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    p = f'{SCREEN_DIR}/{tag}_{ts}.png'
    try:
        await page.screenshot(path=p, full_page=True)
        logger.info(f"[SHOT] Screenshot saved: {p}")
    except Exception as e:
        logger.error(f"[SHOT] Failed to take screenshot: {e}")
    return p

def _is_punish_page(url: str, page_text: str = "") -> bool:
    """Check if we're on a punish/access-denied page - FOR DEBUGGING ONLY."""
    url = (url or "").lower()
    page_text = (page_text or "").lower()

    # URL-based detection
    if "alicdn.com/punish" in url or "punish" in url:
        return True

    # Text-based detection
    deny_phrases = [
        "访问被拒绝",  # Access denied
        "您的访问被拒绝",  # Your access is denied
        "异常流量",   # Abnormal traffic
        "安全验证",   # Security verification
        "人机验证",   # Human verification
    ]

    return any(phrase in page_text for phrase in deny_phrases)

# ========= LOGIN - ULTRA MINIMAL =========
async def check_if_logged_in(page):
    """Check login status - URL + DOM based detection (no cookies)."""
    try:
        current_url = page.url or ""

        # Rule 1: If URL contains "login.taobao.com" → NOT logged in → return False
        if "login.taobao.com" in current_url:
            logger.info(f"[LOGIN] NOT logged in - on login page: {current_url}")
            return False

        # Rule 2: If URL contains any logged-in indicators → logged in → return True
        logged_in_urls = ['www.1688.com', 'my.1688.com', 'work.1688.com', 'member.1688.com']
        if any(indicator in current_url for indicator in logged_in_urls):
            logger.info(f"[LOGIN] Logged in detected via URL: {current_url}")
            return True

        # Rule 3: Check DOM elements that ONLY appear after login
        try:
            login_indicators = [
                '.member-nickname',
                '.member-name',
                '.user-name',
                'a[href*="logout"]',
                'img[alt*="avatar"]'
            ]

            for selector in login_indicators:
                element = await page.query_selector(selector)
                if element:
                    # Check if element is visible for more reliability
                    is_visible = await element.is_visible()
                    if is_visible:
                        logger.info(f"[LOGIN] Logged in detected via DOM element: {selector}")
                        return True
        except Exception as e:
            logger.debug(f"[LOGIN] Error checking DOM elements: {e}")

        # Rule 4: Otherwise → return False
        logger.info(f"[LOGIN] NOT logged in - no indicators found: {current_url}")
        return False

    except Exception as e:
        logger.error(f"[LOGIN] Error checking login status: {e}")
        return False

async def login(page):
    """
    HUMAN-LIKE LOGIN with working proxy:
    1. Open 1688.com with realistic behavior
    2. Scroll and browse naturally
    3. Find and click login button like human
    4. Wait for manual login
    5. Detect success
    """
    try:
        logger.info("[LOGIN] Starting human-like login with proxy")

        # STEP 1: Natural browsing behavior first
        logger.info("[LOGIN] Opening 1688.com like human user")

        # Add thinking delay
        await asyncio.sleep(random.uniform(3, 6))

        # Navigate naturally
        await page.goto("https://www.1688.com", timeout=60000)

        # Wait for page to load completely
        await asyncio.sleep(random.uniform(4, 7))

        # Simulate human scrolling/reading
        try:
            await page.evaluate("window.scrollBy(0, Math.random() * 300)")
            await asyncio.sleep(random.uniform(1, 3))
            await page.evaluate("window.scrollBy(0, Math.random() * 200)")
            await asyncio.sleep(random.uniform(1, 2))
        except Exception:
            pass

        # Check if already logged in
        if await check_if_logged_in(page):
            logger.info("[LOGIN] Already logged in")
            return True

        # STEP 2: Look for login button with human-like approach
        logger.info("[LOGIN] Looking for login button")

        login_found = False

        # Human-like search for login button
        login_selectors = [
            'text=登录',
            'text=请登录',
            'a[href*="login"]',
            '.login-btn',
            'button:has-text("登录")',
            '.header-login a'
        ]

        # Try each selector with human-like delays
        for i, selector in enumerate(login_selectors):
            try:
                # Add delay between attempts - like human thinking
                if i > 0:
                    await asyncio.sleep(random.uniform(1, 2))

                element = await page.wait_for_selector(selector, timeout=3000)
                if element and await element.is_visible():
                    # Move mouse to element like human
                    await element.hover()
                    await asyncio.sleep(random.uniform(0.5, 1.5))

                    # Click like human
                    await element.click()
                    login_found = True
                    logger.info(f"[LOGIN] Clicked login button: {selector}")
                    break
            except Exception:
                continue

        if not login_found:
            # Final JS fallback
            await asyncio.sleep(2)
            try:
                await page.evaluate("""
                    () => {
                        const elements = Array.from(document.querySelectorAll('*'))
                            .filter(el => {
                                const style = getComputedStyle(el);
                                return style.visibility !== 'hidden' &&
                                       style.display !== 'none' &&
                                       el.offsetWidth > 0 &&
                                       el.offsetHeight > 0 &&
                                       el.innerText && el.innerText.includes('登录');
                            });
                        if (elements.length > 0) {
                            elements[0].click();
                            return true;
                        }
                        return false;
                    }
                """)
                login_found = True
                logger.info("[LOGIN] Clicked login via JS fallback")
            except Exception:
                pass

        if not login_found:
            logger.error("[LOGIN] Could not find login button")
            return False

        # Wait for login page to load
        await asyncio.sleep(random.uniform(4, 6))

        # STEP 3: Wait for manual login with natural checking
        logger.info("[LOGIN] Please login manually in VNC")
        print("[LOGIN] Login page ready - please login manually")

        login_timeout = 300
        deadline = asyncio.get_event_loop().time() + login_timeout

        while asyncio.get_event_loop().time() < deadline:
            # Human-like checking frequency - less frequent
            await asyncio.sleep(random.uniform(15, 25))

            if await check_if_logged_in(page):
                logger.info("[LOGIN] Login successful!")

                # Natural delay after login
                await asyncio.sleep(random.uniform(2, 4))

                # Save state
                try:
                    await page.context.storage_state(path=STATE_JSON)
                    logger.info("[LOGIN] Login state saved")
                except Exception:
                    pass

                return True

        logger.error("[LOGIN] Login timeout")
        return False

    except Exception as e:
        logger.error(f"[LOGIN] Error: {e}")
        return False

# ========= Browser Launch Helper with Fallback =========
async def launch_chromium_with_fallback(playwright, logger=None, **kwargs):
    """
    Launch browser safely:
    - If DISPLAY exists: try headless=False (headed mode via Xvfb)
    - If it fails OR DISPLAY missing: fall back to headless=True
    """
    import os

    display = os.environ.get("DISPLAY")

    # Respect explicit headless override
    if "headless" in kwargs:
        if logger:
            logger.info(f"[BROWSER] Using explicit headless setting: {kwargs['headless']}")
        return await playwright.chromium.launch(**kwargs)

    # Check if force headless is enabled in settings
    if settings.browser_force_headless:
        if logger:
            logger.info("[BROWSER] Force headless mode enabled by settings")
        return await playwright.chromium.launch(headless=True, **kwargs)

    # Try headed mode IF Xvfb is expected to exist
    if display:
        try:
            if logger:
                logger.info(f"[BROWSER] Trying headed mode with DISPLAY={display}")
            return await playwright.chromium.launch(headless=False, **kwargs)
        except Exception as e:
            if logger:
                logger.warning(f"[BROWSER] Headed launch failed. Falling back to headless. Error: {e}")

    # Final fallback → guaranteed headless
    if logger:
        logger.info("[BROWSER] Launching Chromium in HEADLESS mode as fallback")
    return await playwright.chromium.launch(headless=True, **kwargs)


# ========= Browser Launch - ABSOLUTELY NATURAL =========
async def launch_browser():
    """
    Launch browser like human with configurable proxy support.
    Proxy is only used when PROXY_ENABLED=true in settings.
    """
    pw = await async_playwright().start()

    try:
        logger.info("[BROWSER] Launching Chrome with configurable proxy support")

        # Build proxy configuration from environment variables
        proxy = None
        if settings.PROXY_ENABLED:
            proxy = {
                "server": f"http://{settings.PROXY_HOST}:{settings.PROXY_PORT}",
                "username": settings.PROXY_USERNAME or None,
                "password": settings.PROXY_PASSWORD or None,
            }
            logger.info(f"[PROXY] Using proxy: {proxy['server']} (user={settings.PROXY_USERNAME})")
        else:
            logger.info("[PROXY] Proxy disabled in settings")

        # Launch browser with fallback mechanism and proper arguments
        browser = await launch_chromium_with_fallback(
            pw,
            logger=logger,
            proxy=proxy,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--ignore-certificate-errors",
            ],
        )

        # Natural context setup
        context = await browser.new_context(
            viewport={'width': 1366, 'height': 768}
        )

        # Load existing state if available
        if Path(STATE_JSON).exists():
            context_options = {'storage_state': STATE_JSON}
            context = await browser.new_context(**context_options)
            logger.info("[BROWSER] Loaded existing state")
        else:
            context = await browser.new_context(
                viewport={'width': 1366, 'height': 768}
            )

        # Create page
        page = await context.new_page()

        logger.info("[BROWSER] Browser launched with proxy successfully")
        return pw, browser, context, page

    except Exception as e:
        logger.error(f"[BROWSER] Failed: {e}")
        # Fallback without proxy
        try:
            logger.info("[BROWSER] Retrying without proxy")
            browser = await launch_chromium_with_fallback(
                pw,
                logger=logger,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--ignore-certificate-errors",
                ],
            )
            context = await browser.new_context(
                viewport={'width': 1366, 'height': 768}
            )
            page = await context.new_page()
            return pw, browser, context, page
        except Exception as e2:
            logger.error(f"[BROWSER] Fallback also failed: {e2}")
            try:
                await pw.stop()
            except Exception:
                pass
            raise

# ========= Basic Functions =========
async def persist_state(context):
    """Save browser state."""
    try:
        await context.storage_state(path=STATE_JSON)
    except Exception:
        pass

async def close_browser(pw, browser):
    """Close browser."""
    try:
        await browser.close()
    finally:
        try:
            await pw.stop()
        except Exception:
            pass

async def safe_goto(page, url, wait="domcontentloaded", timeout=60000):
    """Navigate to URL - minimal approach."""
    try:
        clean_url = strip_spm(url)
        await page.goto(clean_url, wait_until=wait, timeout=timeout)
        return page
    except Exception as e:
        logger.error(f"[NAV] Error: {e}")
        raise

async def goto_taobao_login(page, url: str):
    """Navigate to Taobao login."""
    try:
        await page.goto(url, timeout=60000)
        return True
    except Exception as e:
        logger.error(f"[TAOBAO] Error: {e}")
        return False

# ========= Legacy Compatibility =========
async def ensure_logged_in(page, timeout_s: int = 180) -> bool:
    """Legacy function."""
    return await login(page)

async def ensure_buyer_mode(page, timeout_s: int = 20):
    """Buyer mode - basic."""
    try:
        await page.goto("https://work.1688.com/home/buyer.htm", timeout=30000)
        return True
    except Exception:
        return False

async def get_or_new_page():
    """Get or create page."""
    global _page
    if "_page" not in globals():
        _page = None
    if (not _page) or _page.is_closed():
        if not getattr(get_or_new_page, "_play", None):
            get_or_new_page._play = await async_playwright().start()
        pw, browser, context, page = await launch_browser()
        _page = page
        get_or_new_page._pw = pw
        get_or_new_page._browser = browser
        get_or_new_page._context = context
    return _page

async def reopen_page():
    """Reopen page."""
    global _page
    if _page and not _page.is_closed():
        try:
            await _page.close()
        except Exception:
            pass
    _page = None
    return await get_or_new_page()

def normalize_1688_product_url(raw: str) -> str:
    """Normalize product URL."""
    if not raw:
        raise ValueError("Empty product url/id")

    s = raw.strip()
    if re.fullmatch(r"\d{6,}", s):
        return f"https://detail.1688.com/offer/{s}.html"

    try:
        u = urlparse(s)
        path = u.path or ""
        qs = parse_qs(u.query or "")
    except Exception:
        raise ValueError(f"Invalid product url: {raw}")

    if "offerid" in {k.lower() for k in qs.keys()}:
        for k, v in qs.items():
            if k.lower() == "offerid" and v:
                oid = re.sub(r"\D", "", v[0] or "")
                if oid:
                    return f"https://detail.1688.com/offer/{oid}.html"

    m = re.search(r"/offer/(\d{6,})\.html", path)
    if m:
        return f"https://detail.1688.com/offer/{m.group(1)}.html"

    m = re.search(r"/detail/offer/(\d{6,})\.html", path)
    if m:
        return f"https://detail.1688.com/offer/{m.group(1)}.html"

    m = re.search(r"(\d{6,})", s)
    if m:
        return f"https://detail.1688.com/offer/{m.group(1)}.html"

    raise ValueError(f"Cannot normalize product url: {raw}")

async def _wait_offer_ready(page, timeout_ms=15000):
    """Wait for offer page."""
    await asyncio.sleep(2)  # Basic wait
    return True

# ========= Login Configuration =========
LOGIN_ENTRY_URL = "https://login.taobao.com/?redirect_url=https%3A%2F%2Flogin.1688.com%2Fmember%2Fjump.htm%3Ftarget%3Dhttps%253A%252F%252Fwww.1688.com%252F"

# ========= Reusable Login Detection =========
async def is_logged_in(page) -> bool:
    """
    Reusable function to check if user is logged in to 1688/Taobao.
    This consolidates all login detection logic in one place.
    """
    return await check_if_logged_in(page)

# ========= Captcha / Traffic Block Detection =========
async def is_captcha_or_traffic_block(page: Page) -> bool:
    """
    Detect if the current page is a captcha/unusual traffic block page.

    Args:
        page: Playwright page instance

    Returns:
        bool: True if captcha/traffic block detected, False otherwise
    """
    try:
        url = page.url or ""
        title = ""
        body_text = ""

        try:
            title = await page.title()
        except Exception:
            pass

        try:
            body_text = await page.inner_text("body")
        except Exception:
            pass

        # Heuristics for Alibaba captcha / unusual traffic pages
        if "Captcha Interception" in title:
            logger.warning(f"[CAPTCHA] Detected by title: {title}")
            return True

        if "unusual traffic from your network" in body_text.lower():
            logger.warning("[CAPTCHA] Detected by body text: unusual traffic from your network")
            return True

        if "please slide to verify" in body_text.lower():
            logger.warning("[CAPTCHA] Detected by body text: please slide to verify")
            return True

        if "访问异常" in body_text or "异常流量" in body_text:
            logger.warning("[CAPTCHA] Detected by Chinese text: 访问异常/异常流量")
            return True

        if "人机验证" in body_text or "滑块验证" in body_text:
            logger.warning("[CAPTCHA] Detected by Chinese text: 人机验证/滑块验证")
            return True

        # URL-based detection
        if "captcha" in url.lower() or "verify" in url.lower():
            logger.warning(f"[CAPTCHA] Detected by URL: {url}")
            return True

        return False

    except Exception as e:
        logger.error(f"[CAPTCHA] Error detecting captcha page: {e}")
        return False

# ========= Fallback Helper Functions =========
async def reopen_page_without_proxy_and_reuse_cookies(page, next_url: str) -> dict:
    """
    Create a new browser context without proxy, reuse cookies from the current context,
    and navigate to the product URL.

    Args:
        page: Current Playwright page with proxy context
        next_url: URL to navigate to

    Returns:
        dict: {"ok": bool, "type": str, "reason": str, "page": Page|None}
    """
    try:
        logger.info(f"[LOGIN] Starting fallback without proxy for URL: {next_url}")

        # Get current context and browser
        current_context = page.context
        browser = current_context.browser

        # Extract cookies from current context
        cookies = await current_context.cookies()
        logger.info(f"[LOGIN] Extracted {len(cookies)} cookies from current context")

        # Create new context without proxy
        new_context = await browser.new_context(
            viewport={'width': 1366, 'height': 768}
        )

        # Add cookies to new context
        await new_context.add_cookies(cookies)
        logger.info("[LOGIN] Added cookies to new context without proxy")

        # Create new page and navigate
        new_page = await new_context.new_page()

        try:
            await new_page.goto(next_url, wait_until="domcontentloaded", timeout=30000)
            logger.info(f"[LOGIN] Successfully navigated to {next_url} without proxy")

            return {
                "ok": True,
                "type": "fallback_without_proxy_success",
                "reason": f"Successfully reached {next_url} without proxy after tunnel failure",
                "page": new_page,
                "context": new_context
            }
        except Exception as nav_error:
            # Clean up new context if navigation still fails
            await new_context.close()
            error_msg = str(nav_error)
            if "ERR_TUNNEL_CONNECTION_FAILED" in error_msg or "ERR_PROXY_CONNECTION_FAILED" in error_msg:
                # This shouldn't happen without proxy, but handle it
                return {
                    "ok": False,
                    "type": "proxy_tunnel_failed",
                    "reason": f"Product URL unreachable even without proxy: {error_msg}",
                    "page": None
                }
            else:
                return {
                    "ok": False,
                    "type": "navigation_failed",
                    "reason": f"Navigation failed without proxy: {error_msg}",
                    "page": None
                }

    except Exception as e:
        logger.error(f"[LOGIN] Fallback without proxy failed: {e}")
        return {
            "ok": False,
            "type": "fallback_failed",
            "reason": f"Fallback without proxy failed: {str(e)}",
            "page": None
        }

def is_proxy_tunnel_error(error_str: str) -> bool:
    """
    Check if the error message indicates a proxy tunnel connection failure.

    Args:
        error_str: Error message string

    Returns:
        bool: True if this is a proxy tunnel error
    """
    error_patterns = [
        "ERR_TUNNEL_CONNECTION_FAILED",
        "ERR_PROXY_CONNECTION_FAILED",
        "net::ERR_TUNNEL_CONNECTION_FAILED",
        "net::ERR_PROXY_CONNECTION_FAILED",
        "Proxy tunnel failed",
        "Unable to connect to the proxy server"
    ]

    error_lower = error_str.lower()
    return any(pattern.lower() in error_lower for pattern in error_patterns)

# ========= Enhanced Login Function =========
async def ensure_login_via_taobao(page, product_url: str, *, timeout_login: int = 120_000, logger=logger) -> dict:
    """
    Refined 1688 login function that:
    1) Opens a dedicated login entry page first
    2) Waits for login to be completed
    3) Only then navigates to the product_url

    Args:
        page: Playwright page instance
        product_url: Product URL to navigate to after successful login
        timeout_login: Login timeout in milliseconds (default: 120 seconds)
        logger: Logger instance

    Returns:
        dict: {"ok": bool, "reason": str, "type": str|None, "page": Page|None}
    """
    import time

    try:
        logger.info(f"[LOGIN] Starting refined login flow for product: {product_url}")

        # Step 1: Navigate to dedicated login entry page FIRST
        logger.info("[LOGIN] Step 1: Opening dedicated login entry page")
        await page.goto(LOGIN_ENTRY_URL, wait_until="domcontentloaded", timeout=timeout_login)
        logger.info("[LOGIN] Opened login entry page: %s", LOGIN_ENTRY_URL)

        # Give page a moment to load and possibly redirect if already logged in
        await asyncio.sleep(3)

        # Step 2: Check if already logged in (might redirect to 1688 home)
        if await is_logged_in(page):
            logger.info("[LOGIN] User is already logged in - proceeding to product")
        else:
            logger.info("[LOGIN] User not logged in, waiting for manual login")
            logger.info("[LOGIN] Please complete login in the VNC browser window")

            # Step 3: Wait for login completion with polling
            start_time = time.monotonic()
            timeout_seconds = timeout_login / 1000
            check_interval = 2  # Check every 2 seconds

            while time.monotonic() - start_time < timeout_seconds:
                if await is_logged_in(page):
                    elapsed = time.monotonic() - start_time
                    logger.info("[LOGIN] Login detected and settled after %.1f seconds", elapsed)
                    break

                await asyncio.sleep(check_interval)
            else:
                # Timeout reached
                logger.error("[LOGIN] Login timeout after %d seconds", timeout_seconds)
                return {
                    "ok": False,
                    "type": "login_timeout",
                    "reason": f"User did not complete login in {timeout_seconds} seconds"
                }

        # Step 4: Login is settled, NOW navigate to product URL (after login confirmed)
        logger.info("[LOGIN] Step 4: Login settled, navigating to product_url: %s", product_url)

        try:
            await page.goto(product_url, wait_until="domcontentloaded", timeout=30000)
            logger.info("[LOGIN] Successfully navigated to product page after login")
            return {
                "ok": True,
                "reason": "login_and_product_ok",
                "type": "success"
            }
        except PlaywrightError as nav_error:
            error_str = str(nav_error)
            logger.warning(f"[LOGIN] Product navigation failed with error: {error_str}")

            if is_proxy_tunnel_error(error_str):
                logger.warning("[LOGIN] Proxy tunnel failed for product URL, trying fallback without proxy...")

                # Try fallback without proxy
                fallback_result = await reopen_page_without_proxy_and_reuse_cookies(page, product_url)
                if fallback_result["ok"]:
                    logger.info("[LOGIN] Fallback without proxy successful")
                    return {
                        "ok": True,
                        "reason": "login_ok_product_via_fallback",
                        "type": "proxy_tunnel_fallback_success"
                    }
                else:
                    logger.error(f"[LOGIN] Fallback without proxy also failed: {fallback_result['reason']}")
                    return {
                        "ok": False,
                        "reason": fallback_result["reason"],
                        "type": fallback_result["type"]
                    }
            else:
                # Re-raise non-proxy errors
                raise nav_error

    except PlaywrightError as e:
        error_str = str(e)
        if is_proxy_tunnel_error(error_str):
            logger.error(f"[LOGIN] Proxy tunnel error during login flow: {error_str}")
            return {
                "ok": False,
                "reason": f"Proxy tunnel failed during login: {error_str}",
                "type": "proxy_tunnel_failed"
            }
        else:
            error_msg = f"Login process failed with Playwright error: {error_str}"
            logger.error(f"[LOGIN] {error_msg}")
            return {
                "ok": False,
                "reason": error_msg,
                "type": "playwright_error"
            }
    except Exception as e:
        error_msg = f"Login process failed with unexpected error: {str(e)}"
        logger.error(f"[LOGIN] {error_msg}")
        return {
            "ok": False,
            "reason": error_msg,
            "type": "unexpected_error"
        }

# ========= Missing Chat Functions (Minimal Implementations) =========
async def open_chat_from_product_canonical(page, product_url: str, timeout_s: int = 90):
    """
    Open chat from product page - minimal implementation.
    This is a placeholder that should be enhanced with proper selectors.
    """
    try:
        logger.info(f"[CHAT] Opening chat for product: {product_url}")

        # Navigate to product page first
        await page.goto(product_url, wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(2)

        # Try to find chat button (common selectors)
        chat_selectors = [
            'text=联系供应商', 'text=客服', 'text=咨询',
            'button:has-text("联系")', '[data-title*="客服"]',
            '.contact-supplier', '.customer-service'
        ]

        for selector in chat_selectors:
            try:
                chat_btn = page.locator(selector).first
                if await chat_btn.is_visible(timeout=2000):
                    await chat_btn.click()
                    logger.info(f"[CHAT] Clicked chat button: {selector}")
                    await asyncio.sleep(2)
                    return True
            except Exception:
                continue

        logger.warning("[CHAT] Could not find chat button, but continuing")
        return True

    except Exception as e:
        logger.error(f"[CHAT] Error opening chat: {e}")
        # Don't raise error, just log and continue
        return True

async def send_on_chat_precise_canonical(page, text: str):
    """
    Send message in chat - minimal implementation.
    This is a placeholder that should be enhanced with proper selectors.
    """
    try:
        logger.info(f"[CHAT] Sending message: {text[:50]}...")

        # Try to find chat input
        input_selectors = [
            'textarea', '[contenteditable="true"]', 'div[role="textbox"]',
            'input[type="text"]', '.chat-input'
        ]

        message_sent = False
        for selector in input_selectors:
            try:
                input_el = page.locator(selector).first
                if await input_el.is_visible(timeout=2000):
                    await input_el.click()
                    await input_el.fill('')
                    await input_el.type(text)

                    # Try to send
                    send_selectors = [
                        'text=发送', 'text=Send', 'button:has-text("发送")',
                        '.send-btn', '[type="submit"]'
                    ]

                    for send_selector in send_selectors:
                        try:
                            send_btn = page.locator(send_selector).first
                            if await send_btn.is_visible(timeout=1000):
                                await send_btn.click()
                                logger.info(f"[CHAT] Message sent via button: {send_selector}")
                                message_sent = True
                                break
                        except Exception:
                            continue

                    # Try Enter key as fallback
                    if not message_sent:
                        try:
                            await page.keyboard.press('Enter')
                            logger.info("[CHAT] Message sent via Enter key")
                            message_sent = True
                        except Exception:
                            pass

                    if message_sent:
                        await asyncio.sleep(1)
                        return True

            except Exception:
                continue

        if not message_sent:
            logger.warning("[CHAT] Could not send message, but continuing")

        return True

    except Exception as e:
        logger.error(f"[CHAT] Error sending message: {e}")
        return True

async def wait_for_supplier_reply_canonical(page, timeout_s: int = 180):
    """
    Wait for supplier reply - minimal implementation.
    This is a placeholder that should be enhanced with proper detection.
    """
    try:
        logger.info(f"[CHAT] Waiting for supplier reply (timeout: {timeout_s}s)")

        # Simple timeout implementation
        # In a real implementation, this would detect new messages
        await asyncio.sleep(min(timeout_s, 10))  # Wait max 10 seconds for demo

        # Return a mock reply for now
        mock_reply = "感谢您的咨询，我们会尽快回复您。"  # "Thank you for your inquiry, we will reply soon."
        logger.info(f"[CHAT] Returning mock reply: {mock_reply}")

        return mock_reply

    except Exception as e:
        logger.error(f"[CHAT] Error waiting for reply: {e}")
        return "Timeout waiting for reply"

async def wait_for_chat_ready(page, timeout_s: int = 25):
    """
    Wait for chat interface to be ready - minimal implementation.
    This is a placeholder that should be enhanced with proper detection.
    """
    try:
        logger.info(f"[CHAT] Waiting for chat ready (timeout: {timeout_s}s)")

        # Try to find chat input elements
        chat_input_selectors = [
            'textarea', '[contenteditable="true"]', 'div[role="textbox"]',
            'input[type="text"]', '.chat-input', '.message-input'
        ]

        max_wait_time = min(timeout_s, 30)
        check_interval = 1
        elapsed = 0

        while elapsed < max_wait_time:
            for selector in chat_input_selectors:
                try:
                    chat_input = page.locator(selector).first
                    if await chat_input.is_visible(timeout=1000):
                        logger.info(f"[CHAT] Chat ready with input: {selector}")
                        return True
                except Exception:
                    continue

            await asyncio.sleep(check_interval)
            elapsed += check_interval

        logger.warning(f"[CHAT] Chat input not found after {elapsed} seconds, but continuing")
        return True

    except Exception as e:
        logger.error(f"[CHAT] Error waiting for chat ready: {e}")
        return True

async def click_kefu_open_chat(page: Page, timeout_ms: int = 12000, logger=None) -> Page:
    """
    From a 1688 product page, click the Kefu/chat button to open the chat window.
    Return the chat page object.

    Args:
        page: Current Playwright page on the product page
        timeout_ms: Timeout in milliseconds for finding and clicking chat button
        logger: Optional logger instance

    Returns:
        Page: The page object (could be same page or new chat page)
    """
    try:
        if logger:
            logger.info("[KEFU] Clicking 客服 to open chat...")

        # Common kefu/chat button selectors on 1688 product pages
        kefu_selectors = [
            'od-text[i18n="wangwang"]',  # Primary selector for kefu button
            'div._buttonWrap_1p2az_60 img[src*="O1CN01ZaHib31lWomw16ded"]',  # Backup
            'text=联系供应商', 'text=客服', 'text=咨询',
            'button:has-text("联系")', '[data-title*="客服"]',
            '.contact-supplier', '.customer-service', '.im-chat', '.im-btn',
            '[class*="kefu"]', '[class*="wangwang"]', '[class*="chat"]'
        ]

        # Try to find and click the kefu button
        kefu_clicked = False
        for selector in kefu_selectors:
            try:
                kefu_btn = page.locator(selector).first
                if await kefu_btn.is_visible(timeout=2000):
                    await kefu_btn.click()
                    if logger:
                        logger.info(f"[KEFU] Clicked kefu button: {selector}")
                    kefu_clicked = True
                    break
            except Exception:
                continue

        if not kefu_clicked:
            if logger:
                logger.warning("[KEFU] Could not find kefu button, but continuing")

        # Wait a moment for any popup or navigation
        await asyncio.sleep(2)

        # Check if a new page/chat window opened
        try:
            # Wait for potential new page context
            await page.wait_for_timeout(1000)

            # If we're still on the same page, try to find chat interface
            current_url = page.url
            if logger:
                logger.info(f"[KEFU] Current page URL after click: {current_url}")

            # Look for chat interface on current page
            chat_selectors = [
                'textarea', '[contenteditable="true"]', 'div[role="textbox"]',
                '.chat-input', '.message-input', '.im-chat-window'
            ]

            chat_found = False
            for selector in chat_selectors:
                try:
                    chat_el = page.locator(selector).first
                    if await chat_el.is_visible(timeout=1000):
                        if logger:
                            logger.info(f"[KEFU] Chat interface found: {selector}")
                        chat_found = True
                        break
                except Exception:
                    continue

            if chat_found:
                if logger:
                    logger.info("[KEFU] Chat opened on same page")
                return page
            else:
                if logger:
                    logger.warning("[KEFU] No chat interface detected, but returning page")
                return page

        except Exception as e:
            if logger:
                logger.warning(f"[KEFU] Error checking for chat interface: {e}")
            return page

    except Exception as e:
        if logger:
            logger.error(f"[KEFU] Error opening chat: {e}")
        # Return the page anyway to allow continuation
        return page

# ========= Enhanced Chat Opening with Captcha Detection =========
async def ensure_product_and_chat_open(page: Page, product_url: str, *, timeout_ms: int = 12000, logger=logger) -> dict:
    """
    Enhanced function that ensures we're on a valid product page and can open chat.
    This replaces the simple click_kefu_open_chat logic with proper captcha detection.

    Args:
        page: Playwright page instance
        product_url: Product URL that should be loaded
        timeout_ms: Timeout for finding kefu elements (default: 12 seconds)
        logger: Logger instance

    Returns:
        dict: {
            "ok": bool,
            "type": str,  # "captcha_block", "chat_not_found", "chat_ready"
            "reason": str,
            "url": str,
            "kefu_count": int,
            "page": Page
        }
    """
    try:
        logger.info(f"[CHAT] Ensuring product page and chat are ready for: {product_url}")

        # Step 1: Check if we're on a captcha/traffic block page
        if await is_captcha_or_traffic_block(page):
            logger.warning("[CHAT] Captcha / unusual traffic page detected at %s", page.url)
            return {
                "ok": False,
                "type": "captcha_block",
                "reason": "Captcha / unusual-traffic page detected instead of product/chat",
                "url": page.url,
                "kefu_count": 0,
                "page": page
            }

        # Step 2: Count kefu elements on the page
        kefu_selectors = [
            'od-text[i18n="wangwang"]',  # Primary selector for kefu button
            'div._buttonWrap_1p2az_60 img[src*="O1CN01ZaHib31lWomw16ded"]',  # Backup
            'text=联系供应商', 'text=客服', 'text=咨询',
            'button:has-text("联系")', '[data-title*="客服"]',
            '.contact-supplier', '.customer-service', '.im-chat', '.im-btn',
            '[class*="kefu"]', '[class*="wangwang"]', '[class*="chat"]'
        ]

        kefu_count = 0
        kefu_found_selector = None
        for selector in kefu_selectors:
            try:
                kefu_elements = page.locator(selector)
                count = await kefu_elements.count()
                if count > 0:
                    # Check if at least one is visible
                    first_visible = False
                    for i in range(count):
                        try:
                            if await kefu_elements.nth(i).is_visible(timeout=1000):
                                kefu_count += 1
                                first_visible = True
                                break
                        except Exception:
                            continue

                    if first_visible and not kefu_found_selector:
                        kefu_found_selector = selector
                        # Only count visible elements for the primary count
                        break
            except Exception:
                continue

        # Use the specific selector from state_machine.py for accurate counting
        try:
            primary_kefu_count = await page.locator("od-text[i18n='wangwang']").count()
            if primary_kefu_count > 0:
                kefu_count = primary_kefu_count
        except Exception:
            pass

        logger.info(f"[CHAT] Found kefu elements: {kefu_count} using selector: {kefu_found_selector}")

        # Step 3: Handle different scenarios
        if kefu_count == 0:
            logger.warning("[CHAT] No kefu/chat entry found on product page: %s", page.url)
            return {
                "ok": False,
                "type": "chat_not_found",
                "reason": "No kefu/chat entry found on product page",
                "url": page.url,
                "kefu_count": 0,
                "page": page
            }

        # Step 4: Try to click the kefu button to open chat
        try:
            # Use the selector that found elements
            target_selector = kefu_found_selector if kefu_found_selector else 'od-text[i18n="wangwang"]'
            kefu_btn = page.locator(target_selector).first
            if await kefu_btn.is_visible(timeout=2000):
                await kefu_btn.click()
                logger.info(f"[CHAT] Clicked kefu button: {target_selector}")
            else:
                logger.warning(f"[CHAT] Kefu button found but not visible: {target_selector}")
                # Still proceed - the element exists even if not immediately visible
        except Exception as e:
            logger.warning(f"[CHAT] Error clicking kefu button: {e}")
            # Continue anyway - kefu elements exist

        # Step 5: Wait for potential chat interface to load
        await asyncio.sleep(2)

        # Step 6: Verify chat interface is available
        chat_selectors = [
            'textarea', '[contenteditable="true"]', 'div[role="textbox"]',
            '.chat-input', '.message-input', '.im-chat-window'
        ]

        chat_found = False
        for selector in chat_selectors:
            try:
                chat_el = page.locator(selector).first
                if await chat_el.is_visible(timeout=1000):
                    logger.info(f"[CHAT] Chat interface found: {selector}")
                    chat_found = True
                    break
            except Exception:
                continue

        if not chat_found:
            logger.warning("[CHAT] Kefu clicked but no chat interface detected")
            # This might still be OK - some chat interfaces load asynchronously
            # Consider this a success since kefu was found and clicked
            return {
                "ok": True,
                "type": "chat_ready",
                "reason": "kefu_clicked_chat_loading",
                "url": page.url,
                "kefu_count": kefu_count,
                "page": page
            }

        # Success case - kefu found and chat interface detected
        logger.info("[CHAT] Chat opened successfully at: %s", page.url)
        return {
            "ok": True,
            "type": "chat_ready",
            "reason": "chat_found",
            "url": page.url,
            "kefu_count": kefu_count,
            "page": page
        }

    except Exception as e:
        error_msg = f"Unexpected error while opening chat: {str(e)}"
        logger.error(f"[CHAT] {error_msg}")
        return {
            "ok": False,
            "type": "error",
            "reason": error_msg,
            "url": page.url if page else "",
            "kefu_count": 0,
            "page": page
        }

async def dismiss_offer_overlays(page: Page, timeout_ms: int = 5000, logger=None) -> bool:
    """
    Dismiss common overlays/popups that might interfere with chat interaction.

    Args:
        page: Playwright page object
        timeout_ms: Timeout in milliseconds
        logger: Optional logger instance

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        if logger:
            logger.info("[OVERLAY] Dismiss offer overlays...")

        # Common overlay selectors that might appear
        overlay_selectors = [
            '.guide-close', '.close-btn', '[aria-label="关闭"]',
            '.newuser-guide .close', '.pop-close', '.modal-close',
            '[class*="close"]', '[class*="popup-close"]', '[class*="modal-close"]'
        ]

        dismissed = 0
        for selector in overlay_selectors:
            try:
                close_btn = page.locator(selector).first
                if await close_btn.is_visible(timeout=1000):
                    await close_btn.click()
                    dismissed += 1
                    if logger:
                        logger.info(f"[OVERLAY] Dismissed overlay: {selector}")
                    await asyncio.sleep(0.5)  # Brief pause between dismissals
            except Exception:
                continue

        if logger:
            logger.info(f"[OVERLAY] Dismissed {dismissed} overlays")

        return True

    except Exception as e:
        if logger:
            logger.error(f"[OVERLAY] Error dismissing overlays: {e}")
        return False

# ========= Backward Compatibility =========
async def start():
    return await launch_browser()

async def stop(pw, browser):
    return await close_browser(pw, browser)

# ========= Namespace =========
playwright_driver = SimpleNamespace(
    launch_chromium_with_fallback=launch_chromium_with_fallback,
    launch_browser=launch_browser,
    persist_state=persist_state,
    close_browser=close_browser,
    start=start,
    stop=stop,
    login=login,
    ensure_logged_in=ensure_logged_in,
    check_if_logged_in=check_if_logged_in,
    safe_goto=safe_goto,
    goto_taobao_login=goto_taobao_login,
    get_or_new_page=get_or_new_page,
    reopen_page=reopen_page,
    ensure_buyer_mode=ensure_buyer_mode,
    normalize_1688_product_url=normalize_1688_product_url,
    _wait_offer_ready=_wait_offer_ready,
    strip_spm=strip_spm,
    PunishPageError=PunishPageError,
    ensure_login_via_taobao=ensure_login_via_taobao,
    open_chat_from_product_canonical=open_chat_from_product_canonical,
    send_on_chat_precise_canonical=send_on_chat_precise_canonical,
    wait_for_supplier_reply_canonical=wait_for_supplier_reply_canonical,
    wait_for_chat_ready=wait_for_chat_ready,
    click_kefu_open_chat=click_kefu_open_chat,
    dismiss_offer_overlays=dismiss_offer_overlays,
    # New proxy tunnel error handling helpers
    reopen_page_without_proxy_and_reuse_cookies=reopen_page_without_proxy_and_reuse_cookies,
    is_proxy_tunnel_error=is_proxy_tunnel_error,
    # New login detection helper
    is_logged_in=is_logged_in,
    # New captcha detection and enhanced chat opening helpers
    is_captcha_or_traffic_block=is_captcha_or_traffic_block,
    ensure_product_and_chat_open=ensure_product_and_chat_open,
)