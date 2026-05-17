---
title: spec orphan check 支援 flat OpenSpec 結構
type: refactor
status: proposal
created: 2026-05-17
---

# spec orphan check 支援 flat OpenSpec 結構

## 背景

`dash_devtools/validators/common/spec.py:208` `check_consistency` 偵測
「孤立變更」的邏輯：

1. 掃 `openspec/specs/*.md` 內 `[[change-name]]` 引用
2. `changes/*.md` 沒被任何 spec 引用 → 視為孤立

問題：**這假設所有 repo 用「specs 交叉引用 changes」的階層結構**。
fleet 內多個 repo 用 **flat .md 結構**（每提案獨立 .md，
不互相引用）：

| Repo | OpenSpec 結構 | spec 內 `[[]]` 引用數 |
|------|---------------|---------------------|
| shukuyo | flat | 0 |
| dash-devtools | flat | 0 |
| factory | flat | 0 |

shukuyo 65+ 個 active changes 全部被誤判孤立（輸出截斷顯示前 6 個）。

## 方案

在 `check_consistency` 加 early-return：

```python
def check_consistency(self):
    specs_dir = self.openspec_dir / 'specs'
    changes_dir = self.openspec_dir / 'changes'

    if not specs_dir.exists() or not changes_dir.exists():
        return

    # 收集 specs 中參照的變更
    referenced_changes = set()
    for spec_file in specs_dir.glob('*.md'):
        try:
            content = spec_file.read_text(encoding='utf-8')
            refs = re.findall(r'\[\[([^\]]+)\]\]', content)
            referenced_changes.update(refs)
        except Exception:
            pass

    # 新增：若 specs 內完全沒有 [[]] 引用，視為 flat 結構，跳過 orphan check
    if not referenced_changes:
        existing_changes = {f.stem for f in changes_dir.glob('*.md')}
        self.result['checks']['consistency'] = {
            'specs_count': len(list(specs_dir.glob('*.md'))),
            'changes_count': len(existing_changes),
            'orphan_changes': [],
            'note': 'flat structure detected (specs 內無 [[]] 引用)，略過 orphan check'
        }
        return

    # 既有邏輯
    existing_changes = {f.stem for f in changes_dir.glob('*.md')}
    orphan_changes = existing_changes - referenced_changes
    ...
```

## 設計理由

- **flat 結構是合法選擇**：每提案獨立、不互相引用，archive 用 git mv，
  不需要中央 spec 維護引用清單
- **偵測而非強制**：靠「spec 內有沒有 `[[]]` 引用」自動偵測，repo 不
  需要額外設定檔
- **要轉成階層結構也可以**：第一個 `[[ref]]` 加進 spec 就啟動 orphan
  check，自然 opt-in

## 影響範圍

- `dash_devtools/validators/common/spec.py:208-244` `check_consistency`
- 影響 fleet：所有跑 `dash validate` 且 OpenSpec 為 flat 結構的 repo
- 預期效果：
  - shukuyo：65+ 「孤立變更」警告全部消失
  - dash-devtools 自身：同樣消失
  - 階層結構 repo（若有）：行為不變

## 測試計畫

1. 對 shukuyo 跑 `dash validate .` → 「孤立變更」警告全消
2. 在 shukuyo `openspec/specs/sukuyodo-core.md` 加一個 `[[adjacent-mansion-reference]]` 引用 → 確認 orphan check 自動啟動，其餘 64 個 changes 全被列孤立（opt-in 機制驗證）
3. 移除該引用 → 警告消失

## 不在範圍

- 不改變引用語法（保持 `[[name]]`）
- 不替既有 flat repo 強制遷移到階層結構
