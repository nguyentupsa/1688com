import os, asyncio
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from playwright.async_api import async_playwright, Page, Frame, TimeoutError as PWTimeoutError
import re
from urllib.parse import urlparse, parse_qs, parse_qsl, urlsplit, urlunsplit, urlencode
from typing import Union
import logging
import random

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
    """Check login status - BETTER detection."""
    try:
        # Check cookies first - fastest
        cookies = await page.context.cookies()
        cookie_names = {c.get("name") for c in cookies}

        # More comprehensive cookie check
        login_cookies = ['UC1', 'cna', '_tb_token_', 'login_aliyun', 'cookie2']
        if any(cookie in cookie_names for cookie in login_cookies):
            logger.info("[LOGIN] Login detected via cookies")
            return True

        # Check URL for login indicators
        current_url = page.url or ""
        if any(indicator in current_url for indicator in ['member.1688.com', 'work.1688.com', 'my.1688.com']):
            logger.info(f"[LOGIN] Login detected via URL: {current_url}")
            return True

        # Minimal UI check - only reliable indicators
        try:
            # Check for logout link - very reliable
            logout_link = await page.query_selector('a[href*="logout"]')
            if logout_link:
                logger.info("[LOGIN] Login detected via logout link")
                return True

            # Check for user avatar/nickname
            user_elements = [
                '.member-nickname',
                '.user-name',
                '.nickname',
                'img[alt*="avatar"]'
            ]

            for selector in user_elements:
                if await page.query_selector(selector):
                    logger.info(f"[LOGIN] Login detected via element: {selector}")
                    return True
        except Exception:
            pass

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

# ========= Browser Launch - ABSOLUTELY NATURAL =========
async def launch_browser():
    """
    Launch browser like human but WITH proxy (tested working).
    """
    pw = await async_playwright().start()

    try:
        logger.info("[BROWSER] Launching Chrome with proxy")

        # Use proxy - it's working well for 1688.com
        proxy_config = {
            "server": "http://svhn3.proxy3g.com:17320",
            "username": "nhocqn",
            "password": "sang789"
        }

        browser = await pw.chromium.launch(
            headless=False,
            proxy=proxy_config
            # Keep minimal - no automation flags
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
            browser = await pw.chromium.launch(headless=False)
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

# ========= Backward Compatibility =========
async def start():
    return await launch_browser()

async def stop(pw, browser):
    return await close_browser(pw, browser)

# ========= Namespace =========
playwright_driver = SimpleNamespace(
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
)