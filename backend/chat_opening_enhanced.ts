import { Page } from 'playwright';

/**
 * Enhanced Chat Opening Logic for 1688 Negotiation Bot
 * Handles Alibaba captcha interception and prevents NoneType errors
 */

export interface ChatOpeningResult {
  ok: boolean;
  type: 'chat_ready' | 'blocked_by_captcha' | 'chat_not_found' | 'error';
  reason?: string;
  url: string;
  kefuCount: number;
  page: Page;
}

export interface KefuInfo {
  found: boolean;
  selector: string | null;
  count: number;
  firstVisible: boolean;
  elements: Array<{selector: string, index: number}>;
  error?: string;
}

export interface ClickResult {
  success: boolean;
  reason: string;
  selector: string | null;
}

/**
 * Enhanced detection for Alibaba captcha/unusual traffic block pages
 */
export async function isCaptchaOrTrafficBlock(page: Page): Promise<boolean> {
  try {
    const url = page.url || '';
    let title = '';
    let bodyText = '';

    // PRIMARY: Check for baxia-punish captcha container (most reliable)
    try {
      const captchaSelector = '#baxia-punish > div.wrapper > div > div.bannar > div.captcha-tips > div:nth-child(1)';
      const captchaElement = page.locator(captchaSelector);
      const count = await captchaElement.count();

      if (count > 0) {
        // Check if it's actually visible or exists in DOM
        try {
          if (await captchaElement.isVisible({ timeout: 1000 })) {
            const captchaText = await captchaElement.innerText();
            console.warn(`[CAPTCHA] Detected baxia-punish captcha container: ${captchaText.substring(0, 100)}...`);
            return true;
          }
        } catch (error) {
          // Element exists in DOM even if not fully visible
          console.warn('[CAPTCHA] Detected baxia-punish captcha container in DOM');
          return true;
        }
      }
    } catch (error) {
      // Continue with other detection methods
    }

    // Check URL patterns (secondary)
    if (url.includes('anti_robot')) {
      console.warn(`[CAPTCHA] Detected anti_robot URL: ${url}`);
      return true;
    }

    if (url.toLowerCase().includes('captcha')) {
      console.warn(`[CAPTCHA] Detected captcha URL: ${url}`);
      return true;
    }

    if (url.toLowerCase().includes('verify') && url.includes('1688.com')) {
      console.warn(`[CAPTCHA] Detected 1688 verification URL: ${url}`);
      return true;
    }

    try {
      title = await page.title();
    } catch (error) {
      // Ignore errors
    }

    try {
      bodyText = await page.innerText('body');
    } catch (error) {
      // Ignore errors
    }

    // Enhanced heuristics for Alibaba captcha / unusual traffic pages (fallback)
    if (title.includes('Captcha Interception')) {
      console.warn(`[CAPTCHA] Detected by title: ${title}`);
      return true;
    }

    if (bodyText.toLowerCase().includes('unusual traffic from your network')) {
      console.warn('[CAPTCHA] Detected by body text: unusual traffic from your network');
      return true;
    }

    if (bodyText.toLowerCase().includes('detected unusual traffic from your network')) {
      console.warn('[CAPTCHA] Detected by body text: detected unusual traffic from your network');
      return true;
    }

    if (bodyText.toLowerCase().includes('sorry, we have detected unusual traffic')) {
      console.warn('[CAPTCHA] Detected by body text: sorry, we have detected unusual traffic');
      return true;
    }

    if (bodyText.toLowerCase().includes('please slide to verify')) {
      console.warn('[CAPTCHA] Detected by body text: please slide to verify');
      return true;
    }

    if (bodyText.includes('访问异常') || bodyText.includes('异常流量')) {
      console.warn('[CAPTCHA] Detected by Chinese text: 访问异常/异常流量');
      return true;
    }

    if (bodyText.includes('验证') && bodyText.toLowerCase().includes('robot')) {
      console.warn('[CAPTCHA] Detected by Chinese text: 验证/robot');
      return true;
    }

    if (bodyText.includes('人机验证') || bodyText.includes('滑块验证')) {
      console.warn('[CAPTCHA] Detected by Chinese text: 人机验证/滑块验证');
      return true;
    }

    // URL-based detection (redundant check since we already checked above)
    if (url.toLowerCase().includes('captcha') && url.includes('1688.com')) {
      console.warn(`[CAPTCHA] Detected 1688 captcha URL: ${url}`);
      return true;
    }

    return false;

  } catch (error) {
    console.error(`[CAPTCHA] Error detecting captcha page: ${error}`);
    return false;
  }
}

/**
 * Safely find kefu/chat elements on a product page
 * Returns structured result instead of null to prevent attribute errors
 */
