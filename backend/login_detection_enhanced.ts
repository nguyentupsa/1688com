import { Page } from 'playwright';

/**
 * Enhanced Login Detection for Taobao/1688 Negotiation Bot
 * Optimized for 1688.com cookie-based detection and improved DOM selectors
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
 * Check for 1688-specific authentication cookies
 * This is the most reliable method for detecting login on 1688.com
 */
export async function has1688AuthCookies(page: Page): Promise<boolean> {
  try {
    // Critical auth cookies for 1688.com
    const authCookieNames = [
      'tracknick',     // Main user tracking cookie
      'lgc',           // Login cookie
      '_tb_token_',   // Taobao token
      'cookie2',       // Session cookie
      'uc1',           // User cookie 1
      'uc3',           // User cookie 3
      'isg',           // ISG cookie
      'l'              // Legacy cookie
    ];

    const domains = ['.1688.com', '.taobao.com', '.tmall.com'];
    const cookies = await page.context().cookies();

    for (const cookie of cookies) {
      if (authCookieNames.includes(cookie.name) &&
          domains.some(domain => cookie.domain?.endsWith(domain))) {
        console.debug(`[LOGIN] Found auth cookie: ${cookie.name} from domain ${cookie.domain}`);
        return true;
      }
    }

    return false;

  } catch (error) {
    console.debug(`[LOGIN] Error checking 1688 auth cookies: ${error}`);
    return false;
  }
}

/**
 * Check for login/register buttons specifically on 1688.com
 */
export async function has1688LoginButtonsVisible(page: Page): Promise<boolean> {
  try {
    // Common 1688 login button selectors
    const loginButtonSelectors = [
      'text=/登录|请登录|免费注册/i',
      'a[href*="login"]',
      'a[href*="register"]',
      'button:has-text("登录")',
      'button:has-text("注册")',
      '.login-btn',
      '.register-btn',
      '.sign-in-btn',
      '[data-spm*="login"]'
    ];

    for (const selector of loginButtonSelectors) {
      try {
        const elements = await page.locator(selector).count();
        if (elements > 0) {
          // Check if any are actually visible
          for (let i = 0; i < Math.min(elements, 3); i++) {
            if (await page.locator(selector).nth(i).isVisible()) {
              console.debug(`[LOGIN] Found visible login button: ${selector}`);
              return true;
            }
          }
        }
      } catch (error) {
        continue;
      }
    }

    return false;

  } catch (error) {
    console.debug(`[LOGIN] Error checking 1688 login buttons: ${error}`);
    return false;
  }
}

/**
 * Check for 1688-specific logged-in DOM indicators
 */
export async function has1688DomIndicators(page: Page): Promise<boolean> {
  try {
    // Enhanced selectors for 1688.com user indicators
    const loggedInSelectors = [
      // Greetings and user info (Chinese)
      'text=/您好|你好|早上好|下午好|晚上好/i',

      // Logout links and buttons
      'text=/退出登录|退出 登陆|退出/i',
      'a[href*="logout"]',

      // User-specific elements
      '.member-nickname',
      '.member-name',
      '.user-name',
      '.user-info',
      '.user-profile',

      // Avatar and user images
      '.avatar',
      'img[alt*="avatar"]',
      'img[alt*="用户"]',
      '[class*="avatar"]',
      '[class*="user"]',

      // User-specific data attributes
      '[data-role*="user"]',
      '[data-spm*="user"]',

      // 1688 specific elements
      '.safeframe-user-info',
      '.user-operate',
      '.login-info'
    ];

    for (const selector of loggedInSelectors) {
      try {
        const elements = await page.locator(selector).count();
        if (elements > 0) {
          // Check if any are actually visible
          for (let i = 0; i < Math.min(elements, 3); i++) {
            if (await page.locator(selector).nth(i).isVisible()) {
              console.debug(`[LOGIN] Found visible logged-in indicator: ${selector}`);
              return true;
            }
          }
        }
      } catch (error) {
        continue;
      }
    }

    return false;

  } catch (error) {
    console.debug(`[LOGIN] Error checking 1688 DOM indicators: ${error}`);
    return false;
  }
}

/**
 * Check if page has login/register buttons visible (general case)
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
    console.debug(`Error checking login buttons: ${error}`);
  }

  return false;
}

/**
 * Check if page has logged-in user indicators (general case)
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
 * Check if logged-in cookies exist (general case)
 */
