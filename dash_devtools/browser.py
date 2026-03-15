"""
瀏覽器自動化模組
使用 agent-browser 進行網頁操作、截圖、表單填寫等

安裝方式：
    npm install -g agent-browser
    agent-browser install
"""

import subprocess
import json
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass


@dataclass
class BrowserResult:
    """瀏覽器操作結果"""
    success: bool
    output: str = ""
    error: str = ""
    data: Optional[Any] = None


class AgentBrowser:
    """agent-browser CLI wrapper"""

    def __init__(self, session: Optional[str] = None, headed: bool = False):
        """
        初始化瀏覽器

        Args:
            session: 會話名稱 (可同時操作多個瀏覽器)
            headed: 是否顯示瀏覽器視窗 (debug 用)
        """
        self.session = session
        self.headed = headed
        self._check_installed()

    def _check_installed(self) -> bool:
        """檢查 agent-browser 是否已安裝"""
        if not shutil.which('agent-browser'):
            raise RuntimeError(
                "agent-browser 未安裝。請執行:\n"
                "  npm install -g agent-browser\n"
                "  agent-browser install"
            )
        return True

    def _run(self, *args, timeout: int = 30) -> BrowserResult:
        """執行 agent-browser 指令"""
        cmd = ['agent-browser']

        if self.session:
            cmd.extend(['--session', self.session])

        cmd.extend(args)

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )

            if result.returncode == 0:
                return BrowserResult(
                    success=True,
                    output=result.stdout.strip()
                )
            else:
                return BrowserResult(
                    success=False,
                    output=result.stdout.strip(),
                    error=result.stderr.strip()
                )

        except subprocess.TimeoutExpired:
            return BrowserResult(
                success=False,
                error=f"操作超時 ({timeout}秒)"
            )
        except Exception as e:
            return BrowserResult(
                success=False,
                error=str(e)
            )

    def _run_json(self, *args, timeout: int = 30) -> BrowserResult:
        """執行指令並解析 JSON 輸出"""
        result = self._run(*args, '--json', timeout=timeout)
        if result.success and result.output:
            try:
                result.data = json.loads(result.output)
            except json.JSONDecodeError:
                pass
        return result

    # ========== 導航操作 ==========

    def open(self, url: str, timeout: int = 30) -> BrowserResult:
        """開啟網頁"""
        args = ['open', url]
        if self.headed:
            args.append('--headed')
        return self._run(*args, timeout=timeout)

    def back(self) -> BrowserResult:
        """回到上一頁"""
        return self._run('back')

    def forward(self) -> BrowserResult:
        """前進下一頁"""
        return self._run('forward')

    def reload(self) -> BrowserResult:
        """重新載入頁面"""
        return self._run('reload')

    def close(self) -> BrowserResult:
        """關閉瀏覽器"""
        return self._run('close')

    # ========== 頁面分析 ==========

    def snapshot(self, interactive_only: bool = True, compact: bool = False, depth: int = 0) -> BrowserResult:
        """
        取得頁面快照 (元素列表)

        Args:
            interactive_only: 只顯示可互動元素
            compact: 精簡輸出
            depth: 限制深度 (0 = 不限)
        """
        args = ['snapshot']
        if interactive_only:
            args.append('-i')
        if compact:
            args.append('-c')
        if depth > 0:
            args.extend(['-d', str(depth)])

        return self._run_json(*args)

    def get_title(self) -> str:
        """取得頁面標題"""
        result = self._run('get', 'title')
        return result.output if result.success else ""

    def get_url(self) -> str:
        """取得目前網址"""
        result = self._run('get', 'url')
        return result.output if result.success else ""

    def get_text(self, ref: str) -> str:
        """取得元素文字"""
        result = self._run('get', 'text', ref)
        return result.output if result.success else ""

    def get_value(self, ref: str) -> str:
        """取得輸入框值"""
        result = self._run('get', 'value', ref)
        return result.output if result.success else ""

    # ========== 互動操作 ==========

    def click(self, ref: str) -> BrowserResult:
        """點擊元素"""
        return self._run('click', ref)

    def dblclick(self, ref: str) -> BrowserResult:
        """雙擊元素"""
        return self._run('dblclick', ref)

    def fill(self, ref: str, text: str) -> BrowserResult:
        """填寫輸入框 (會先清空)"""
        return self._run('fill', ref, text)

    def type_text(self, ref: str, text: str) -> BrowserResult:
        """輸入文字 (不清空)"""
        return self._run('type', ref, text)

    def press(self, key: str) -> BrowserResult:
        """按鍵 (如 Enter, Tab, Control+a)"""
        return self._run('press', key)

    def hover(self, ref: str) -> BrowserResult:
        """滑鼠懸停"""
        return self._run('hover', ref)

    def check(self, ref: str) -> BrowserResult:
        """勾選 checkbox"""
        return self._run('check', ref)

    def uncheck(self, ref: str) -> BrowserResult:
        """取消勾選 checkbox"""
        return self._run('uncheck', ref)

    def select(self, ref: str, value: str) -> BrowserResult:
        """選擇下拉選單"""
        return self._run('select', ref, value)

    def scroll(self, direction: str = 'down', amount: int = 500) -> BrowserResult:
        """捲動頁面"""
        return self._run('scroll', direction, str(amount))

    def scroll_to(self, ref: str) -> BrowserResult:
        """捲動到元素"""
        return self._run('scrollintoview', ref)

    # ========== 截圖 ==========

    def screenshot(self, path: Optional[str] = None, full_page: bool = False) -> BrowserResult:
        """
        截圖

        Args:
            path: 儲存路徑 (None 則輸出到 stdout)
            full_page: 是否截取完整頁面
        """
        args = ['screenshot']
        if path:
            args.append(path)
        if full_page:
            args.append('--full')

        return self._run(*args, timeout=60)

    # ========== 等待 ==========

    def wait(self, ref_or_ms: str, timeout: int = 30) -> BrowserResult:
        """等待元素或時間"""
        return self._run('wait', ref_or_ms, timeout=timeout)

    def wait_text(self, text: str, timeout: int = 30) -> BrowserResult:
        """等待文字出現"""
        return self._run('wait', '--text', text, timeout=timeout)

    def wait_load(self, state: str = 'networkidle', timeout: int = 30) -> BrowserResult:
        """等待載入完成 (networkidle, domcontentloaded, load)"""
        return self._run('wait', '--load', state, timeout=timeout)

    def wait_url(self, pattern: str, timeout: int = 30) -> BrowserResult:
        """等待網址符合 pattern"""
        return self._run('wait', '--url', pattern, timeout=timeout)

    # ========== 狀態管理 ==========

    def state_save(self, path: str) -> BrowserResult:
        """儲存登入狀態 (cookies, localStorage)"""
        return self._run('state', 'save', path)

    def state_load(self, path: str) -> BrowserResult:
        """載入登入狀態"""
        return self._run('state', 'load', path)

    # ========== 語意定位 ==========

    def find_and_click(self, locator_type: str, value: str, **kwargs) -> BrowserResult:
        """
        使用語意定位點擊

        Args:
            locator_type: role, text, label
            value: 定位值
            **kwargs: 額外參數 (如 name)
        """
        args = ['find', locator_type, value, 'click']
        for k, v in kwargs.items():
            args.extend([f'--{k}', str(v)])
        return self._run(*args)

    def find_and_fill(self, locator_type: str, value: str, text: str, **kwargs) -> BrowserResult:
        """使用語意定位填寫"""
        args = ['find', locator_type, value, 'fill', text]
        for k, v in kwargs.items():
            args.extend([f'--{k}', str(v)])
        return self._run(*args)

    # ========== 進階互動 ==========

    def focus(self, ref: str) -> BrowserResult:
        """聚焦元素"""
        return self._run('focus', ref)

    def drag(self, from_ref: str, to_ref: str) -> BrowserResult:
        """拖放元素"""
        return self._run('drag', from_ref, to_ref)

    def upload(self, ref: str, file_path: str) -> BrowserResult:
        """上傳檔案"""
        return self._run('upload', ref, file_path)

    # ========== PDF ==========

    def pdf(self, path: str) -> BrowserResult:
        """輸出 PDF"""
        return self._run('pdf', path, timeout=60)

    # ========== Cookie 管理 ==========

    def cookies_get(self) -> BrowserResult:
        """取得所有 cookies"""
        return self._run_json('cookies')

    def cookies_set(self, name: str, value: str, **kwargs) -> BrowserResult:
        """設定 cookie"""
        args = ['cookies', 'set', name, value]
        for k, v in kwargs.items():
            args.extend([f'--{k}', str(v)])
        return self._run(*args)

    def cookies_clear(self) -> BrowserResult:
        """清除所有 cookies"""
        return self._run('cookies', 'clear')

    # ========== JavaScript 執行 ==========

    def evaluate(self, js_code: str) -> BrowserResult:
        """執行 JavaScript"""
        return self._run('evaluate', js_code)

    # ========== 網路請求 ==========

    def network(self) -> BrowserResult:
        """取得網路請求列表"""
        return self._run_json('network')

    # ========== 會話管理 ==========

    def session_list(self) -> BrowserResult:
        """列出所有會話"""
        return self._run_json('session', 'list')

    def session_kill(self, session_name: str) -> BrowserResult:
        """結束指定會話"""
        return self._run('session', 'kill', session_name)

    # ========== Debug ==========

    def console(self) -> BrowserResult:
        """取得 console 訊息"""
        return self._run('console')

    def errors(self) -> BrowserResult:
        """取得頁面錯誤"""
        return self._run('errors')


# 便捷函數 re-export（向下相容）
from .browser_helpers import quick_screenshot, check_page_errors, fill_form, login_and_save_state  # noqa: E402, F401
