---
title: 資安稽核修正（路徑比對、gitignore 語意、指令注入、暫存檔、瀏覽器沙箱）
type: fix
status: completed
created: 2026-08-31
---

# 資安稽核修正

## 背景

dash-devtools 自身是掃描工具與 git pre-push 閘門。稽核發現掃描器的路徑排除邏輯用裸字串包含比對，
導致大量原始碼被靜默跳過而仍回報「通過」。因為 `run_ggshield_scan()` 在未設 `GITGUARDIAN_API_KEY`
（預設狀態）時回 `None`，正則備援才是實際把關者，這個漏掃直接等於閘門失效。

## 變更內容

### 1. High：排除目錄改用路徑元件比對

現況 `any(ignore in str(file_path) for ignore in ignore_dirs)` 拿絕對路徑做裸字串包含比對，
排除清單含 `dist` / `test` / `spec` / `build` / `cache` / `venv` / `coverage`：

- `src/api/distributor.ts`（含 dist）、`src/lib/latest.ts`（含 test）、`src/utils/inspector.ts`（含 spec）全被跳過
- 專案根目錄名稱含這些字（例 `~/github/latest-app`）時，整個 repo 每個檔案都被跳過

改法：新增共用模組 `dash_devtools/path_filters.py`，`is_in_ignored_dir()` 只比對相對路徑的目錄元件，
與既有正確寫法 `dash_devtools/commands/analyze.py:215` 同一口徑。三處呼叫點一起改。

### 2. Medium：gitignore 比對改用 fnmatch 正規語意

現況在合理規則之後多一條 `if pattern in rel_path: return True`（validators 版是
`if line in rel_path or rel_path.startswith(line)`）。`.gitignore` 任何一行只要是路徑子字串就跳過掃描，
常見的 `env/` `lib` `out` `logs` 會誤殺真實原始碼。

改法：`path_filters.is_gitignored()` 用標準庫 `fnmatch` 實作 gitignore 語意（目錄型 pattern 只比對目錄元件、
含斜線的 pattern 錨定根目錄、`!` 反向規則後者覆蓋前者），不引入新相依所以不動打包設定。

### 3. Medium：Lighthouse 與截圖腳本的指令注入

- `dash_devtools/perf.py:28`：內嵌 Node 腳本用 template literal 把 url / categories 拼進字串交給
  `execSync`（走 `/bin/sh`），`categories` 完全沒引號，`url` 在雙引號內但 shell 仍展開 `$(...)` 與反引號。
  改 `execFileSync("npx", [...])` 不經 shell，另在 Python 端擋非 http(s) 的 url。
- `dash_devtools/word_report.py:359`：f-string 把 url 與輸出路徑拼進 JS 字面量再交給 `node -e`。
  稽核判為死碼，實查是活的（`commands/test.py:91` → `run_and_generate_report()` → `take_screenshots()`）。
  改成用 `process.argv` 傳值，腳本內不再有插值。

### 4. Low：pre-push 腳本用可猜的固定暫存檔路徑

`scripts/pre-push:106`、`:144` 用 `/tmp/dash_hook_$$`。改 `mktemp` 加 `trap` 清理，
偵測條件同步由 `[ -f ]` 改 `[ -s ]`（mktemp 會先建好空檔）。

### 5. Low：截圖工具關閉瀏覽器沙箱

`scripts/screenshot.js:34` 的 puppeteer args 含 `--no-sandbox` 與 `--disable-setuid-sandbox`，
而該工具會導向任意 URL 並執行頁面 JS，沙箱是主要隔離邊界。改為預設開啟沙箱，
需要時以環境變數 `DASH_SCREENSHOT_NO_SANDBOX=1` 顯式開啟並標注風險。

## 影響範圍

| 檔案 | 變更 |
|------|------|
| `dash_devtools/path_filters.py` | 新增：共用路徑排除與 gitignore 比對 |
| `dash_devtools/hooks/pre_push.py` | 改用共用模組，移除子字串比對與 `pattern in rel_path` |
| `dash_devtools/validators/security.py` | 同上（`check_sensitive_files` / `_get_source_files` / `_is_gitignored`） |
| `dash_devtools/validators/common/security.py` | 同上（`_should_skip` / `_is_gitignored`） |
| `dash_devtools/perf.py` | `execFileSync` + url scheme 驗證 |
| `dash_devtools/word_report.py` | 截圖腳本改 `process.argv` 傳值 |
| `scripts/pre-push` | `mktemp` + `trap` |
| `scripts/screenshot.js` | 預設開啟沙箱，環境變數才關 |
| `tests/` | 新增：掃描器覆蓋率回歸測試 |

行為影響：掃描範圍變大，先前被靜默跳過的檔案現在會被掃到，既有專案可能因此冒出新的告警。
這是修正而非退步，誤判用 `.scanignore` 處理。

## UI 規格

無 UI 變更。CLI 輸出格式不變。

## 測試計畫

新增 `tests/test_path_filters.py` 與 `tests/test_secret_scan_coverage.py`，用 `tmp_path` 建臨時專案：

1. 路徑含 `dist` / `test` / `spec` 字串的原始檔（`src/api/distributor.ts`、`src/lib/latest.ts`、
   `src/utils/inspector.ts`）內含佔位假金鑰 → 修正前漏掃、修正後掃得到
2. 專案根目錄名稱含 `test`（`latest-app`）→ 修正前整個 repo 漏掃、修正後正常
3. 真正的 `node_modules/` `tests/` `dist/` 目錄仍要被跳過（不得過度修正）
4. `.gitignore` 寫 `logs` 不得誤殺 `src/logs_helper.ts`；寫 `build/` 仍要跳過 `build/generated.js`
5. `fnmatch` 語意：`*.log`、`/anchored`、`dir/`、`!negation`
6. 三個掃描進入點（`run_pre_push_check`、兩支 `SecurityValidator`）同樣覆蓋

驗收：先跑測試看到紅燈（證明漏掃存在），修正後全綠。

## 驗證結果

測試：`python3 -m pytest tests/ -q` → 84 passed。四個測試檔（test_path_filters 35、
test_secret_scan_coverage 34、test_command_injection 10、test_scripts_hardening 5）。
修正前紅燈：掃描覆蓋率 21 failed / 13 passed、注入 6 failed / 4 passed、腳本 2 failed / 3 passed。

同一份 fixture 直接對照（4 個檔案各放一組佔位假金鑰，另有 node_modules/ 與 dist/ 干擾檔）：

| 專案根目錄 | 修正前 | 修正後 |
|---|---|---|
| `latest-app`（名稱含 test） | passed=True，抓到 0 個 | passed=False，抓到 4 個 |
| `neutral-app`（中性名稱） | passed=True，抓到 0 個 | passed=False，抓到 4 個 |

漏掉的四個檔各自命中不同的舊 bug：distributor 含 dist、latest 含 test、inspector 含 spec、
logs_helper 被 `.gitignore` 的 `logs` 子字串誤殺。`node_modules/` 與 `dist/` 修正後仍正確跳過。

真實 repo 的掃描覆蓋率（符合副檔名的檔案）：

| repo | 修正前掃描 | 修正後掃描 | 檔案總數 |
|---|---|---|---|
| dash-devtools | 68 | 84 | 87 |
| sinoauto | 85 | 87 | 26151（其餘為 node_modules 等正常排除） |

dash-devtools 自我掃描（`dash scan .`）與 `run_validation('.')` 修正後結果與 main 一致，
沒有新增誤判。
