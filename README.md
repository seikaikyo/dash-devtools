# DashAI DevTools

大許開發工具集 - 統一的開發、驗證、遷移工具

## 安裝

```bash
cd dash-devtools
pip install -e .
```

## 工具總覽

| 分類 | 指令 | 用途 |
|------|------|------|
| **驗證** | `dash validate` | 驗證專案符合開發規範 |
| **遷移** | `dash migrate` | UI 框架遷移 |
| **文件** | `dash docs` | 產生文件、CLAUDE.md |
| **發布** | `dash release` | 版本管理、發布流程 |
| **視覺** | `dash vision` | AI 視覺分析工具 |
| **報告** | `dash report` | 產出 HTML/PDF 報告 |

## 快速使用

### 驗證專案

```bash
# 驗證單一專案
dash validate /path/to/project

# 驗證所有專案
dash validate --all

# 只檢查特定項目
dash validate --check security /path/to/project
dash validate --check migration /path/to/project
dash validate --check performance /path/to/project
```

### 遷移 UI 框架

```bash
# 預覽模式 (不實際修改)
dash migrate --dry-run /path/to/project

# 執行遷移
dash migrate /path/to/project

# 指定來源/目標框架
dash migrate --from shoelace --to daisyui /path/to/project
```

### 產生文件

```bash
# 產生 CLAUDE.md
dash docs claude /path/to/project

# 產生 API 文件
dash docs api /path/to/project

# 產生所有文件
dash docs --all
```

### 版本發布

```bash
# 檢視版本狀態
dash release status

# 發布新版本
dash release publish --version 1.2.0 /path/to/project
```

## 驗證項目

### 1. 安全性檢查 (`security`)
- API Key / Token 外洩
- 密碼硬編碼
- .env 檔案提交
- 敏感資料暴露

### 2. 遷移檢查 (`migration`)
- Shoelace 元件殘留 (`<sl-*>`)
- 重複 class 屬性
- CSS 變數殘留 (`--sl-*`)
- Tailwind 設定完整性
- CSS Bundle 大小

### 3. 效能檢查 (`performance`)
- Bundle 大小限制
- 圖片優化
- 未使用的依賴
- Tree-shaking 狀態

### 4. 程式碼品質 (`code_quality`)
- 檔案行數限制 (500 行)
- 命名規範
- 中文註解
- 禁止簡體字

## 設定檔

專案根目錄可建立 `.dashrc.json`：

```json
{
  "validate": {
    "checks": ["security", "migration", "performance", "code_quality"],
    "ignore": ["node_modules", "dist", ".git"],
    "maxFileLines": 500,
    "maxBundleSize": "500KB"
  },
  "migrate": {
    "from": "shoelace",
    "to": "daisyui"
  }
}
```

## 專案清單

| 專案 | 類型 | 說明 |
|------|------|------|
| MES | Angular + PrimeNG | 製造執行系統 |
| SSO | Vite + DaisyUI | 單一登入系統 |
| EAP | Vite + DaisyUI | 設備自動化程式 |
| VAC | Vite + DaisyUI | 休假管理系統 |
| RFID | Vite + DaisyUI | RFID 標籤管理 |
| MCS | Vite + DaisyUI | 物料管控系統 |
| MIDS | Vite + DaisyUI | 物料識別系統 |
| GHG | Vite + DaisyUI | 碳排管理系統 |
| BPM | Vite + DaisyUI | 流程管理系統 |
| RMS | Vite + DaisyUI | 資源管理系統 |
| VisionAI | Python | AI 視覺分析 |
| AOI-8D | Python + Streamlit | AOI 缺陷分析 |

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