export async function hasLoggedInCookies(page: Page): Promise<boolean> {
  const loggedInCookieNames = [
    'tracknick',
    'lgc',
    '_tb_token_',
    'cookie2',
    'uc1',
    'uc3',
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

  // Must be on normal page (not login/verify) AND match logged-in patterns
  return !isOnLoginOrVerifyPage(lowercaseUrl) &&
         loggedInPatterns.some(pattern => lowercaseUrl.includes(pattern));
}

/**
 * ENHANCED LOGIN DETECTOR - Optimized for 1688.com cookie-based detection
 *
 * Rules:
 * 1. ALWAYS false on login/verify pages
 * 2. On www.1688.com: Check auth cookies first, then DOM indicators
 * 3. Only treat as NOT logged in if login buttons visible AND no auth cookies
 * 4. Enhanced DOM selectors for 1688.com
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

    // Parse URL for better analysis
    const parsedUrl = new URL(currentUrl);
    const hostname = parsedUrl.hostname || '';

    // Enhanced detection for 1688.com main site
    if (hostname.endsWith("1688.com") && !hostname.startsWith("login.")) {
      console.log(`[LOGIN] On 1688.com main site - prioritizing cookie detection`);

      // Rule 2a: Check auth cookies FIRST (most reliable on 1688.com)
      const authCookies = await has1688AuthCookies(page);
      if (authCookies) {
        console.log(`[LOGIN] 1688 auth cookies detected – marking as logged in: ${currentUrl}`);
        return true;
      }

      // Rule 2b: Only check for login buttons if no auth cookies found
      const loginButtonsVisible = await has1688LoginButtonsVisible(page);
      if (loginButtonsVisible) {
        console.log(`[LOGIN] Login/register buttons visible on 1688.com + no auth cookies - NOT logged in: ${currentUrl}`);
        return false;
      }

      // Rule 2c: Check DOM indicators for 1688.com (greetings, logout)
      const domIndicators = await has1688DomIndicators(page);
      if (domIndicators) {
        console.log(`[LOGIN] 1688 DOM indicators found - marking as logged in: ${currentUrl}`);
        return true;
      }

      // Rule 2d: If we're on 1688.com main site without login buttons, assume logged in
      console.log(`[LOGIN] On 1688.com main site without login buttons - assuming logged in: ${currentUrl}`);
      return true;
    }

    // Rule 3: Check URL indicators for other sites (taobao.com, etc.)
    if (isLoggedInUrl(currentUrl)) {
      console.log(`[LOGIN] Likely logged in - URL indicates logged-in state: ${currentUrl}`);

      // Check auth cookies for these sites too
      if (await hasLoggedInCookies(page)) {
        console.log(`[LOGIN] Auth cookies confirm login status: ${currentUrl}`);
        return true;
      }
    }

    // Rule 4: Check for login buttons (NOT logged in indicator)
    if (await hasLoginButtonsVisible(page)) {
      console.log(`[LOGIN] Login/register buttons visible - NOT logged in: ${currentUrl}`);
      return false;
    }

    // Rule 5: Check for logged-in DOM indicators
    if (await hasLoggedInIndicators(page)) {
      console.log(`[LOGIN] Logged in - DOM indicators found: ${currentUrl}`);
      return true;
    }

    // Rule 6: Check for logged-in cookies (general fallback)
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

    const parsedUrl = new URL(currentUrl);
    const hostname = parsedUrl.hostname || '';

    if (hostname.endsWith("1688.com") && !hostname.startsWith("login.")) {
      const hasAuthCookies = await has1688AuthCookies(page);
      if (hasAuthCookies) {
        return `1688 auth cookies detected on: ${currentUrl}`;
      }

      const hasLoginButtons = await has1688LoginButtonsVisible(page);
      if (hasLoginButtons) {
        return `Login buttons visible on 1688.com: ${currentUrl}`;
      }

      const hasDomIndicators = await has1688DomIndicators(page);
      if (hasDomIndicators) {
        return `1688 DOM indicators found on: ${currentUrl}`;
      }

      return `On 1688.com without clear login state: ${currentUrl}`;
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
  has1688AuthCookies,
  has1688LoginButtonsVisible,
  has1688DomIndicators,
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
  has1688AuthCookies,
  has1688LoginButtonsVisible,
  has1688DomIndicators,
  hasLoggedInIndicators,
  hasLoginButtonsVisible,
  hasLoggedInCookies,
  isLoggedInUrl,
  getLoginStateDescription
};