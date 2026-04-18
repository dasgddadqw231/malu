/**
 * Playwright script to capture all Malu dashboard pages for user manual.
 * Usage: npx playwright test docs/capture-screenshots.mjs
 *   or:  node docs/capture-screenshots.mjs
 */
import { chromium } from 'playwright';
import { mkdirSync } from 'fs';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const SCREENSHOT_DIR = resolve(__dirname, 'screenshots');
mkdirSync(SCREENSHOT_DIR, { recursive: true });

const BASE = 'http://localhost:3000';

const PAGES = [
  { name: '01_home',           path: '/',           title: '홈 대시보드' },
  { name: '02_trades',         path: '/trades',     title: '수동 트레이드' },
  { name: '03_bot_trades',     path: '/bot-trades', title: '봇 트레이드' },
  { name: '04_signature_list', path: '/diy',        title: '시그니처 목록' },
  { name: '05_signature_new',  path: '/diy/new',    title: '새 시그니처 생성' },
  { name: '06_backtest',       path: '/backtest',   title: '백테스트' },
  { name: '07_deploy',         path: '/deploy',     title: '봇 배포' },
  { name: '08_datasets',       path: '/datasets',   title: '데이터셋' },
];

async function run() {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    deviceScaleFactor: 2,
    colorScheme: 'dark',
  });

  for (const pg of PAGES) {
    const page = await context.newPage();
    console.log(`📸 Capturing ${pg.name} (${pg.path}) ...`);

    try {
      await page.goto(`${BASE}${pg.path}`, { waitUntil: 'networkidle', timeout: 15000 });
    } catch {
      // networkidle can timeout on polling pages, fall back to load
      await page.goto(`${BASE}${pg.path}`, { waitUntil: 'load', timeout: 10000 });
    }

    // Wait a bit for animations / data loading
    await page.waitForTimeout(2000);

    await page.screenshot({
      path: resolve(SCREENSHOT_DIR, `${pg.name}.png`),
      fullPage: true,
    });

    await page.close();
    console.log(`  ✅ ${pg.name}.png saved`);
  }

  await browser.close();
  console.log(`\n🎉 Done! Screenshots saved to ${SCREENSHOT_DIR}`);
}

run().catch((err) => {
  console.error('❌ Error:', err);
  process.exit(1);
});
