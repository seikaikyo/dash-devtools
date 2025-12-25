"""
E2E 煙霧測試模組
使用 Puppeteer 檢查頁面是否有 JS 錯誤
支援失敗時自動截圖
"""

import subprocess
import json
import tempfile
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

# Node.js Puppeteer 腳本模板 (支援截圖)
PUPPETEER_SCRIPT = '''
const puppeteer = require("puppeteer");
const path = require("path");

(async () => {
  const url = process.argv[2];
  const timeout = parseInt(process.argv[3]) || 30000;
  const checkType = process.argv[4] || "errors";
  const screenshotOnFail = process.argv[5] === "true";
  const screenshotPath = process.argv[6] || "/tmp/e2e-screenshot.png";

  const result = {
    url: url,
    success: true,
    errors: [],
    warnings: [],
    loadTime: 0,
    status: 200,
    screenshot: null
  };

  let browser;
  let page;
  try {
    browser = await puppeteer.launch({ headless: "new" });
    page = await browser.newPage();
    await page.setViewport({ width: 1920, height: 1080 });

    // 收集 console 錯誤
    page.on("console", msg => {
      if (msg.type() === "error") {
        const text = msg.text();
        // 忽略常見的非關鍵錯誤
        if (!text.includes("favicon") && !text.includes("404")) {
          result.errors.push(text.substring(0, 200));
        }
      } else if (msg.type() === "warning") {
        result.warnings.push(msg.text().substring(0, 200));
      }
    });

    page.on("pageerror", err => {
      result.errors.push(err.toString().substring(0, 300));
    });

    // 載入頁面
    const startTime = Date.now();
    const response = await page.goto(url, {
      waitUntil: "networkidle0",
      timeout: timeout
    });
    result.loadTime = Date.now() - startTime;
    result.status = response ? response.status() : 0;

    // 等待額外時間讓 JS 執行
    await new Promise(r => setTimeout(r, 2000));

    // 檢查是否有 Vue/React 錯誤
    const hasVueError = result.errors.some(e =>
      e.includes("TypeError") ||
      e.includes("insertBefore") ||
      e.includes("Cannot read properties")
    );

    if (hasVueError) {
      result.success = false;
    }

    // 只檢查載入
    if (checkType === "load") {
      result.success = result.status === 200 || result.status === 304;
    }
    // 檢查錯誤 (預設)
    else {
      result.success = result.errors.length === 0;
    }

    // 失敗時截圖
    if (!result.success && screenshotOnFail && page) {
      try {
        await page.screenshot({ path: screenshotPath, fullPage: true });
        result.screenshot = screenshotPath;
      } catch (screenshotErr) {
        result.warnings.push("Screenshot failed: " + screenshotErr.message);
      }
    }

  } catch (err) {
    result.success = false;
    result.errors.push(err.message);

    // 錯誤時也嘗試截圖
    if (screenshotOnFail && page) {
      try {
        await page.screenshot({ path: screenshotPath, fullPage: true });
        result.screenshot = screenshotPath;
      } catch (screenshotErr) {
        // 忽略截圖錯誤
      }
    }
  } finally {
    if (browser) await browser.close();
  }

  console.log(JSON.stringify(result));
})();
'''


def run_e2e_test(
    url: str,
    timeout: int = 30000,
    check_type: str = "errors",
    screenshot_on_fail: bool = False,
    screenshot_path: Optional[str] = None
) -> Dict:
    """
    執行 E2E 煙霧測試

    Args:
        url: 要測試的網址
        timeout: 超時時間 (毫秒)
        check_type: 檢查類型 (errors, load)
        screenshot_on_fail: 失敗時是否截圖
        screenshot_path: 截圖儲存路徑 (預設 /tmp/e2e-screenshot-{timestamp}.png)

    Returns:
        測試結果字典，包含 screenshot 欄位 (如有截圖)
    """
    # 建立臨時腳本檔案
    with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
        f.write(PUPPETEER_SCRIPT)
        script_path = f.name

    # 決定截圖路徑
    if screenshot_on_fail and not screenshot_path:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        screenshot_path = f"/tmp/e2e-screenshot-{timestamp}.png"

    try:
        # 找到有 puppeteer 的目錄
        puppeteer_cwd = get_puppeteer_cwd()

        # 設定 NODE_PATH 讓 node 可以找到 puppeteer
        env = {
            **subprocess.os.environ,
            'NODE_PATH': f"{puppeteer_cwd}/node_modules"
        }

        # 執行 Node.js 腳本
        cmd = [
            'node', script_path, url, str(timeout), check_type,
            str(screenshot_on_fail).lower(),
            screenshot_path or ""
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout / 1000 + 30,  # 額外 30 秒緩衝
            cwd=puppeteer_cwd,
            env=env
        )

        if result.returncode != 0:
            return {
                'url': url,
                'success': False,
                'errors': [f"Script error: {result.stderr}"],
                'warnings': [],
                'loadTime': 0,
                'status': 0,
                'screenshot': None
            }

        # 解析 JSON 輸出
        try:
            return json.loads(result.stdout.strip())
        except json.JSONDecodeError:
            return {
                'url': url,
                'success': False,
                'errors': [f"Invalid JSON output: {result.stdout[:200]}"],
                'warnings': [],
                'loadTime': 0,
                'status': 0,
                'screenshot': None
            }

    except subprocess.TimeoutExpired:
        return {
            'url': url,
            'success': False,
            'errors': ['Timeout exceeded'],
            'warnings': [],
            'loadTime': timeout,
            'status': 0,
            'screenshot': None
        }
    except FileNotFoundError:
        return {
            'url': url,
            'success': False,
            'errors': ['Node.js not found. Please install Node.js and puppeteer.'],
            'warnings': [],
            'loadTime': 0,
            'status': 0,
            'screenshot': None
        }
    finally:
        # 清理臨時檔案
        Path(script_path).unlink(missing_ok=True)


def run_e2e_tests(
    urls: List[str],
    timeout: int = 30000,
    check_type: str = "errors",
    screenshot_on_fail: bool = False
) -> List[Dict]:
    """
    批次執行 E2E 測試

    Args:
        urls: 要測試的網址列表
        timeout: 超時時間 (毫秒)
        check_type: 檢查類型
        screenshot_on_fail: 失敗時是否截圖

    Returns:
        測試結果列表
    """
    results = []
    for url in urls:
        result = run_e2e_test(url, timeout, check_type, screenshot_on_fail)
        results.append(result)
    return results


def check_puppeteer_installed() -> bool:
    """檢查 Puppeteer 是否已安裝 (全域或本地)"""
    # 嘗試常見的 puppeteer 安裝位置
    check_dirs = [
        '.',
        '/Users/dash/Documents/github/smai-process-vision',
        '/Users/dash/Documents/github/smai-portal-v2',
    ]

    for check_dir in check_dirs:
        try:
            result = subprocess.run(
                ['node', '-e', 'require("puppeteer")'],
                capture_output=True,
                timeout=10,
                cwd=check_dir
            )
            if result.returncode == 0:
                return True
        except:
            continue

    return False


def get_puppeteer_cwd() -> str:
    """取得有安裝 Puppeteer 的目錄"""
    check_dirs = [
        '/Users/dash/Documents/github/smai-process-vision',
        '/Users/dash/Documents/github/smai-portal-v2',
        '.',
    ]

    for check_dir in check_dirs:
        try:
            result = subprocess.run(
                ['node', '-e', 'require("puppeteer")'],
                capture_output=True,
                timeout=10,
                cwd=check_dir
            )
            if result.returncode == 0:
                return check_dir
        except:
            continue

    return '.'