export async function findKefuOnProductPage(page: Page, logger?: (message: string) => void): Promise<KefuInfo> {
  const log = logger || console.log;

  try {
    log('[KEFU] Searching for kefu/chat elements on product page');

    // Common kefu/chat button selectors on 1688 product pages
    const kefuSelectors = [
      'od-text[i18n="wangwang"]',  // Primary selector for kefu button
      'div._buttonWrap_1p2az_60 img[src*="O1CN01ZaHib31lWomw16ded"]',  // Backup
      'text=联系供应商', 'text=客服', 'text=咨询',
      'button:has-text("联系")', '[data-title*="客服"]',
      '.contact-supplier', '.customer-service', '.im-chat', '.im-btn',
      '[class*="kefu"]', '[class*="wangwang"]', '[class*="chat"]'
    ];

    const result: KefuInfo = {
      found: false,
      selector: null,
      count: 0,
      firstVisible: false,
      elements: []
    };

    // Search for kefu elements
    for (const selector of kefuSelectors) {
      try {
        const elements = page.locator(selector);
        const count = await elements.count();

        if (count > 0) {
          // Check if any are visible
          let visibleCount = 0;
          for (let i = 0; i < Math.min(count, 3); i++) {
            try {
              if (await elements.nth(i).isVisible({ timeout: 1000 })) {
                visibleCount += 1;
                if (!result.firstVisible) {
                  result.firstVisible = true;
                }
              }
            } catch (error) {
              continue;
            }
          }

          if (visibleCount > 0) {
            result.found = true;
            result.selector = selector;
            result.count = visibleCount;
            result.elements = Array.from({ length: visibleCount }, (_, i) => ({ selector, index: i }));
            log(`[KEFU] Found ${visibleCount} kefu elements with selector: ${selector}`);
            break;
          }
        }
      } catch (error) {
        console.debug(`[KEFU] Error checking selector ${selector}: ${error}`);
        continue;
      }
    }

    if (!result.found) {
      log('[KEFU] No kefu/chat elements found on product page');
    }

    return result;

  } catch (error) {
    const errorMsg = `Error searching for kefu elements: ${error}`;
    console.error(`[KEFU] ${errorMsg}`);
    return {
      found: false,
      selector: null,
      count: 0,
      firstVisible: false,
      elements: [],
      error: errorMsg
    };
  }
}

/**
 * Safely click kefu button using structured kefu information
 * Prevents NoneType errors by validating input first
 */
export async function clickKefuSafely(page: Page, kefuInfo: KefuInfo, logger?: (message: string) => void): Promise<ClickResult> {
  const log = logger || console.log;

  // Validate kefuInfo
  if (!kefuInfo || !kefuInfo.found || !kefuInfo.selector) {
    return {
      success: false,
      reason: 'No valid kefu element found to click',
      selector: null
    };
  }

  try {
    const selector = kefuInfo.selector;
    log(`[KEFU] Attempting to click kefu element: ${selector}`);

    const kefuBtn = page.locator(selector).first;
    if (await kefuBtn.isVisible({ timeout: 3000 })) {
      await kefuBtn.click();
      log(`[KEFU] Successfully clicked kefu button: ${selector}`);
      return {
        success: true,
        reason: 'Kefu button clicked successfully',
        selector: selector
      };
    } else {
      log(`[KEFU] Kefu button found but not visible: ${selector}`);
      return {
        success: false,
        reason: 'Kefu button found but not visible',
        selector: selector
      };
    }

  } catch (error) {
    const errorMsg = `Error clicking kefu button: ${error}`;
    console.error(`[KEFU] ${errorMsg}`);
    return {
      success: false,
      reason: errorMsg,
      selector: kefuInfo.selector || null
    };
  }
}

/**
 * Enhanced function that ensures we're on a valid product page and can open chat
 * Replaces the simple click logic with proper captcha detection and safe kefu handling
 */
