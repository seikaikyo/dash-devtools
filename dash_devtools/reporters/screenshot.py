"""
截圖整合模組

使用 agent-browser 擷取網頁截圖。
"""

import json
import shutil
import subprocess
from pathlib import Path
from datetime import datetime
from typing import List, Optional

from rich.console import Console

from .report_data import ScreenshotResult

console = Console()


def take_screenshots(
    project_path: Path,
    report_dir: Path,
    urls: Optional[List[str]] = None
) -> List[ScreenshotResult]:
    """使用 agent-browser 截圖

    Args:
        project_path: 專案根目錄路徑
        report_dir: 報告輸出目錄
        urls: 要截圖的 URL 清單，若未指定會嘗試偵測本地開發伺服器

    Returns:
        截圖結果清單
    """
    results = []

    # 檢查 agent-browser 是否安裝
    if not shutil.which('agent-browser'):
        console.print("[yellow]agent-browser 未安裝，跳過截圖[/yellow]")
        console.print("[dim]安裝方式: npm install -g agent-browser && agent-browser install[/dim]")
        return results

    # 如果沒指定 URL，嘗試偵測本地開發伺服器
    if not urls:
        urls = _detect_dev_urls(project_path)

    if not urls:
        return results

    # 確保報告目錄存在
    screenshots_dir = report_dir / 'screenshots'
    screenshots_dir.mkdir(parents=True, exist_ok=True)

    # 使用 agent-browser 截圖
    for url in urls:
        result = _capture_single(url, screenshots_dir)
        results.append(result)

    return results


def _detect_dev_urls(project_path: Path) -> Optional[List[str]]:
    """偵測本地開發伺服器 URL

    Args:
        project_path: 專案根目錄路徑

    Returns:
        偵測到的 URL 清單，或 None
    """
    package_json = project_path / 'package.json'
    if package_json.exists():
        try:
            pkg = json.loads(package_json.read_text())
            scripts = pkg.get('scripts', {})
            if 'dev' in scripts or 'start' in scripts:
                return ['http://localhost:5173', 'http://localhost:3000', 'http://localhost:4200']
        except Exception:
            pass
    return None


def _capture_single(url: str, screenshots_dir: Path) -> ScreenshotResult:
    """擷取單一頁面截圖

    Args:
        url: 目標 URL
        screenshots_dir: 截圖儲存目錄

    Returns:
        截圖結果
    """
    screenshot_path = screenshots_dir / f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"

    try:
        # 開啟頁面
        open_result = subprocess.run(
            ['agent-browser', 'open', url],
            capture_output=True,
            text=True,
            timeout=30
        )

        if open_result.returncode != 0:
            subprocess.run(['agent-browser', 'close'], capture_output=True)
            return ScreenshotResult(
                url=url,
                path="",
                success=False,
                error=f"無法開啟頁面: {open_result.stderr}"
            )

        # 等待頁面載入
        subprocess.run(
            ['agent-browser', 'wait', '--load', 'networkidle'],
            capture_output=True,
            timeout=15
        )

        # 額外等待 JS 渲染
        subprocess.run(
            ['agent-browser', 'wait', '2000'],
            capture_output=True,
            timeout=5
        )

        # 截圖
        screenshot_result = subprocess.run(
            ['agent-browser', 'screenshot', str(screenshot_path), '--full'],
            capture_output=True,
            text=True,
            timeout=30
        )

        # 關閉瀏覽器
        subprocess.run(['agent-browser', 'close'], capture_output=True)

        if screenshot_result.returncode == 0 and screenshot_path.exists():
            return ScreenshotResult(
                url=url,
                path=str(screenshot_path),
                success=True
            )
        else:
            return ScreenshotResult(
                url=url,
                path="",
                success=False,
                error=screenshot_result.stderr or "截圖失敗"
            )

    except subprocess.TimeoutExpired:
        subprocess.run(['agent-browser', 'close'], capture_output=True)
        return ScreenshotResult(
            url=url,
            path="",
            success=False,
            error="操作超時"
        )
    except Exception as e:
        subprocess.run(['agent-browser', 'close'], capture_output=True)
        return ScreenshotResult(
            url=url,
            path="",
            success=False,
            error=str(e)
        )
