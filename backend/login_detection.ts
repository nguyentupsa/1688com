import { Page } from 'playwright';

/**
 * Robust login detection system for 1688/Taobao negotiation bot
 * Addresses risk-control verification pages and provides indefinite waiting
 */

export interface LoginResult {
  ok: boolean;
  type: 'logged_in' | 'page_closed' | string;
  reason?: string;
  url?: string;
}

/**
 * Check if current URL is a login or verification page
 * These pages should ALWAYS return false for login status
 */
export function isOnLoginOrVerifyPage(url: string): boolean {
  const lowercaseUrl = url.toLowerCase();

  const loginVerifyPatterns = [
    'login.taobao.com',
    'login.1688.com',
    'passport.taobao.com/iv/normal_validate',
    'passport.taobao.com/iv/identity_verify',
    'passport.taobao.com/iv/',
  ];

  return loginVerifyPatterns.some(pattern => lowercaseUrl.includes(pattern));
}

/**
 * Check if page has login/register buttons visible (indicates NOT logged in)
 */
export async function hasLoginButtonsVisible(page: Page): Promise<boolean> {
  const loginButtonSelectors = [
    'text=/登录|请登录|免费注册/i',
    'a[href*="login"]',
    'button:has-text("登录")',
    '.login-btn',
    '.sign-in-btn'
  ];

  try {
    for (const selector of loginButtonSelectors) {
      const elements = await page.locator(selector).count();
      if (elements > 0) {
        const firstVisible = await page.locator(selector).first().isVisible();
        if (firstVisible) {
          return true;
        }
      }
    }
  } catch (error) {
    // If we can't check, assume no visible login buttons
    console.debug(`Error checking login buttons: ${error}`);
  }

  return false;
}

/**
 * Check if page has logged-in user indicators
 */
export async function hasLoggedInIndicators(page: Page): Promise<boolean> {
  const loggedInSelectors = [
    'text=/退出登录|退出 登陆|退出/i',
    'text=/您好|你好/i',
    '.member-nickname',
    '.member-name',
    '.user-name',
    '.user-info',
    '.avatar',
    'a[href*="logout"]',
    'img[alt*="avatar"]',
    '[data-role*="user"]',
    '.user-profile'
  ];

  try {
    for (const selector of loggedInSelectors) {
      const elements = await page.locator(selector).count();
      if (elements > 0) {
        const firstVisible = await page.locator(selector).first().isVisible();
        if (firstVisible) {
          return true;
        }
      }
    }
  } catch (error) {
    console.debug(`Error checking logged-in indicators: ${error}`);
  }

  return false;
}

/**
 * Check if logged-in cookies exist in browser
 */
export async function hasLoggedInCookies(page: Page): Promise<boolean> {
  const loggedInCookieNames = [
    'tracknick',
    'lgc',
    '_tb_token_',
    'cookie2',
    'uc1',
    'uc3',
    'lgc',
    'isg',
    'l'
  ];

  const domains = ['.1688.com', '.taobao.com', '.tmall.com'];

  try {
    const cookies = await page.context().cookies();

    return cookies.some(cookie =>
      loggedInCookieNames.includes(cookie.name) &&
      domains.some(domain => cookie.domain?.endsWith(domain))
    );
  } catch (error) {
    console.debug(`Error checking cookies: ${error}`);
    return false;
  }
}

/**
 * Check if URL indicates logged-in state
 */
export function isLoggedInUrl(url: string): boolean {
  const lowercaseUrl = url.toLowerCase();

  const loggedInPatterns = [
    'www.1688.com',
    'my.1688.com',
    'work.1688.com',
    'member.1688.com',
    'cart.1688.com',
    'order.1688.com',
    'www.taobao.com',
    'my.taobao.com',
    'member1.taobao.com',
    'trade.taobao.com',
    'cart.taobao.com'
  ];

  // Must be on a normal page (not login/verify) AND match logged-in patterns
  return !isOnLoginOrVerifyPage(lowercaseUrl) &&
         loggedInPatterns.some(pattern => lowercaseUrl.includes(pattern));
}

/**
 * MAIN LOGIN DETECTOR - Robust login status checking
 *
 * Rules:
 * 1. ALWAYS false if on login/verify pages
 * 2. ONLY true when on normal pages AND has login indicators
 * 3. False if login buttons are visible
 *
 * @param page Playwright page instance
 * @returns true if logged in, false otherwise
 */
