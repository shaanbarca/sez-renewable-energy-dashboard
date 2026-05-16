#!/usr/bin/env node
/**
 * Headless browser console + error capture for the dashboard.
 *
 * Spins up a Chromium instance via Playwright, opens the local dev server,
 * optionally clicks a site to trigger the map render path, and prints every
 * console message, page error, request failure, and unhandled promise
 * rejection to stdout. Exits non-zero if any error-level events landed.
 *
 * Usage:
 *
 *   # default: opens localhost:5173, waits for map idle, dumps console
 *   node scripts/capture-console.mjs
 *
 *   # pick a site by site_id to exercise the selectSite path
 *   node scripts/capture-console.mjs --site indonesia-morowali-industrial-park-imip
 *
 *   # different port / hostname
 *   node scripts/capture-console.mjs --url http://localhost:5174
 *
 *   # keep the browser open + visible for manual inspection
 *   node scripts/capture-console.mjs --headed --keep-open
 *
 *   # screenshot the rendered map (useful for "is the map black?" debugging)
 *   node scripts/capture-console.mjs --screenshot /tmp/dashboard.png
 *
 * Exit codes:
 *   0  no errors captured
 *   1  one or more errors / pageerrors / unhandled rejections fired
 *   2  network unreachable / timeout
 *
 * Why this exists: faster than copy-pasting from Chrome DevTools, and
 * scriptable from a CI / agent loop. See `scripts/check-dashboard-console.sh`
 * for a convenience wrapper.
 */

import { chromium } from 'playwright';

const args = process.argv.slice(2);
const flag = (name, defaultValue) => {
  const idx = args.indexOf(name);
  if (idx === -1) return defaultValue;
  // value flag (--url X) vs boolean flag (--headed)
  const next = args[idx + 1];
  if (next && !next.startsWith('--')) return next;
  return true;
};

const URL = flag('--url', 'http://localhost:5173');
const SITE_ID = flag('--site', null);
const HEADED = flag('--headed', false);
const KEEP_OPEN = flag('--keep-open', false);
const SCREENSHOT = flag('--screenshot', null);
const WAIT_MS = parseInt(flag('--wait', '6000'), 10);

const COLOR = {
  red: (s) => `\x1b[31m${s}\x1b[0m`,
  yellow: (s) => `\x1b[33m${s}\x1b[0m`,
  green: (s) => `\x1b[32m${s}\x1b[0m`,
  cyan: (s) => `\x1b[36m${s}\x1b[0m`,
  dim: (s) => `\x1b[2m${s}\x1b[0m`,
};

const events = {
  errors: [],
  warnings: [],
  pageerrors: [],
  unhandled: [],
  failed_requests: [],
  log_count: 0,
};

