---
title: dash scan 加入 .scanignore 機制
type: feature
status: completed
created: 2026-02-06
---

# dash scan 加入 .scanignore 機制

## 變更內容

在 `dash scan` 指令中加入 `.scanignore` 檔案支援，讓各專案可自訂掃描排除規則，避免誤判。

支援三種排除方式：
1. **檔案/目錄路徑** - 與 `.gitignore` 格式一致
2. **特定 pattern 排除** - `[pattern:名稱]` 語法，只忽略指定檢測規則
3. **註解與空行** - `#` 開頭為註解

`.scanignore` 範例：
```
# 排除外部 skill 的範例檔案
external/neon-skills/

# 只排除特定 pattern
[pattern:PostgreSQL 連線字串] scripts/run-migration.ts
```

## 影響範圍

- `dash_devtools/hooks/pre_push.py` - `run_pre_push_check()` 載入並套用 `.scanignore`
- `dash_devtools/hooks/pre_commit.py` - `run_pre_commit_check()` 同步支援

## 測試計畫

1. 無 `.scanignore` 時行為不變
2. `.scanignore` 中的路徑排除能正確跳過檔案
3. `[pattern:xxx]` 語法能只排除特定 pattern
4. 註解和空行正確忽略
5. 實際在 dash-skills 專案建立 `.scanignore` 驗證

## Checklist

- [x] 實作 `.scanignore` 解析函數
- [x] 整合到 `pre_push.py`
- [x] 整合到 `pre_commit.py`
- [x] dash-skills 建立 `.scanignore` 驗證
