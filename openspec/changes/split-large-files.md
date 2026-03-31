---
title: 拆分超過 500 行的大型檔案
type: refactor
status: in-progress
created: 2026-03-15
---

# 拆分超過 500 行的大型檔案

## 現況

dash validate 自己違反自己的 500 行規則，5 個檔案超標：

| 檔案 | 行數 | 超標 | 優先級 |
|------|------|------|--------|
| `cli.py` | 1528 | 3x | 高 |
| `test_suite.py` | 690 | 1.4x | 中 |
| `word_report.py` | 689 | 1.4x | 中 |
| `report.py` | 667 | 1.3x | 中 |
| `browser.py` | 541 | 1.1x | 低 |

## 拆分方案

### cli.py (1528 行) → 目標 < 300 行

目前 cli.py 包含所有 Click 指令定義，是整個 CLI 的進入點。

拆分策略：
```
cli.py (主入口，只做 @main.group 和 import)
├── commands/validate.py    # dash validate
├── commands/health.py      # dash health
├── commands/spec.py        # dash spec
├── commands/test.py        # dash test, test-suite
├── commands/deploy.py      # dash e2e, perf, report
├── commands/db.py          # dash db, dbdiagram
├── commands/ai.py          # dash ai, vision
├── commands/hooks.py       # dash hooks
├── commands/misc.py        # dash doctor, stats, watch, monitor, scan
└── commands/__init__.py    # 註冊所有子指令
```

### test_suite.py (690 行)

拆分策略：
```
test_suite.py (測試套件主邏輯)
├── test_runners/vitest.py   # Vitest 執行器
├── test_runners/jest.py     # Jest 執行器
├── test_runners/karma.py    # Karma 執行器
├── test_runners/pytest.py   # Pytest 執行器
└── test_runners/__init__.py # 統一介面
```

### word_report.py (689 行)

拆分策略：
```
reporters/
├── word_report.py     # Word 報告（縮減到模板 + 資料填充）
├── templates.py       # 報告模板（樣式、表格格式）
└── charts.py          # 圖表產生邏輯
```

### report.py (667 行)

拆分策略：
```
reporters/
├── html_report.py     # HTML 報告產生
├── report_data.py     # 資料收集（測試結果、驗證結果）
└── screenshot.py      # 截圖整合邏輯
```

### browser.py (541 行)

輕微超標，可先不動。如果要拆：
```
browser/
├── core.py        # AgentBrowser 核心類別
├── actions.py     # click, fill, scroll 等動作
└── helpers.py     # quick_screenshot 等便利函式
```

## 影響範圍

| 檔案 | 動作 |
|------|------|
| `cli.py` | 拆分為 `commands/` 目錄 |
| `test_suite.py` | 拆分為 `test_runners/` 目錄 |
| `word_report.py` | 移入 `reporters/` |
| `report.py` | 移入 `reporters/` |
| `__init__.py` | 更新 import 路徑 |
| `pyproject.toml` | 確認 entry point 不變 |

## 原則

- 拆分後外部介面不變（`dash` CLI 指令、import 路徑）
- 用 `__init__.py` re-export 維持向下相容
- 每個新檔案 < 300 行
- 不改功能，只搬程式碼

## 測試計畫

1. `dash --help` 所有指令仍正常顯示
2. `dash validate .` 通過
3. `dash spec list .` 正常
4. `pip install -e .` 安裝成功
5. pre-push hook 正常執行

## Checklist

- [ ] cli.py 拆分為 commands/
- [ ] test_suite.py 拆分為 test_runners/
- [ ] word_report.py 移入 reporters/
- [ ] report.py 移入 reporters/
- [ ] 更新 import 路徑
- [ ] 確認 pyproject.toml entry point
- [ ] 全部指令測試通過
- [ ] dash validate 自己降到 0 警告
