# DashAI DevTools v2.0

大許開發工具集 - 統一的開發、驗證、測試、AI 分析工具

## 安裝

```bash
cd dash-devtools
pip install -e .
```

## 工具總覽

| 分類 | 指令 | 用途 |
|------|------|------|
| **驗證** | `dash validate` | 驗證專案符合開發規範 |
| **健康** | `dash health` | 專案健康評分 (類似 Lighthouse) |
| **統計** | `dash stats` | 程式碼統計儀表板 |
| **測試** | `dash test` | 執行測試 (vitest/jest/pytest) |
| **E2E** | `dash e2e` | E2E 煙霧測試 (Puppeteer) |
| **報告** | `dash report` | 產生完整 HTML 報告 |
| **監控** | `dash watch` | 即時監控模式 |
| **掃描** | `dash scan` | 掃描機敏資料 |
| **AI** | `dash ai` | AI 程式碼助手 (Gemini) |
| **資料庫** | `dash db` | 資料庫遷移管理 (Alembic) |
| **圖表** | `dash dbdiagram` | 產生資料庫 ERD 連結 |
| **文件** | `dash docs` | 產生文件、CLAUDE.md |
| **視覺** | `dash vision` | AI 視覺分析工具 |
| **診斷** | `dash doctor` | 診斷開發環境 |

## 快速使用

### 驗證專案

```bash
# 智慧驗證 (自動偵測專案類型)
dash validate /path/to/project

# 驗證並自動修復
dash validate /path/to/project --fix

# 驗證所有專案
dash validate --all

# 只檢查特定項目
dash validate --check security /path/to/project
dash validate --check smart /path/to/project
```

### 自動修復功能

使用 `--fix` 參數可自動修復以下問題：

| 問題類型 | 自動修復 |
|----------|----------|
| 表格內下拉選單 | 轉換為圖示按鈕 |
| 圖示按鈕缺少 title | 自動加入 title 屬性 |
| 白底卡片缺邊框 | 加入 CSS 邊框樣式 |
| Emoji 圖示 | 建議改用 sl-icon |

### 遷移 UI 框架（已暫停）

> **注意**：自動遷移功能已暫停使用。
> UI 框架遷移需要完整理解設計邏輯後手動進行，避免破壞現有 UI/UX。

```bash
# 此指令目前會返回錯誤訊息
dash migrate /path/to/project
```

### 產生文件

```bash
# 產生 CLAUDE.md
dash docs claude /path/to/project

# 產生所有專案的 CLAUDE.md
dash docs claude --all
```

### 版本發布

```bash
# 檢視版本狀態
dash release status

# 發布新版本
dash release publish --version 1.2.0 /path/to/project
```

## 驗證項目

### 智慧驗證 (`smart`)

自動偵測專案類型並執行對應檢查：

| 專案類型 | 偵測方式 | 檢查項目 |
|----------|----------|----------|
| Angular | `angular.json` | PrimeNG、TypeScript、Bundle |
| Vite | `vite` | Shoelace 使用、Emoji 圖示、UX 模式 |
| React | `react` | JSX、Hooks、Bundle |
| Node.js | Express/Fastify | API、Vercel、安全性 |
| Python | `requirements.txt` | AI/ML、模型檔案 |

### UI/UX 檢查

| 檢查項目 | 說明 | 嚴重度 |
|----------|------|--------|
| 表格內下拉選單 | 建議改用圖示按鈕 | [UX] |
| 圖示按鈕缺 title | 影響無障礙性 | [A11Y] |
| 巢狀選單過深 | 超過 2 層影響體驗 | [UX] |
| 白底卡片無邊框 | 難以辨識區域 | [UI] |

### 安全性檢查 (`security`)

- API Key / Token 外洩
- 密碼硬編碼
- .env 檔案提交
- 敏感資料暴露

#### GitGuardian 整合

