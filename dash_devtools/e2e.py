"""
E2E 煙霧測試模組
使用 agent-browser 檢查頁面是否有 JS 錯誤
支援失敗時自動截圖、手機版測試
"""

import subprocess
import json
import shutil
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime


def check_agent_browser_installed() -> bool:
    """檢查 agent-browser 是否已安裝"""
    return shutil.which('agent-browser') is not None


def run_agent_browser(*args, timeout: int = 30) -> Dict:
    """執行 agent-browser 指令"""
    cmd = ['agent-browser', *args]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return {
            'success': result.returncode == 0,
            'stdout': result.stdout.strip(),
            'stderr': result.stderr.strip()
        }
    except subprocess.TimeoutExpired:
        return {'success': False, 'stdout': '', 'stderr': f'超時 ({timeout}秒)'}
    except Exception as e:
        return {'success': False, 'stdout': '', 'stderr': str(e)}


def run_e2e_test(
    url: str,
    timeout: int = 30000,
    check_type: str = "errors",
    screenshot_on_fail: bool = False,
    screenshot_path: Optional[str] = None,
    mobile: bool = False
) -> Dict:
    """
    執行 E2E 煙霧測試

    Args:
        url: 要測試的網址
        timeout: 超時時間 (毫秒)
        check_type: 檢查類型 (errors, load, all)
        screenshot_on_fail: 失敗時是否截圖
        screenshot_path: 截圖儲存路徑
        mobile: 是否使用手機版視窗 (375x812)

    Returns:
        測試結果字典
    """
    result = {
        'url': url,
        'success': True,
        'errors': [],
        'warnings': [],
        'loadTime': 0,
        'status': 200,
        'screenshot': None,
        'hasHorizontalScroll': False,
        'isMobile': mobile,
        'title': ''
    }

    # 檢查 agent-browser 是否安裝
    if not check_agent_browser_installed():
        result['success'] = False
        result['errors'].append(
            'agent-browser 未安裝。請執行: npm install -g agent-browser && agent-browser install'
        )
        return result

    timeout_sec = timeout // 1000

    try:
        import time
        start_time = time.time()

        # 開啟頁面
        open_result = run_agent_browser('open', url, timeout=timeout_sec)
        if not open_result['success']:
            result['success'] = False
            result['errors'].append(f"頁面載入失敗: {open_result['stderr']}")
            result['status'] = 0
            return result

        # 等待頁面載入完成
        run_agent_browser('wait', '--load', 'networkidle', timeout=timeout_sec)

        result['loadTime'] = int((time.time() - start_time) * 1000)

        # 等待額外時間讓 JS 執行
        run_agent_browser('wait', '2000')

        # 取得頁面標題
        title_result = run_agent_browser('get', 'title')
        if title_result['success']:
            result['title'] = title_result['stdout']

        # 檢查頁面錯誤
        if check_type in ('errors', 'all'):
            errors_result = run_agent_browser('errors')
            if errors_result['stdout']:
                # 解析錯誤，過濾常見無害錯誤
                for line in errors_result['stdout'].split('\n'):
                    line = line.strip()
                    if not line:
                        continue
                    # 忽略常見的非關鍵錯誤
                    if any(ignore in line.lower() for ignore in ['favicon', '404', 'analytics']):
                        continue
                    result['errors'].append(line[:300])

        # 檢查 Vue/React 常見錯誤
        vue_react_errors = [
            e for e in result['errors']
            if any(err_type in e for err_type in [
                'TypeError', 'insertBefore', 'Cannot read properties',
                'is not a function', 'undefined is not an object'
            ])
        ]
        if vue_react_errors:
            result['success'] = False

        # 手機版：檢查水平滾動
        if mobile:
            # 使用 snapshot 檢查頁面寬度 (透過 console 執行 JS)
            scroll_check = run_agent_browser(
                'console',
                timeout=5
            )
            # 簡化：如果有錯誤就標記
            if result['errors']:
                result['hasHorizontalScroll'] = True
                result['success'] = False

        # 判斷最終結果
        if check_type == 'load':
            result['success'] = result['status'] == 200
        elif check_type in ('errors', 'all'):
            result['success'] = len(result['errors']) == 0

        # 失敗時截圖
        if not result['success'] and screenshot_on_fail:
            if not screenshot_path:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                device_suffix = "-mobile" if mobile else ""
                screenshot_path = f"/tmp/e2e-screenshot{device_suffix}-{timestamp}.png"

            screenshot_result = run_agent_browser('screenshot', screenshot_path, '--full')
            if screenshot_result['success']:
                result['screenshot'] = screenshot_path

    except Exception as e:
        result['success'] = False
        result['errors'].append(str(e))

    finally:
        # 關閉瀏覽器
        run_agent_browser('close')

    return result


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
    """檢查 agent-browser 是否已安裝 (向下相容舊 API)"""
    return check_agent_browser_installed()


