"""
DashAI DevTools - AI Engine
使用 Google Generative AI SDK (Gemini)
"""

import os
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from enum import Enum

# 載入 .env 檔案 (如果存在)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv 是可選的

# 檢查 Google Generative AI SDK
try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError as e:
    GENAI_AVAILABLE = False
    _GENAI_IMPORT_ERROR = str(e)


class AIModel(Enum):
    """可用的 AI 模型"""
    GEMINI_FLASH = "gemini-1.5-flash"  # 速度優先
    GEMINI_PRO = "gemini-1.5-pro"       # 品質優先
    GEMINI_FLASH_8B = "gemini-1.5-flash-8b"  # 輕量版


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
            model: 使用的模型 (預設 gemini-1.5-flash)
            api_key: API Key (預設從環境變數 GEMINI_API_KEY 讀取)
        """
        if not GENAI_AVAILABLE:
            error_detail = _GENAI_IMPORT_ERROR if '_GENAI_IMPORT_ERROR' in dir() else ''
            raise ImportError(
                f"Google Generative AI SDK 未安裝或載入失敗。\n"
                f"錯誤: {error_detail}\n"
                f"請執行: pip install google-generativeai"
            )

        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "未設定 GEMINI_API_KEY。\n"
                "請設定環境變數: export GEMINI_API_KEY='your-api-key'"
            )

        self.model_name = model.value
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(self.model_name)

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

            generation_config = genai.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens
            )

            response = self.model.generate_content(
                full_prompt,
                generation_config=generation_config
            )

            return AIResponse(
                success=True,
                content=response.text,
                model=self.model_name,
                prompt_tokens=response.usage_metadata.prompt_token_count if hasattr(response, 'usage_metadata') else 0,
                completion_tokens=response.usage_metadata.candidates_token_count if hasattr(response, 'usage_metadata') else 0
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
