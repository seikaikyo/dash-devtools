---
title: Node.js auth validator 加 Logto pattern + public-proxy 白名單
type: refactor
status: proposal
created: 2026-05-17
---

# Node.js auth validator 加 Logto pattern + public-proxy 白名單

## 背景

`dash_devtools/validators/backend/nodejs.py:174` `check_auth_middleware`
只偵測 `withApiAuth` 一個 pattern。`withApiAuth` 是 Clerk 時代殘留，
fleet 內所有 repo 在 2026-03-18 已全面遷移到 Logto，沒有任何 repo
使用 `withApiAuth`，導致：

1. **誤判 false positive**：Logto 保護的 endpoint 也被標「可能缺少認證」
2. **不支援 public-proxy 設計選擇**：刻意公開的 proxy endpoint
   （104 職缺搜尋、GCIS 公司資料等）沒有白名單機制可以宣告意圖

shukuyo `api/104-search.js` 是典型受害例：刻意 public 設計卻被誤判。

## 方案

### A. 加 Logto / 通用認證 pattern 偵測

`check_auth_middleware` 加 pattern：

| Pattern | 來源 | 偵測方式 |
|---------|------|---------|
| `withApiAuth` | Clerk（保留向後相容） | substring match |
| `verifyLogtoJWT` | Logto JWT 中間件 | substring match |
| `getLogtoAccessToken` | Logto access token helper | substring match |
| `requireAuth` | 通用 helper（jose / passport / lucia 等） | substring match |
| `event.context.user` | Nuxt server context 直取 user | substring match |
| `await requireUserSession` | sidebase nuxt-auth | substring match |

任一 pattern 出現 → 視為已保護。

### B. Public-proxy 白名單機制

兩種宣告方式（任一即跳過認證檢查）：

1. **檔頭註解標示**：
   ```js
   /**
    * @public-proxy 104 公開職缺搜尋 proxy，刻意無認證
    */
   ```
   偵測 regex：`@public-proxy`

2. **檔名包含 `-public` 或在 `api/public/` 子目錄**：
   既有規則排除 `health` / `public` / `webhook`，加強為更明確路徑檢查
   避免誤判（例如 `api/health-check.js` 應該排除）

### C. Warning 訊息升級

把「可能缺少認證保護 (withApiAuth)」改成：

```
可能缺少認證保護（未偵測到 Logto/Clerk/通用認證 pattern）
若為刻意 public，請加 @public-proxy 註解
```

## 影響範圍

- `dash_devtools/validators/backend/nodejs.py:165-207` `check_auth_middleware`
- 影響 fleet：所有跑 `dash validate` 的 repo（shukuyo / factory / dashai-portfolio / smart-factory-demo 等）
- 預期效果：
  - shukuyo：`api/104-search.js` 加 `@public-proxy` 註解後不再誤判
  - 其他 repo：用 Logto 的 endpoint 不再誤判
  - 未來新 repo：Logto / 通用 pattern 自動偵測

## 測試計畫

1. 對 shukuyo 跑 `dash validate .` → `api/104-search.js` 加註解後應消除警告
2. 對 factory / smart-factory-demo 跑 → 確認 Logto 保護的 endpoint 不再誤判
3. 故意建一個無認證 endpoint → 確認警告仍正確觸發

## 不在範圍

- 不深度驗證 Logto JWT verify 邏輯正確性（pattern match 即視為已宣告，
  實際安全性靠 code review / security-reviewer skill）
- 不改變既有 `withApiAuth` 偵測（向後相容）