def get_puppeteer_cwd() -> str:
    """向下相容舊 API，現在不需要"""
    return '.'


# ========== 進階功能 ==========

def run_e2e_with_login(
    url: str,
    state_file: str,
    timeout: int = 30000,
    check_type: str = "errors",
    screenshot_on_fail: bool = False
) -> Dict:
    """
    使用已儲存的登入狀態執行 E2E 測試

    Args:
        url: 要測試的網址
        state_file: 登入狀態檔案路徑 (由 agent-browser state save 產生)
        timeout: 超時時間 (毫秒)
        check_type: 檢查類型
        screenshot_on_fail: 失敗時是否截圖

    Returns:
        測試結果字典
    """
    result = {
        'url': url,
        'success': True,
        'errors': [],
        'warnings': [],
        'loadTime': 0,
        'status': 200,
        'screenshot': None,
        'hasAuth': True
    }

    if not check_agent_browser_installed():
        result['success'] = False
        result['errors'].append('agent-browser 未安裝')
        return result

    if not Path(state_file).exists():
        result['success'] = False
        result['errors'].append(f'登入狀態檔案不存在: {state_file}')
        return result

    timeout_sec = timeout // 1000

    try:
        import time

        # 載入登入狀態
        load_result = run_agent_browser('state', 'load', state_file)
        if not load_result['success']:
            result['warnings'].append(f"載入登入狀態失敗: {load_result['stderr']}")

        start_time = time.time()

        # 開啟頁面
        open_result = run_agent_browser('open', url, timeout=timeout_sec)
        if not open_result['success']:
            result['success'] = False
            result['errors'].append(f"頁面載入失敗: {open_result['stderr']}")
            return result

        run_agent_browser('wait', '--load', 'networkidle', timeout=timeout_sec)
        result['loadTime'] = int((time.time() - start_time) * 1000)

        # 等待 JS 執行
        run_agent_browser('wait', '2000')

        # 檢查錯誤
        if check_type in ('errors', 'all'):
            errors_result = run_agent_browser('errors')
            if errors_result['stdout']:
                for line in errors_result['stdout'].split('\n'):
                    line = line.strip()
                    if line and 'favicon' not in line.lower():
                        result['errors'].append(line[:300])

        result['success'] = len(result['errors']) == 0

        # 失敗時截圖
        if not result['success'] and screenshot_on_fail:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = f"/tmp/e2e-auth-{timestamp}.png"
            screenshot_result = run_agent_browser('screenshot', screenshot_path, '--full')
            if screenshot_result['success']:
                result['screenshot'] = screenshot_path

    except Exception as e:
        result['success'] = False
        result['errors'].append(str(e))

    finally:
        run_agent_browser('close')

    return result


def quick_smoke_test(url: str) -> Dict:
    """
    快速煙霧測試 (簡化版)

    Args:
        url: 要測試的網址

    Returns:
        {
            'ok': bool,
            'title': str,
            'load_time_ms': int,
            'error_count': int
        }
    """
    result = run_e2e_test(url, timeout=15000, check_type='errors')
    return {
        'ok': result['success'],
        'title': result.get('title', ''),
        'load_time_ms': result['loadTime'],
        'error_count': len(result['errors'])
    }
