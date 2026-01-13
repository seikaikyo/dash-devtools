"""
視覺 AI 工具
使用 agent-browser 截圖 + Gemini AI 進行 UI/UX 分析

功能：
- 網頁截圖並分析 UI/UX 問題
- 視覺回歸測試
- 無障礙設計檢查
- 效能視覺指標分析
"""

import subprocess
import shutil
import base64
import tempfile
from pathlib import Path
from typing import Optional, Dict, List
from dataclasses import dataclass


@dataclass
class VisionResult:
    """視覺分析結果"""
    success: bool
    url: str = ""
    screenshot_path: str = ""
    analysis: str = ""
    issues: List[str] = None
    recommendations: List[str] = None
    error: str = ""

    def __post_init__(self):
        if self.issues is None:
            self.issues = []
        if self.recommendations is None:
            self.recommendations = []


def check_dependencies() -> Dict[str, bool]:
    """檢查依賴是否已安裝"""
    return {
        'agent-browser': shutil.which('agent-browser') is not None,
        'gemini': _check_gemini_available()
    }


def _check_gemini_available() -> bool:
    """檢查 Gemini API 是否可用"""
    try:
        from ..ai_engine import AIEngine
        AIEngine()
        return True
    except Exception:
        return False


def take_screenshot(url: str, output_path: Optional[str] = None, wait_ms: int = 3000) -> Optional[str]:
    """
    使用 agent-browser 截圖

    Args:
        url: 要截圖的網址
        output_path: 輸出路徑 (預設建立臨時檔案)
        wait_ms: 等待時間 (毫秒)

    Returns:
        截圖路徑，失敗回傳 None
    """
    if not shutil.which('agent-browser'):
        return None

    if not output_path:
        output_path = tempfile.mktemp(suffix='.png')

    try:
        # 開啟頁面
        result = subprocess.run(
            ['agent-browser', 'open', url],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode != 0:
            subprocess.run(['agent-browser', 'close'], capture_output=True)
            return None

        # 等待載入
        subprocess.run(
            ['agent-browser', 'wait', '--load', 'networkidle'],
            capture_output=True,
            timeout=15
        )

        # 額外等待 JS 渲染
        subprocess.run(
            ['agent-browser', 'wait', str(wait_ms)],
            capture_output=True,
            timeout=10
        )

        # 截圖
        result = subprocess.run(
            ['agent-browser', 'screenshot', output_path, '--full'],
            capture_output=True,
            timeout=30
        )

        subprocess.run(['agent-browser', 'close'], capture_output=True)

        if result.returncode == 0 and Path(output_path).exists():
            return output_path

    except Exception:
        subprocess.run(['agent-browser', 'close'], capture_output=True)

    return None


def analyze_image(
    image_path: str,
    prompt: Optional[str] = None,
    analysis_type: str = "general"
) -> VisionResult:
    """
    使用 AI 分析圖片

    Args:
        image_path: 圖片路徑
        prompt: 自訂分析提示 (可選)
        analysis_type: 分析類型 (general, ui_ux, accessibility, performance)

    Returns:
        VisionResult 物件
    """
    result = VisionResult(success=False)

    # 檢查檔案
    if not Path(image_path).exists():
        result.error = f"圖片不存在: {image_path}"
        return result

    result.screenshot_path = image_path

    # 預設提示
    prompts = {
        "general": """分析這張網頁截圖，提供：
1. 整體 UI/UX 評估
2. 發現的問題列表
3. 改善建議

請用正體中文回答，以清單格式呈現。""",

        "ui_ux": """以 UI/UX 專家的角度分析這張網頁截圖：

評估項目：
1. 視覺層次 - 資訊是否清晰分層
2. 色彩搭配 - 是否協調、對比是否足夠
3. 排版布局 - 是否整齊、間距是否合理
4. 互動元素 - 按鈕、連結是否明顯可點擊
5. 一致性 - 元件風格是否統一

請列出具體問題和改善建議。用正體中文回答。""",

        "accessibility": """以無障礙設計 (WCAG 2.1) 的角度分析這張網頁截圖：

檢查項目：
1. 色彩對比度是否足夠 (至少 4.5:1)
2. 文字大小是否易讀 (至少 16px)
3. 互動元素是否有足夠點擊範圍 (至少 44x44px)
4. 是否有僅靠顏色傳達資訊的問題
5. 表單元素是否有明確標籤

請列出具體問題和改善建議。用正體中文回答。""",

        "performance": """分析這張網頁截圖的視覺效能指標：

評估項目：
1. 內容是否完整載入
2. 是否有明顯的版面跳動風險
3. 圖片是否適當優化
4. 是否有過多視覺元素影響效能
5. 首屏內容是否有效利用

請列出具體問題和改善建議。用正體中文回答。"""
    }

    analysis_prompt = prompt or prompts.get(analysis_type, prompts["general"])

    try:
        from ..ai_engine import AIEngine

        ai = AIEngine()

        # 讀取圖片並轉為 base64
        with open(image_path, 'rb') as f:
            image_data = base64.b64encode(f.read()).decode()

        # 使用 Gemini 的多模態功能
        from google.genai import types

        # 建立圖片內容
        image_part = types.Part.from_bytes(
            data=base64.b64decode(image_data),
            mime_type="image/png"
        )

        # 呼叫 API
        response = ai.client.models.generate_content(
            model=ai.model_name,
            contents=[analysis_prompt, image_part]
        )

        result.success = True
        result.analysis = response.text

        # 解析問題和建議
        lines = response.text.split('\n')
        current_section = None

        for line in lines:
            line = line.strip()
            if not line:
                continue

            lower_line = line.lower()
            if '問題' in line or 'issue' in lower_line or 'problem' in lower_line:
                current_section = 'issues'
            elif '建議' in line or '改善' in line or 'recommend' in lower_line or 'suggest' in lower_line:
                current_section = 'recommendations'
            elif line.startswith(('-', '*', '•', '1', '2', '3', '4', '5', '6', '7', '8', '9')):
                # 移除列表符號
                clean_line = line.lstrip('-*•0123456789. ')
                if clean_line:
                    if current_section == 'issues':
                        result.issues.append(clean_line)
                    elif current_section == 'recommendations':
                        result.recommendations.append(clean_line)

    except ImportError:
        result.error = "AI 引擎未安裝。請執行: pip install google-genai"
    except Exception as e:
        result.error = str(e)

    return result


def analyze_url(
    url: str,
    analysis_type: str = "general",
    output_path: Optional[str] = None
) -> VisionResult:
    """
    截圖並分析網頁

    Args:
        url: 要分析的網址
        analysis_type: 分析類型
        output_path: 截圖儲存路徑 (可選)

    Returns:
        VisionResult 物件
    """
    result = VisionResult(success=False, url=url)

    # 檢查 agent-browser
    if not shutil.which('agent-browser'):
        result.error = "agent-browser 未安裝。請執行: npm install -g agent-browser && agent-browser install"
        return result

    # 截圖
    screenshot = take_screenshot(url, output_path)
    if not screenshot:
        result.error = "截圖失敗"
        return result

    result.screenshot_path = screenshot

    # 分析
    analysis_result = analyze_image(screenshot, analysis_type=analysis_type)

    result.success = analysis_result.success
    result.analysis = analysis_result.analysis
    result.issues = analysis_result.issues
    result.recommendations = analysis_result.recommendations
    result.error = analysis_result.error

    return result


def compare_screenshots(
    screenshot1: str,
    screenshot2: str,
    description1: str = "版本 A",
    description2: str = "版本 B"
) -> VisionResult:
    """
    比較兩張截圖 (視覺回歸測試)

    Args:
        screenshot1: 第一張截圖路徑
        screenshot2: 第二張截圖路徑
        description1: 第一張截圖描述
        description2: 第二張截圖描述

    Returns:
        VisionResult 物件
    """
    result = VisionResult(success=False)

    if not Path(screenshot1).exists():
        result.error = f"截圖不存在: {screenshot1}"
        return result

    if not Path(screenshot2).exists():
        result.error = f"截圖不存在: {screenshot2}"
        return result

    prompt = f"""比較這兩張網頁截圖的差異：

第一張：{description1}
第二張：{description2}

請分析：
1. 視覺上的主要差異
2. 版面布局的變化
3. 可能的回歸問題
4. 改善的地方

用正體中文回答，以清單格式呈現。"""

    try:
        from ..ai_engine import AIEngine
        from google.genai import types

        ai = AIEngine()

        # 讀取兩張圖片
        with open(screenshot1, 'rb') as f:
            img1_data = f.read()
        with open(screenshot2, 'rb') as f:
            img2_data = f.read()

        image1_part = types.Part.from_bytes(data=img1_data, mime_type="image/png")
        image2_part = types.Part.from_bytes(data=img2_data, mime_type="image/png")

        response = ai.client.models.generate_content(
            model=ai.model_name,
            contents=[prompt, image1_part, image2_part]
        )

        result.success = True
        result.analysis = response.text

    except Exception as e:
        result.error = str(e)

    return result


__all__ = [
    'VisionResult',
    'check_dependencies',
    'take_screenshot',
    'analyze_image',
    'analyze_url',
    'compare_screenshots'
]
