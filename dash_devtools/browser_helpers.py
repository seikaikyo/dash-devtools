"""
瀏覽器自動化便捷函數

快速截圖、頁面檢查、表單填寫、登入等常用操作
"""

import time
from typing import Dict, List, Optional

from .browser import AgentBrowser, BrowserResult


def quick_screenshot(url: str, output_path: str, wait_ms: int = 3000, mobile: bool = False) -> bool:
    """
    快速截圖

    Args:
        url: 網址
        output_path: 輸出路徑
        wait_ms: 等待時間 (毫秒)
        mobile: 是否使用手機版視窗

    Returns:
        是否成功
    """
    browser = AgentBrowser()
    try:
        result = browser.open(url)
        if not result.success:
            return False

        # 等待頁面載入
        browser.wait(str(wait_ms))

        # 截圖
        result = browser.screenshot(output_path, full_page=True)
        return result.success

    finally:
        browser.close()


def check_page_errors(url: str, timeout: int = 30) -> Dict:
    """
    檢查頁面 JS 錯誤

    Args:
        url: 網址
        timeout: 超時時間 (秒)

    Returns:
        {
            'success': bool,
            'url': str,
            'title': str,
            'errors': List[str],
            'load_time': int
        }
    """
    browser = AgentBrowser()
    result = {
        'success': True,
        'url': url,
        'title': '',
        'errors': [],
        'load_time': 0
    }

    try:
        start = time.time()
        open_result = browser.open(url, timeout=timeout)
        result['load_time'] = int((time.time() - start) * 1000)

        if not open_result.success:
            result['success'] = False
            result['errors'].append(open_result.error or "頁面載入失敗")
            return result

        # 等待 JS 執行
        browser.wait('2000')

        # 取得標題
        result['title'] = browser.get_title()

        # 取得錯誤
        errors_result = browser.errors()
        if errors_result.output:
            # 解析錯誤訊息
            error_lines = [
                line.strip()
                for line in errors_result.output.split('\n')
                if line.strip() and 'favicon' not in line.lower()
            ]
            result['errors'] = error_lines

        result['success'] = len(result['errors']) == 0

    except Exception as e:
        result['success'] = False
        result['errors'].append(str(e))

    finally:
        browser.close()

    return result


def fill_form(url: str, fields: Dict[str, str], submit_ref: Optional[str] = None) -> BrowserResult:
    """
    填寫表單

    Args:
        url: 網址
        fields: {ref: value} 對應
        submit_ref: 送出按鈕 ref (可選)

    Returns:
        操作結果
    """
    browser = AgentBrowser()
    try:
        result = browser.open(url)
        if not result.success:
            return result

        browser.wait('2000')

        # 填寫欄位
        for ref, value in fields.items():
            result = browser.fill(ref, value)
            if not result.success:
                return result

        # 送出表單
        if submit_ref:
            result = browser.click(submit_ref)
            browser.wait_load('networkidle')

        return BrowserResult(success=True, output="表單填寫完成")

    finally:
        browser.close()


def login_and_save_state(
    login_url: str,
    username_ref: str,
    password_ref: str,
    submit_ref: str,
    username: str,
    password: str,
    state_file: str,
    success_url_pattern: Optional[str] = None
) -> BrowserResult:
    """
    登入並儲存狀態

    Args:
        login_url: 登入頁面網址
        username_ref: 帳號輸入框 ref
        password_ref: 密碼輸入框 ref
        submit_ref: 登入按鈕 ref
        username: 帳號
        password: 密碼
        state_file: 狀態儲存檔案
        success_url_pattern: 登入成功後的網址 pattern

    Returns:
        操作結果
    """
    browser = AgentBrowser()
    try:
        result = browser.open(login_url)
        if not result.success:
            return result

        browser.wait('2000')

        # 填寫登入資訊
        browser.fill(username_ref, username)
        browser.fill(password_ref, password)
        browser.click(submit_ref)

        # 等待登入完成
        if success_url_pattern:
            browser.wait_url(success_url_pattern, timeout=30)
        else:
            browser.wait_load('networkidle')

        # 儲存狀態
        result = browser.state_save(state_file)
        if result.success:
            return BrowserResult(success=True, output=f"登入成功，狀態已儲存至 {state_file}")
        else:
            return result

    finally:
        browser.close()