async function main() {
  const browser = await chromium.launch({ headless: !HEADED });
  const context = await browser.newContext({
    viewport: { width: 1920, height: 1200 },
    deviceScaleFactor: 2,
  });
  const page = await context.newPage();

  // Capture EVERY console message. type() is one of:
  //   log / info / debug / warn / error / dir / table / trace / clear / etc.
  page.on('console', (msg) => {
    const type = msg.type();
    const text = msg.text();
    const loc = msg.location();
    const where = loc.url ? `${loc.url}:${loc.lineNumber}` : '';
    if (type === 'error') {
      events.errors.push({ text, where });
      console.log(COLOR.red(`[console.error] ${text}`));
      if (where) console.log(COLOR.dim(`    at ${where}`));
    } else if (type === 'warning') {
      events.warnings.push({ text, where });
      console.log(COLOR.yellow(`[console.warn]  ${text}`));
    } else {
      events.log_count++;
      // Suppress noise: only print log/info when explicitly verbose.
      // Could add --verbose later.
    }
  });

  // Runtime exceptions thrown to window — separate from console.error.
  page.on('pageerror', (err) => {
    events.pageerrors.push({ message: err.message, stack: err.stack });
    console.log(COLOR.red(`[pageerror] ${err.message}`));
    if (err.stack) {
      console.log(COLOR.dim(err.stack.split('\n').slice(0, 5).join('\n')));
    }
  });

  // Unhandled promise rejections.
  page.on('crash', () => {
    events.unhandled.push({ kind: 'page_crash' });
    console.log(COLOR.red('[crash] page crashed'));
  });

  // Failed network requests (CORS, 4xx, 5xx, etc.).
  page.on('requestfailed', (req) => {
    const failure = req.failure();
    events.failed_requests.push({
      url: req.url(),
      method: req.method(),
      reason: failure?.errorText || 'unknown',
    });
    console.log(COLOR.yellow(`[requestfailed] ${req.method()} ${req.url()} — ${failure?.errorText}`));
  });

  // Response errors (4xx / 5xx) — these don't fire requestfailed.
  page.on('response', (res) => {
    if (res.status() >= 400) {
      events.failed_requests.push({
        url: res.url(),
        method: res.request().method(),
        status: res.status(),
      });
      console.log(
        COLOR.yellow(`[response ${res.status()}] ${res.request().method()} ${res.url()}`),
      );
    }
  });

  console.log(COLOR.cyan(`→ navigating to ${URL}`));
  try {
    await page.goto(URL, { waitUntil: 'domcontentloaded', timeout: 15000 });
  } catch (e) {
    console.log(COLOR.red(`navigation failed: ${e.message}`));
    await browser.close();
    process.exit(2);
  }

  // Wait for the map to settle. networkidle is the safest cross-app signal
  // since SPAs vary widely in their ready state markers.
  console.log(COLOR.cyan('→ waiting for networkidle'));
  try {
    await page.waitForLoadState('networkidle', { timeout: 15000 });
  } catch {
    console.log(COLOR.yellow('  (networkidle timeout — proceeding anyway)'));
  }

  // Dismiss the persona-selection / walkthrough modal that opens on first
  // load — it blocks the map and any interaction with markers. Side-effect:
  // first-time runs persist `walkthroughDismissed=true` in localStorage so
  // subsequent runs skip this step automatically.
  const dismissed = await page.evaluate(() => {
    const w = window;
    if (w.useDashboardStore?.getState) {
      const state = w.useDashboardStore.getState();
      if (state.walkthroughDismissed === false && typeof state.dismissWalkthrough === 'function') {
        state.dismissWalkthrough();
        return true;
      }
    }
    return false;
  });
  if (dismissed) {
    console.log(COLOR.cyan('→ dismissed walkthrough modal'));
    await page.waitForTimeout(500); // let React rerender
  }

  if (SITE_ID) {
    console.log(COLOR.cyan(`→ selecting site: ${SITE_ID}`));
    const handled = await page.evaluate(async (id) => {
      const w = window;
      if (w.useDashboardStore?.getState) {
        w.useDashboardStore.getState().selectSite(id);
        return 'store';
      }
      return null;
    }, SITE_ID);
    if (!handled) {
      console.log(COLOR.dim('  (no dev hook; relying on marker click is not implemented yet)'));
    }
    // Reveal the bottom table panel if a screenshot path contains 'table'
    // so we can verify column changes. The "Show" toggle lives at the
    // bottom-center as a sticky button; the click target is whichever
    // element has text exactly equal to 'Show'.
    if (SCREENSHOT && SCREENSHOT.includes('table')) {
      await page.evaluate(() => {
        // Find buttons or clickable spans whose innerText is exactly 'Show'.
        const candidates = Array.from(
          document.querySelectorAll('button, [role="button"], span'),
        );
        const showBtn = candidates.find(
          (el) => (el.textContent || '').trim() === 'Show',
        );
        if (showBtn instanceof HTMLElement) showBtn.click();
      });
      await page.waitForTimeout(1500);
      // Scroll to the bottom so the table is in view for the screenshot.
      await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
      await page.waitForTimeout(500);
    }
    await page.waitForTimeout(WAIT_MS);
  } else {
    // Give the map a moment to render after networkidle.
    await page.waitForTimeout(WAIT_MS);
  }

  if (SCREENSHOT) {
    // For SITE screenshots, clip to the right-side score drawer where the
    // captive comparator + tier pills land. For TABLE / non-SITE, full viewport.
    if (SITE_ID && !SCREENSHOT.includes('table')) {
      await page.screenshot({
        path: SCREENSHOT,
        clip: { x: 1450, y: 0, width: 470, height: 1200 },
      });
    } else {
      await page.screenshot({ path: SCREENSHOT, fullPage: false });
    }
    console.log(COLOR.cyan(`→ screenshot saved to ${SCREENSHOT}`));
  }

  if (SITE_ID) {
    // Capture drawer text content for verification — easier than reading a
    // downsampled screenshot. Greps the rendered DOM for new captive labels
    // so we can confirm M-AT8b changes landed.
    const verifyText = await page.evaluate(() => {
      const body = document.body.textContent || '';
      const matches = [];
      for (const key of ['Captive Power', 'Captive Coal', 'Captive Gas', 'Captive Hydro', 'Grid Cost']) {
        if (body.includes(key)) matches.push(key);
      }
      return matches;
    });
    console.log(COLOR.cyan(`→ labels visible: ${verifyText.join(', ')}`));
  }

  if (KEEP_OPEN) {
    console.log(COLOR.cyan('→ --keep-open set; press Ctrl-C to exit'));
    await new Promise(() => {}); // hang forever
  }

  await browser.close();

  // Summary.
  console.log('\n' + COLOR.cyan('━━━ summary ━━━'));
  console.log(`  console.log/info/debug:  ${events.log_count}`);
  console.log(`  ${events.warnings.length ? COLOR.yellow(`console.warn:            ${events.warnings.length}`) : `console.warn:            0`}`);
  console.log(`  ${events.errors.length ? COLOR.red(`console.error:           ${events.errors.length}`) : COLOR.green(`console.error:           0`)}`);
  console.log(`  ${events.pageerrors.length ? COLOR.red(`pageerror (uncaught):    ${events.pageerrors.length}`) : COLOR.green(`pageerror (uncaught):    0`)}`);
  console.log(`  ${events.failed_requests.length ? COLOR.yellow(`failed/4xx/5xx requests: ${events.failed_requests.length}`) : COLOR.green(`failed requests:         0`)}`);
  console.log(`  ${events.unhandled.length ? COLOR.red(`unhandled/crash:         ${events.unhandled.length}`) : `unhandled/crash:         0`}`);

  const exitCode = events.errors.length || events.pageerrors.length || events.unhandled.length ? 1 : 0;
  process.exit(exitCode);
}

main().catch((err) => {
  console.error('capture-console fatal:', err);
  process.exit(2);
});
