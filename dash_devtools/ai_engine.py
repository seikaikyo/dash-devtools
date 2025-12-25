"""
DashAI DevTools - AI Engine
使用 Google GenAI SDK (Gemini) - 新版 API
"""

import os
from pathlib import Path
from typing import Optional
from dataclasses import dataclass
from enum import Enum

# 檢查 Google GenAI SDK (新版)
GENAI_AVAILABLE = False
_GENAI_IMPORT_ERROR = ""

try:
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
except ImportError as e:
    _GENAI_IMPORT_ERROR = str(e)


def _load_dotenv_multi_path() -> list[str]:
    """
    多路徑載入 .env 檔案

    搜尋順序：
    1. 當前工作目錄 .env
    2. 使用者家目錄 ~/.env
    3. dash-devtools 專案目錄 .env

    Returns:
        成功載入的路徑列表
    """
    loaded_paths = []

    try:
        from dotenv import load_dotenv
    except ImportError:
        return loaded_paths  # dotenv 未安裝

    # 搜尋路徑列表
    search_paths = [
        Path.cwd() / '.env',                    # 當前目錄
        Path.home() / '.env',                   # 家目錄
        Path(__file__).parent.parent / '.env',  # dash-devtools 根目錄
    ]

    for env_path in search_paths:
        if env_path.exists():
            load_dotenv(env_path, override=False)  # 不覆蓋已存在的值
            loaded_paths.append(str(env_path))

    return loaded_paths


def _mask_api_key(key: str) -> str:
    """隱藏 API Key 中間字元"""
    if len(key) <= 8:
        return key[:2] + '*' * (len(key) - 2)
    return key[:4] + '*' * (len(key) - 8) + key[-4:]


def _debug_env_info() -> str:
    """產生除錯資訊"""
    lines = []

    # 檢查 GEMINI_API_KEY 是否存在
    api_key = os.environ.get("GEMINI_API_KEY")
    if api_key:
        lines.append(f"  GEMINI_API_KEY: {_mask_api_key(api_key)} (已設定)")
    else:
        lines.append("  GEMINI_API_KEY: (未設定)")

    # 列出所有 GEMINI 或 GOOGLE 相關的環境變數
    related_keys = [k for k in os.environ.keys()
                    if 'GEMINI' in k.upper() or 'GOOGLE' in k.upper()]
    if related_keys:
        lines.append("  相關環境變數:")
        for k in sorted(related_keys):
            val = os.environ.get(k, "")
            if 'KEY' in k.upper() or 'SECRET' in k.upper() or 'TOKEN' in k.upper():
                val = _mask_api_key(val) if val else "(空)"
            else:
                val = val[:50] + "..." if len(val) > 50 else val
            lines.append(f"    {k}: {val}")

    return "\n".join(lines)


class AIModel(Enum):
    """可用的 AI 模型"""
    GEMINI_FLASH = "gemini-2.5-flash"      # 最新快速版
    GEMINI_PRO = "gemini-2.0-flash"        # 穩定版
    GEMINI_FLASH_LITE = "gemini-2.0-flash-lite"  # 輕量版


@dataclass
class AIResponse:
    """AI 回應結構"""
    success: bool
    content: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    error: Optional[str] = None