export async function isLoggedIn(page: Page): Promise<boolean> {
  try {
    const currentUrl = page.url || '';

    console.debug(`[LOGIN] Checking login status for URL: ${currentUrl}`);

    // Rule 1: ALWAYS false on login/verify pages
    if (isOnLoginOrVerifyPage(currentUrl)) {
      console.log(`[LOGIN] NOT logged in - on login/verify page: ${currentUrl}`);
      return false;
    }

    // Rule 2: False if login/register buttons are visible
    if (await hasLoginButtonsVisible(page)) {
      console.log(`[LOGIN] NOT logged in - login buttons visible: ${currentUrl}`);
      return false;
    }

    // Rule 3: Check URL indicators (fast check)
    if (isLoggedInUrl(currentUrl)) {
      console.log(`[LOGIN] Likely logged in - URL indicates logged-in state: ${currentUrl}`);
      // Continue to verify with DOM elements
    }

    // Rule 4: Check for logged-in DOM indicators
    if (await hasLoggedInIndicators(page)) {
      console.log(`[LOGIN] Logged in - DOM indicators found: ${currentUrl}`);
      return true;
    }

    // Rule 5: Check for logged-in cookies (fallback)
    if (await hasLoggedInCookies(page)) {
      console.log(`[LOGIN] Logged in - cookies indicate logged-in state: ${currentUrl}`);
      return true;
    }

    // Default: not logged in
    console.log(`[LOGIN] NOT logged in - no indicators found: ${currentUrl}`);
    return false;

  } catch (error) {
    console.error(`[LOGIN] Error checking login status: ${error}`);
    return false;
  }
}

/**
 * Wait indefinitely until user is logged in
 * NO FIXED TIMEOUT - relies entirely on login detection
 *
 * @param page Playwright page instance
 * @param logger Logger function (optional)
 * @returns LoginResult with status details
 */
export async function waitUntilLoggedIn(
  page: Page,
  logger: (message: string) => void = console.log
): Promise<LoginResult> {
  const checkInterval = 2000; // 2 seconds

  logger('[LOGIN] Starting indefinite wait for login completion...');

  while (true) {
    // Check if page is closed
    if (page.isClosed()) {
      const result: LoginResult = {
        ok: false,
        type: 'page_closed',
        reason: 'Page was closed while waiting for login'
      };
      logger('[LOGIN] Page closed while waiting for login');
      return result;
    }

    try {
      const currentUrl = page.url;
      const loggedIn = await isLoggedIn(page);

      if (loggedIn) {
        const result: LoginResult = {
          ok: true,
          type: 'logged_in',
          url: currentUrl,
          reason: 'Successfully logged in'
        };
        logger(`[LOGIN] Login detected! URL: ${currentUrl}`);
        return result;
      }

      // Log current state
      if (isOnLoginOrVerifyPage(currentUrl)) {
        logger(`[LOGIN] Still on login/verify page: ${currentUrl}`);
      } else {
        logger(`[LOGIN] On non-login page but not logged in yet: ${currentUrl}`);
      }

    } catch (error) {
      logger(`[LOGIN] Error during login check: ${error}`);
      // Continue waiting even if there's an error
    }

    // Wait before next check
    await new Promise(resolve => setTimeout(resolve, checkInterval));
  }
}

/**
 * Helper function to get current login state description
 */
export async function getLoginStateDescription(page: Page): Promise<string> {
  try {
    const currentUrl = page.url;

    if (isOnLoginOrVerifyPage(currentUrl)) {
      return `On login/verify page: ${currentUrl}`;
    }

    if (await hasLoginButtonsVisible(page)) {
      return `Login buttons visible on: ${currentUrl}`;
    }

    if (await hasLoggedInIndicators(page)) {
      return `Logged in (DOM indicators) on: ${currentUrl}`;
    }

    if (await hasLoggedInCookies(page)) {
      return `Logged in (cookies) on: ${currentUrl}`;
    }

    if (isLoggedInUrl(currentUrl)) {
      return `URL indicates logged in but no DOM confirmation: ${currentUrl}`;
    }

    return `Unknown login state on: ${currentUrl}`;

  } catch (error) {
    return `Error determining login state: ${error}`;
  }
}

/**
 * Export all functions for external use
 */
export default {
  isLoggedIn,
  waitUntilLoggedIn,
  isOnLoginOrVerifyPage,
  hasLoggedInIndicators,
  hasLoginButtonsVisible,
  hasLoggedInCookies,
  isLoggedInUrl,
  getLoginStateDescription
};

// Also export individual functions for TypeScript imports
export {
  isLoggedIn,
  waitUntilLoggedIn,
  isOnLoginOrVerifyPage,
  hasLoggedInIndicators,
  hasLoginButtonsVisible,
  hasLoggedInCookies,
  isLoggedInUrl,
  getLoginStateDescription
};