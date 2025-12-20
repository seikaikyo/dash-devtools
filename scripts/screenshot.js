#!/usr/bin/env node
/**
 * DashAI DevTools - Puppeteer 截圖工具
 *
 * 使用方式：
 *   node screenshot.js <url> [options]
 *
 * 選項：
 *   --output, -o    輸出路徑 (預設: /tmp/screenshot.png)
 *   --wait, -w      等待時間 ms (預設: 3000)
 *   --full          全頁截圖 (預設: true)
 *   --width         視窗寬度 (預設: 1920)
 *   --height        視窗高度 (預設: 1080)
 *   --storage       JSON 格式的 localStorage 設定
 */

const puppeteer = require('puppeteer');

async function screenshot(options) {
  const {
    url,
    output = '/tmp/screenshot.png',
    wait = 3000,
    fullPage = true,
    width = 1920,
    height = 1080,
    storage = {}
  } = options;

  console.log('[Screenshot] Starting browser...');
  const browser = await puppeteer.launch({
    headless: 'new',
    executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-gpu']
  });

  try {
    const page = await browser.newPage();
    await page.setViewport({ width, height });

    console.log('[Screenshot] Navigating to:', url);
    await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 30000 });

    // 設定 localStorage
    if (Object.keys(storage).length > 0) {
      console.log('[Screenshot] Setting localStorage...');
      await page.evaluate((storageData) => {
        Object.entries(storageData).forEach(([key, value]) => {
          localStorage.setItem(key, value);
        });
      }, storage);

      // 重新載入
      await page.reload({ waitUntil: 'networkidle0', timeout: 30000 });
    } else {
      await page.waitForNetworkIdle({ timeout: 30000 }).catch(() => {});
    }

    // 等待渲染
    console.log(`[Screenshot] Waiting ${wait}ms for render...`);
    await new Promise(r => setTimeout(r, wait));

    // 截圖
    console.log('[Screenshot] Taking screenshot...');
    await page.screenshot({ path: output, fullPage });

    console.log('[Screenshot] Saved to:', output);
    return { success: true, path: output };

  } finally {
    await browser.close();
  }
}

// CLI 執行
if (require.main === module) {
  const args = process.argv.slice(2);
  const url = args.find(a => !a.startsWith('-'));

  if (!url) {
    console.log('Usage: node screenshot.js <url> [options]');
    console.log('Options:');
    console.log('  --output, -o    Output path (default: /tmp/screenshot.png)');
    console.log('  --wait, -w      Wait time in ms (default: 3000)');
    console.log('  --width         Viewport width (default: 1920)');
    console.log('  --height        Viewport height (default: 1080)');
    console.log('  --storage       JSON localStorage data');
    process.exit(1);
  }

  const getArg = (name, short) => {
    const idx = args.findIndex(a => a === `--${name}` || a === `-${short}`);
    return idx !== -1 ? args[idx + 1] : undefined;
  };

  const options = {
    url,
    output: getArg('output', 'o') || '/tmp/screenshot.png',
    wait: parseInt(getArg('wait', 'w') || '3000'),
    width: parseInt(getArg('width') || '1920'),
    height: parseInt(getArg('height') || '1080'),
    storage: getArg('storage') ? JSON.parse(getArg('storage')) : {}
  };

  screenshot(options)
    .then(() => process.exit(0))
    .catch(err => {
      console.error('[Screenshot] Error:', err.message);
      process.exit(1);
    });
}

module.exports = { screenshot };