export async function ensureProductAndChatReady(
  page: Page,
  productUrl: string,
  timeoutMs: number = 12000,
  logger?: (message: string) => void
): Promise<ChatOpeningResult> {
  const log = logger || console.log;

  try {
    log(`[CHAT] Ensuring product page and chat are ready for: ${productUrl}`);

    // Step 1: Enhanced captcha/traffic block detection (including baxia-punish)
    if (await isCaptchaOrTrafficBlock(page)) {
      log(`[CHAT] Detected Alibaba captcha interception (baxia-punish) on product page: ${page.url()}`);
      return {
        ok: false,
        type: 'blocked_by_captcha',
        reason: 'Alibaba detected unusual traffic (baxia-punish captcha) on the product page. Please solve the slider captcha in the browser or change proxy, then click Retry.',
        url: page.url(),
        kefuCount: 0,
        page: page
      };
    }

    // Step 2: Safely find kefu elements using new function
    const kefuInfo = await findKefuOnProductPage(page, logger);

    // Get primary selector count for consistency
    let primaryKefuCount = 0;
    try {
      primaryKefuCount = await page.locator('od-text[i18n="wangwang"]').count();
    } catch (error) {
      // Ignore errors
    }

    // Use the found count or primary count
    const kefuCount = kefuInfo.found ? kefuInfo.count || 0 : 0;
    const finalKefuCount = primaryKefuCount > 0 ? primaryKefuCount : kefuCount;

    log(`[CHAT] Found kefu elements: ${finalKefuCount} (info: found=${kefuInfo.found})`);

    // Step 3: Handle different scenarios
    if (!kefuInfo || !kefuInfo.found) {
      log(`[CHAT] No kefu/chat entry found on product page: ${page.url()}`);
      return {
        ok: false,
        type: 'chat_not_found',
        reason: 'No kefu/chat entry found on product page',
        url: page.url(),
        kefuCount: 0,
        page: page
      };
    }

    // Step 4: Safely click the kefu button
    const clickResult = await clickKefuSafely(page, kefuInfo, logger);
    if (!clickResult.success) {
      log(`[CHAT] Failed to click kefu button: ${clickResult.reason}`);
      // Continue anyway - kefu elements exist, we can try other methods
    }

    // Step 5: Wait for potential chat interface to load
    await new Promise(resolve => setTimeout(resolve, 2000));

    // Step 6: Verify chat interface is available
    const chatSelectors = [
      'textarea', '[contenteditable="true"]', 'div[role="textbox"]',
      '.chat-input', '.message-input', '.im-chat-window'
    ];

    let chatFound = false;
    for (const selector of chatSelectors) {
      try {
        const chatEl = page.locator(selector).first;
        if (await chatEl.isVisible({ timeout: 1000 })) {
          log(`[CHAT] Chat interface found: ${selector}`);
          chatFound = true;
          break;
        }
      } catch (error) {
        continue;
      }
    }

    if (!chatFound) {
      log('[CHAT] Kefu clicked but no chat interface detected');
      // This might still be OK - some chat interfaces load asynchronously
      // Consider this a success since kefu was found and clicked
      return {
        ok: true,
        type: 'chat_ready',
        reason: 'kefu_clicked_chat_loading',
        url: page.url(),
        kefuCount: finalKefuCount,
        page: page
      };
    }

    // Success case - kefu found and chat interface detected
    log(`[CHAT] Chat opened successfully at: ${page.url()}`);
    return {
      ok: true,
      type: 'chat_ready',
      reason: 'chat_found',
      url: page.url(),
      kefuCount: finalKefuCount,
      page: page
    };

  } catch (error) {
    const errorMsg = `Error ensuring product and chat ready: ${error}`;
    log(`[CHAT] ${errorMsg}`);
    return {
      ok: false,
      type: 'error',
      reason: errorMsg,
      url: page.url(),
      kefuCount: 0,
      page: page
    };
  }
}

/**
 * Enhanced chat opening with automatic retry and error handling
 */
export async function openChatEnhanced(
  page: Page,
  productUrl: string,
  options: {
    timeoutMs?: number;
    maxRetries?: number;
    logger?: (message: string) => void;
  } = {}
): Promise<ChatOpeningResult> {
  const { timeoutMs = 12000, maxRetries = 3, logger } = options;
  const log = logger || console.log;

  let lastResult: ChatOpeningResult | null = null;

  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    log(`[CHAT] Attempt ${attempt}/${maxRetries} to open chat`);

    try {
      const result = await ensureProductAndChatReady(page, productUrl, timeoutMs, logger);
      lastResult = result;

      if (result.ok) {
        log(`[CHAT] Successfully opened chat on attempt ${attempt}`);
        return result;
      }

      // Handle different error types
      if (result.type === 'blocked_by_captcha') {
        // Don't retry captcha blocks - requires manual intervention
        log(`[CHAT] Blocked by captcha - requires manual intervention`);
        return result;
      }

      if (result.type === 'chat_not_found') {
        log(`[CHAT] Chat not found - retrying... (${attempt}/${maxRetries})`);
        // Wait before retry
        if (attempt < maxRetries) {
          await new Promise(resolve => setTimeout(resolve, 3000));
          continue;
        }
      }

    } catch (error) {
      const errorMsg = `Attempt ${attempt} failed: ${error}`;
      log(`[CHAT] ${errorMsg}`);

      if (attempt === maxRetries) {
        return {
          ok: false,
          type: 'error',
          reason: `Failed after ${maxRetries} attempts: ${error}`,
          url: page.url(),
          kefuCount: 0,
          page: page
        };
      }
    }
  }

  // Return the last result if we get here
  return lastResult || {
    ok: false,
    type: 'error',
    reason: 'Unknown error during chat opening',
    url: page.url(),
    kefuCount: 0,
    page: page
  };
}

// Export all functions
export default {
  isCaptchaOrTrafficBlock,
  findKefuOnProductPage,
  clickKefuSafely,
  ensureProductAndChatReady,
  openChatEnhanced
};

// Also export individual functions for TypeScript imports
export {
  isCaptchaOrTrafficBlock,
  findKefuOnProductPage,
  clickKefuSafely,
  ensureProductAndChatReady,
  openChatEnhanced
};