class AIEngine:
    """
    DashAI DevTools AI 引擎

    使用方式:
        from dash_devtools.ai_engine import AIEngine

        ai = AIEngine()
        response = ai.analyze_code("def foo(): pass")
    """

    def __init__(
        self,
        model: AIModel = AIModel.GEMINI_FLASH,
        api_key: Optional[str] = None
    ):
        """
        初始化 AI 引擎

        Args:
            model: 使用的模型 (預設 gemini-2.5-flash)
            api_key: API Key (預設從環境變數 GEMINI_API_KEY 讀取)
        """
        # 在 __init__ 最前面載入 .env (多路徑搜尋)
        loaded_paths = _load_dotenv_multi_path()

        if not GENAI_AVAILABLE:
            raise ImportError(
                f"Google GenAI SDK 未安裝或載入失敗。\n"
                f"錯誤: {_GENAI_IMPORT_ERROR}\n"
                f"請執行: pip install google-genai"
            )

        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            # 除錯資訊
            debug_info = _debug_env_info()
            loaded_info = ""
            if loaded_paths:
                loaded_info = f"\n已搜尋的 .env 檔案:\n  " + "\n  ".join(loaded_paths)
            else:
                loaded_info = "\n未找到任何 .env 檔案"

            raise ValueError(
                f"未設定 GEMINI_API_KEY。\n"
                f"請設定環境變數: export GEMINI_API_KEY='your-api-key'\n"
                f"或在 .env 檔案中設定: GEMINI_API_KEY=your-api-key\n"
                f"\n診斷資訊:\n{debug_info}"
                f"{loaded_info}"
            )

        self.model_name = model.value
        self.client = genai.Client(api_key=self.api_key)

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048
    ) -> AIResponse:
        """
        生成文字回應

        Args:
            prompt: 使用者提示
            system_prompt: 系統提示 (可選)
            temperature: 創意度 (0.0-1.0)
            max_tokens: 最大輸出 token 數

        Returns:
            AIResponse 物件
        """
        try:
            full_prompt = prompt
            if system_prompt:
                full_prompt = f"{system_prompt}\n\n{prompt}"

            config = types.GenerateContentConfig(
                temperature=temperature,
                max_output_tokens=max_tokens
            )

            response = self.client.models.generate_content(
                model=self.model_name,
                contents=full_prompt,
                config=config
            )

            # 取得 token 使用量
            prompt_tokens = 0
            completion_tokens = 0
            if hasattr(response, 'usage_metadata') and response.usage_metadata:
                prompt_tokens = getattr(response.usage_metadata, 'prompt_token_count', 0) or 0
                completion_tokens = getattr(response.usage_metadata, 'candidates_token_count', 0) or 0

            return AIResponse(
                success=True,
                content=response.text,
                model=self.model_name,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens
            )
        except Exception as e:
            return AIResponse(
                success=False,
                content="",
                model=self.model_name,
                error=str(e)
            )

    def analyze_code(
        self,
        code: str,
        language: str = "auto",
        focus: str = "general"
    ) -> AIResponse:
        """
        分析程式碼

        Args:
            code: 要分析的程式碼
            language: 程式語言 (auto 自動偵測)
            focus: 分析重點 (general/security/performance/quality)

        Returns:
            AIResponse 物件
        """
        focus_prompts = {
            "general": "請全面分析這段程式碼，包括可讀性、潛在問題、最佳實踐建議。",
            "security": "請從安全性角度分析這段程式碼，找出潛在的安全漏洞和風險。",
            "performance": "請從效能角度分析這段程式碼，找出可能的效能瓶頸和優化建議。",
            "quality": "請從程式碼品質角度分析，包括命名規範、結構設計、可維護性。"
        }

        system_prompt = """你是一位資深的軟體工程師和程式碼審查專家。
請用正體中文（台灣用語）回答。
回答要具體、有建設性，並提供改善範例。"""

        prompt = f"""
{focus_prompts.get(focus, focus_prompts["general"])}

程式語言: {language}

```
{code}
```
"""
        return self.generate(prompt, system_prompt, temperature=0.3)

    def suggest_fix(
        self,
        code: str,
        error_message: str,
        language: str = "auto"
    ) -> AIResponse:
        """
        建議修復方案

        Args:
            code: 有問題的程式碼
            error_message: 錯誤訊息
            language: 程式語言

        Returns:
            AIResponse 物件包含修復建議
        """
        system_prompt = """你是一位除錯專家。
請用正體中文（台灣用語）回答。
請提供：
1. 問題原因分析
2. 修復後的完整程式碼
3. 預防類似問題的建議"""

        prompt = f"""
請幫我修復以下程式碼的問題：

錯誤訊息:
```
{error_message}
```

程式碼 ({language}):
```
{code}
```
"""
        return self.generate(prompt, system_prompt, temperature=0.2)

    def generate_tests(
        self,
        code: str,
        framework: str = "auto",
        coverage: str = "comprehensive"
    ) -> AIResponse:
        """
        生成測試程式碼

        Args:
            code: 要測試的程式碼
            framework: 測試框架 (auto/pytest/jest/vitest)
            coverage: 覆蓋範圍 (basic/comprehensive/edge-cases)

        Returns:
            AIResponse 物件包含測試程式碼
        """
        coverage_desc = {
            "basic": "基本功能測試",
            "comprehensive": "全面測試，包括正常流程和邊界情況",
            "edge-cases": "專注於邊界條件和異常處理"
        }

        system_prompt = f"""你是一位測試專家。
請用正體中文註解。
測試框架: {framework}
覆蓋範圍: {coverage_desc.get(coverage, coverage_desc["comprehensive"])}"""

        prompt = f"""
請為以下程式碼生成測試：

```
{code}
```

要求：
- 使用 {framework} 框架
- 包含 {coverage_desc.get(coverage, coverage)} 的測試案例
- 每個測試案例都要有清楚的名稱和註解
"""
        return self.generate(prompt, system_prompt, temperature=0.3)

    def explain_code(
        self,
        code: str,
        detail_level: str = "medium"
    ) -> AIResponse:
        """
        解釋程式碼

        Args:
            code: 要解釋的程式碼
            detail_level: 詳細程度 (brief/medium/detailed)

        Returns:
            AIResponse 物件包含解釋
        """
        detail_prompts = {
            "brief": "請簡潔說明這段程式碼的功能（2-3 句話）。",
            "medium": "請說明這段程式碼的功能、主要邏輯和使用方式。",
            "detailed": "請詳細說明這段程式碼，包括每個函數的作用、資料流、設計模式等。"
        }

        system_prompt = """你是一位技術文件撰寫專家。
請用正體中文（台灣用語）回答。
使用清晰的結構化格式。"""

        prompt = f"""
{detail_prompts.get(detail_level, detail_prompts["medium"])}

```
{code}
```
"""
        return self.generate(prompt, system_prompt, temperature=0.3)

    def review_commit(
        self,
        diff: str,
        commit_message: str = ""
    ) -> AIResponse:
        """
        審查 Git Commit

        Args:
            diff: Git diff 內容
            commit_message: Commit 訊息

        Returns:
            AIResponse 物件包含審查結果
        """
        system_prompt = """你是一位資深的程式碼審查員。
請用正體中文（台灣用語）回答。
審查要點：
1. 程式碼品質
2. 潛在問題
3. 安全性考量
4. Commit 訊息是否清楚描述變更"""

        prompt = f"""
請審查這個 commit:

Commit 訊息: {commit_message or "(無)"}

變更內容:
```diff
{diff}
```
"""
        return self.generate(prompt, system_prompt, temperature=0.3)


# 快速存取函數
def get_ai(model: AIModel = AIModel.GEMINI_FLASH) -> AIEngine:
    """
    取得 AI 引擎實例

    Args:
        model: 使用的模型

    Returns:
        AIEngine 實例
    """
    return AIEngine(model=model)


# CLI 整合
def ai_analyze_command(path: str, focus: str = "general") -> None:
    """CLI 分析指令"""
    try:
        ai = get_ai()
        with open(path, 'r', encoding='utf-8') as f:
            code = f.read()

        response = ai.analyze_code(code, focus=focus)
        if response.success:
            print(response.content)
        else:
            print(f"[!] 錯誤: {response.error}")
    except FileNotFoundError:
        print(f"[!] 找不到檔案: {path}")
    except Exception as e:
        print(f"[!] 錯誤: {e}")