支援 [GitGuardian](https://www.gitguardian.com/) 掃描引擎，與 GitHub 偵測一致：

```bash
# 安裝 ggshield
pip install ggshield

# 設定 API Key
export GITGUARDIAN_API_KEY="your-api-key"

# 掃描會自動使用 GitGuardian（如果有設定）
dash scan /path/to/project
```

掃描優先順序：
1. **GitGuardian** - 如果有 API Key 且安裝了 ggshield
2. **本地規則** - 備援，使用內建正則表達式

### 資料庫圖表

從 Prisma schema 自動產生 [dbdiagram.io](https://dbdiagram.io) 可分享連結：

```bash
# 產生連結
dash dbdiagram /path/to/project

# 開啟瀏覽器
dash dbdiagram . --open

# 複製到剪貼簿
dash dbdiagram . --copy

# 儲存到檔案
dash dbdiagram . --save
```

#### Prisma 設定

在 `schema.prisma` 加入：

```prisma
generator dbml {
  provider   = "prisma-dbml-generator"
  output     = "../docs"
  outputName = "schema.dbml"
}
```

安裝套件：

```bash
npm install -D prisma-dbml-generator
```

執行 `npx prisma generate` 後會產生 DBML 檔案，`dash dbdiagram` 會自動編碼為可分享連結。

**注意**：dbdiagram.io 的 DBML-in-Link 功能完全免費，不需要帳號也不需要 API Key

### 程式碼品質 (`code_quality`)

- 檔案行數限制 (500 行)
- 命名規範 (kebab-case)
- 禁止 Emoji (程式碼中)
- 禁止簡體字

## v2.0 新功能

### 專案健康評分

類似 Lighthouse 的評分機制：

```bash
# 單一專案
dash health .

# 所有專案
dash health --all

# JSON 輸出
dash health . --json
```

評分項目：
- 安全性：機敏資料、依賴漏洞
- 品質：程式碼規範、檔案結構
- 維護性：技術債務、文件完整度
- 效能：Bundle 大小、依賴數量

### 程式碼統計

```bash
# 單一專案
dash stats .

# 比較所有專案
dash stats --all
```

顯示：語言分佈、檔案數量與行數、最大檔案排行、複雜度警告

### 測試執行

```bash
# 執行測試
dash test .

# 含覆蓋率報告
dash test . --coverage

# 測試所有專案
dash test --all
```

自動偵測：vitest、jest、karma、pytest

### E2E 煙霧測試

使用 Puppeteer 檢查頁面 JS 錯誤：

```bash
# 基本測試
dash e2e https://your-app.vercel.app

# 只檢查頁面載入
dash e2e https://example.com --check load

# 延長超時
dash e2e https://example.com --timeout 60000

# JSON 輸出
dash e2e https://example.com --json
```

需要先安裝 Puppeteer：`npm install puppeteer`

### 專案報告

產生完整 HTML 報告：

```bash
# 基本報告
dash report .

# 含 UI 截圖
dash report . --screenshot -u http://localhost:3000

# 不執行測試
dash report . --no-test
```

### 即時監控

```bash
# 監控檔案變更
dash watch .

# 發現問題自動修復
dash watch . --fix
```

### AI 程式碼助手

使用 Gemini 2.5 分析程式碼：

```bash
# 分析程式碼
dash ai analyze src/main.py

# 安全分析
dash ai analyze src/api.ts --focus security

# 建議修復
dash ai fix src/main.py -e "TypeError: Cannot read property"

# 生成測試
dash ai test src/utils.py

# 解釋程式碼
dash ai explain src/complex-algo.py

# 審查 commit
dash ai review .
```

需設定環境變數：`export GEMINI_API_KEY="your-api-key"`

### 資料庫遷移

Alembic 整合：

```bash
# 初始化
dash db init .

# 檢視狀態
dash db status .

# 產生遷移
dash db generate . -m "add user table"

# 升級
dash db upgrade .

# 降級（需確認）
dash db downgrade . -r -1 --confirm
```

### 診斷工具

```bash
dash doctor
```

顯示：系統資訊、Python 路徑、套件版本、環境變數

## Git Hooks

安裝 pre-push hook 自動驗證：

```bash
# 基本安裝
dash hooks install .

# 嚴格模式：測試失敗會阻止推送
dash hooks install . --strict

# 啟用 E2E 煙霧測試
dash hooks install . --e2e https://your-app.vercel.app

# 嚴格 E2E 模式：E2E 失敗會阻止推送
dash hooks install . --e2e https://your-app.vercel.app --strict-e2e
```

Push 前會自動執行：
1. 檢查 Emoji
2. 掃描機敏資料 (GitGuardian 或本地規則)
3. 驗證專案規範
4. 執行測試 (vitest/jest/pytest)
5. E2E 煙霧測試 (如有設定)

## 模板

位於 `templates/` 目錄：

| 模板 | 說明 |
|------|------|
| `deploy-netlify.yml` | GitHub Actions Netlify 備援部署 |

---

# Claude Code 指令集指南

## 內建指令總覽

### 會話管理

| 指令 | 功能 | 說明 |
|------|------|------|
| `/clear` | 清空對話 | 重新開始對話 |
| `/resume [session]` | 恢復對話 | 按 ID 或名稱恢復 |
| `/compact [指令]` | 壓縮對話 | 節省 token，可指定焦點 |
| `/rewind` | 回退 | 回退對話和程式碼變更 |
| `/rename <name>` | 重新命名 | 為當前會話命名 |
| `/exit` | 退出 | 結束 CLI |

### 設定與配置

| 指令 | 功能 | 說明 |
|------|------|------|
| `/config` | 設定介面 | 開啟設定頁面 |
| `/model` | 切換模型 | 選擇 AI 模型 |
| `/permissions` | 權限管理 | 查看/更新工具權限 |
| `/settings` | 設定管理 | 管理所有設定 |
| `/sandbox` | 沙箱模式 | 啟用安全沙箱 |
| `/status` | 狀態資訊 | 版本、模型、帳號狀態 |

### 工具與整合

| 指令 | 功能 | 說明 |
|------|------|------|
| `/mcp` | MCP 伺服器 | 管理 MCP 連接 |
| `/hooks` | Hooks 設定 | 管理工具事件鉤子 |
| `/ide` | IDE 整合 | 管理編輯器整合 |
| `/plugin` | 插件管理 | 管理 Claude Code 插件 |
| `/agents` | 代理管理 | 管理自定義子代理 |

### 開發與專案

| 指令 | 功能 | 說明 |
|------|------|------|
| `/init` | 初始化 | 建立 CLAUDE.md |
| `/memory` | 編輯記憶 | 編輯 CLAUDE.md |
| `/review` | 程式碼審查 | 請求審查 |
| `/add-dir` | 新增目錄 | 添加工作目錄 |

### 資訊與統計

| 指令 | 功能 | 說明 |
|------|------|------|
| `/cost` | Token 用量 | 顯示使用統計 |
| `/context` | 上下文視覺化 | 彩色網格顯示 |
| `/todos` | 待辦事項 | 列出當前 TODO |
| `/stats` | 使用統計 | 日常用法、連勝記錄 |
| `/usage` | 用量限制 | 訂閱計劃使用量 |

### 系統與診斷

| 指令 | 功能 | 說明 |
|------|------|------|
| `/doctor` | 健康檢查 | 檢查安裝狀態 |
| `/bug` | 回報 Bug | 發送至 Anthropic |
| `/release-notes` | 發行說明 | 查看更新內容 |
| `/login` / `/logout` | 帳號管理 | 登入/登出 |

### 輸出與匯出

| 指令 | 功能 | 說明 |
|------|------|------|
| `/vim` | Vim 模式 | 進入 Vim 編輯模式 |
| `/export [file]` | 匯出對話 | 匯出到檔案或剪貼簿 |
| `/output-style` | 輸出樣式 | 設定回應格式 |

---

## 自定義指令 (Slash Commands)

### 建立位置

| 範圍 | 路徑 | 說明 |
|------|------|------|
| 專案級 | `.claude/commands/xxx.md` | 與團隊共享 |
| 個人級 | `~/.claude/commands/xxx.md` | 跨專案可用 |

### 基本格式

```markdown
---
description: 指令說明（必填）
argument-hint: [參數提示]
allowed-tools: Bash(npm:*), Read, Edit
---

# 指令內容

你的提示詞內容...
```

### Frontmatter 選項

| 選項 | 必填 | 說明 |
|------|------|------|
| `description` | 是 | 指令說明 |
| `argument-hint` | 否 | 參數提示 |
| `allowed-tools` | 否 | 允許的工具 |
| `model` | 否 | 指定模型 |

### 範例：Chrome 截圖指令

```markdown
---
description: Chrome 截圖或輸出 PDF
argument-hint: <url> [--pdf]
allowed-tools: Bash(*/Google Chrome*:*), Read
---

截圖網頁並進行 UI/UX 分析。

使用方式：
- `/chrome https://example.com` - 截圖
- `/chrome https://example.com --pdf` - 輸出 PDF
```

### 動態內容

使用 `!` 前綴執行 Bash 指令：

```markdown
當前狀態：!`git status`
最近提交：!`git log -3 --oneline`
```

使用 `@` 前綴引用檔案：

```markdown
請參考 @src/utils/helpers.js 的實作
```

---

## Skills（複雜工作流）

### 與 Slash Commands 差異

| 項目 | Slash Commands | Skills |
|------|----------------|--------|
| 複雜度 | 簡單提示 | 複雜工作流 |
| 結構 | 單一 `.md` 檔 | 目錄 + 多檔案 |
| 觸發 | 手動 `/command` | 自動偵測上下文 |
| 適用 | 常用指令 | 團隊標準流程 |

### 目錄結構

```
.claude/skills/my-skill/
├── SKILL.md          # 必須 - 主要說明
├── REFERENCE.md      # 選用 - API 參考
├── EXAMPLES.md       # 選用 - 使用範例
└── scripts/          # 選用 - 輔助腳本
    └── helper.py
```

### SKILL.md 格式

```markdown
---
name: skill-name
description: 簡短說明（何時使用）
allowed-tools: Read, Bash(npm:*)
---

# Skill 名稱

## 何時使用
描述觸發條件...

## 步驟
1. 步驟一
2. 步驟二

## 範例
具體使用範例...
```

---

## CLI 參數

### 啟動方式

```bash
claude                         # 交互模式
claude "問題"                  # 帶初始提示
claude -p "問題"               # 非交互模式
claude -c                      # 恢復最近對話
claude -r "session-name"       # 恢復特定會話
cat file | claude -p "問題"    # 管道輸入
```

### 常用參數

| 參數 | 說明 |
|------|------|
| `--model <model>` | 指定模型 |
| `--add-dir <path>` | 添加工作目錄 |
| `--permission-mode plan` | Plan 模式 |
| `--tools "Bash,Edit,Read"` | 指定工具 |
| `--append-system-prompt` | 追加系統提示 |

---

## 專案清單

| 專案 | 類型 | 說明 |
|------|------|------|
| MES 製造執行 | Angular + PrimeNG | 再生廠製造執行系統 |
| SSO 管理後台 | Vite + Shoelace | 用戶與權限管理 |
| EAP 設備自動化 | Vite + Shoelace | 設備自動化平台 |
| VAC 承攬商門禁 | Vite + Shoelace | 承攬商門禁管理系統 |
| RFID 追蹤 | Vite + Shoelace | RFID 標籤追蹤系統 |
| MCS 物料控制 | Vite + Shoelace | 物料控制系統 |
| MIDS 材料追蹤 | Vite + Shoelace | 材料識別與追蹤系統 |
| GHG 碳排管理 | Vite + Shoelace | 溫室氣體排放管理系統 |
| BPM 簽核流程 | Vite + Shoelace | 簽核流程管理系統 |
| RMS 配方管理 | Vite + Shoelace | 配方管理系統 |
| 8D 問題管理 | Vite + Shoelace | 8D 問題解決流程管理 |
| Vision AI | Python | AI 影像辨識系統 |
| API Center | Vite + Shoelace | API 管理中心與開發文件 |

## 開發

```bash
# 安裝開發依賴
pip install -e ".[dev]"

# 執行測試
pytest

# 格式化
black .
```

## 授權

MIT License - DashAI
