---
title: 整合 9 個 GitHub 開源工具到 dash CLI
type: feature
status: completed
created: 2026-03-16
---

# 整合 9 個 GitHub 開源工具

## 變更內容

新增 9 個子指令，整合業界知名開源工具：

| 子指令 | 工具 | 用途 |
|--------|------|------|
| `dash deps` | deptry + pip-audit | 依賴分析 (孤兒依賴 + 安全漏洞) |
| `dash deadcode` | vulture | 死代碼偵測 |
| `dash complexity` | radon + complexipy | 程式碼複雜度分析 |
| `dash api-test` | schemathesis | FastAPI 自動化 API 測試 |
| `dash changelog` | gitchangelog | 自動產生 CHANGELOG |
| `dash licenses` | pip-licenses + liccheck | 授權合規檢查 |
| `dash bundle` | vite-bundle-visualizer (npx) | Vite bundle 分析 |
| `dash git-stats` | gitinspector | Git 貢獻者統計 |
| `dash env-lint` | dotenv-linter | .env 檔案檢查 |

## 影響範圍

- `pyproject.toml` - 新增 optional dependencies
- `dash_devtools/commands/__init__.py` - 註冊新指令模組
- `dash_devtools/commands/analyze.py` - 新增 (deps, deadcode, complexity, licenses, env-lint)
- `dash_devtools/commands/generate.py` - 新增 (changelog, git-stats, bundle)
- `dash_devtools/commands/api_test.py` - 新增 (api-test)

## 設計原則

1. 所有外部工具放 optional dependencies，不裝也不影響核心功能
2. 未安裝時給出清楚的安裝指引
3. 統一用 Rich 格式化輸出
4. 盡量用工具的 Python API，避免 subprocess

## 測試計畫

1. `pip install -e ".[analyze]"` 安裝成功
2. 每個子指令 `--help` 正常顯示
3. 在 dash-devtools 自身跑 `dash deps`、`dash deadcode`、`dash complexity`
4. 未安裝 optional deps 時提示安裝而非 crash

## Checklist

- [x] pyproject.toml 新增 dependencies
- [x] commands/analyze.py (deps, deadcode, complexity, licenses, env-lint)
- [x] commands/generate.py (changelog, git-stats, bundle)
- [x] commands/api_test.py (api-test)
- [x] commands/__init__.py 註冊
- [x] pip install -e . 測試
- [x] 各指令測試
