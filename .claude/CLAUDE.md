# DashAI DevTools

## 專案概述

大許開發工具集 - 整合程式碼品質檢查、測試、部署、AI 輔助的 CLI 工具。

## 核心功能

| 指令 | 功能 | 依賴 |
|------|------|------|
| `dash e2e <url>` | E2E 煙霧測試 | agent-browser |
| `dash perf <url>` | Lighthouse 效能測試 | lighthouse |
| `dash test-suite` | 四大測試套件 | playwright |
| `dash report` | 專案報告產生 | agent-browser |
| `dash vision` | AI 視覺分析 | agent-browser + gemini |
| `dash validate` | 程式碼規範驗證 | - |
| `dash health` | 專案健康評分 | - |
| `dash ai` | AI 程式碼助手 | gemini |

## 瀏覽器自動化 (agent-browser)

### 安裝
```bash
npm install -g agent-browser
agent-browser install
```

### 模組架構
```
dash_devtools/
  browser.py     # agent-browser wrapper (AgentBrowser 類別)
  e2e.py         # E2E 測試 (使用 agent-browser)
  report.py      # 報告截圖 (使用 agent-browser)
  vision/
    __init__.py  # AI 視覺分析 (截圖 + Gemini)
```

### browser.py API
```python
from dash_devtools.browser import AgentBrowser, quick_screenshot

# 完整控制
browser = AgentBrowser()
browser.open("https://example.com")
browser.snapshot(interactive_only=True)  # 取得可互動元素
browser.fill("@e1", "test@example.com")
browser.click("@e2")
browser.screenshot("/tmp/result.png")
browser.close()

# 快速截圖
quick_screenshot("https://example.com", "/tmp/screenshot.png")
```

### vision 模組 API
```python
from dash_devtools.vision import analyze_url, analyze_image, compare_screenshots

# 截圖並分析
result = analyze_url("https://example.com", analysis_type="ui_ux")
print(result.analysis)
print(result.issues)
print(result.recommendations)

# 分析已有截圖
result = analyze_image("/tmp/screenshot.png", analysis_type="accessibility")

# 比較兩張截圖 (視覺回歸)
result = compare_screenshots("before.png", "after.png")
```

### 分析類型
| 類型 | 說明 |
|------|------|
| general | 整體 UI/UX 評估 |
| ui_ux | UI/UX 專家角度分析 |
| accessibility | WCAG 2.1 無障礙檢查 |
| performance | 視覺效能指標 |

## 開發注意事項

1. **瀏覽器資源**: 每次操作後必須呼叫 `browser.close()` 或 `agent-browser close`
2. **超時處理**: 所有網路操作應設定合理超時
3. **錯誤處理**: 截圖失敗時應優雅降級，不阻斷主流程
