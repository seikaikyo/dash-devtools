# DashAI DevTools v2.1

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)

**[English](README.en.md)** | **日本語** | **[正體中文](README.md)**

統合開発ツールキット - 検証、テスト、AI分析ツール

## 特徴

- **E2Eテスト**: Vercel Labsの[agent-browser](https://github.com/vercel-labs/agent-browser)によるブラウザ自動化
- **AIビジュアル分析**: スクリーンショット + Gemini AIによるUI/UX、アクセシビリティ、パフォーマンス分析
- **コード品質**: セキュリティ、規約、技術的負債の自動チェック
- **テストスイート**: UIT/Smoke/E2E/UAT完全テスト + Word/Markdownレポート

## インストール

```bash
cd dash-devtools
pip install -e .

# ブラウザ自動化用
npm install -g agent-browser
agent-browser install
```

## コマンド一覧

| カテゴリ | コマンド | 説明 |
|----------|---------|------|
| **検証** | `dash validate` | プロジェクト規約検証 |
| **健全性** | `dash health` | プロジェクト健全性スコア (Lighthouse風) |
| **統計** | `dash stats` | コード統計ダッシュボード |
| **テスト** | `dash test` | テスト実行 (vitest/jest/pytest) |
| **テストスイート** | `dash test-suite` | 4種類テスト (UIT/Smoke/E2E/UAT) + レポート |
| **E2E** | `dash e2e` | E2Eスモークテスト (agent-browser) |
| **レポート** | `dash report` | HTMLレポート生成 |
| **監視** | `dash watch` | リアルタイム監視 |
| **スキャン** | `dash scan` | 機密データスキャン |
| **AI** | `dash ai` | AIコードアシスタント (Gemini) |
| **ビジョン** | `dash vision` | AIビジュアル分析 |
| **データベース** | `dash db` | データベース移行 (Alembic) |
| **図表** | `dash dbdiagram` | データベースERD生成 |
| **診断** | `dash doctor` | 開発環境診断 |

## クイックスタート

### プロジェクト検証

```bash
# スマート検証 (プロジェクトタイプ自動検出)
dash validate /path/to/project

# 検証と自動修正
dash validate /path/to/project --fix

# 全プロジェクト検証
dash validate --all
```

### E2Eスモークテスト

agent-browserでページエラーをチェック:

```bash
# 基本テスト
dash e2e https://your-app.vercel.app

# ページ読み込みのみチェック
dash e2e https://example.com --check load

# タイムアウト延長
dash e2e https://example.com --timeout 60000

# 失敗時スクリーンショット
dash e2e https://example.com --screenshot

# モバイルテスト
dash e2e https://example.com --mobile

# JSON出力
dash e2e https://example.com --json
```

### AIビジュアル分析

スクリーンショット + Gemini AIでUI/UX分析:

```bash
# 基本ビジュアル分析
dash vision https://example.com

# UI/UXエキスパート分析
dash vision https://example.com --type ui_ux

# アクセシビリティ (WCAG 2.1) チェック
dash vision https://example.com --type accessibility

# パフォーマンスビジュアル指標
dash vision https://example.com --type performance

# ローカルスクリーンショット分析
dash vision /path/to/screenshot.png
```

分析タイプ:

| タイプ | 説明 |
|--------|------|
| `general` | 総合UI/UX評価 |
| `ui_ux` | プロフェッショナルUI/UX分析 |
| `accessibility` | WCAG 2.1アクセシビリティチェック |
| `performance` | ビジュアルパフォーマンス指標 |

### ブラウザ自動化API

完全なブラウザ制御のためのPython API:

```python
from dash_devtools.browser import AgentBrowser, quick_screenshot

# クイックスクリーンショット
quick_screenshot("https://example.com", "/tmp/screenshot.png")

# 完全制御
browser = AgentBrowser()
browser.open("https://example.com")
browser.snapshot(interactive_only=True)  # インタラクティブ要素取得
browser.fill("@e1", "test@example.com")  # フォーム入力
browser.click("@e2")                      # ボタンクリック
browser.screenshot("/tmp/result.png")
browser.close()
```

ビジュアル分析API:

```python
from dash_devtools.vision import analyze_url, compare_screenshots

# スクリーンショットと分析
result = analyze_url("https://example.com", analysis_type="ui_ux")
print(result.issues)
print(result.recommendations)

# スクリーンショット比較 (ビジュアルリグレッション)
result = compare_screenshots("before.png", "after.png")
print(result.analysis)
```

### プロジェクト健全性スコア

Lighthouse風スコアリング:

```bash
# 単一プロジェクト
dash health .

# 全プロジェクト
dash health --all

# JSON出力
dash health . --json
```

スコアリングカテゴリ:
- セキュリティ: 機密データ、依存関係の脆弱性
- 品質: コード規約、ファイル構造
- 保守性: 技術的負債、ドキュメント完全性
- パフォーマンス: バンドルサイズ、依存関係数

### テストスイート

完全テストスイート実行とレポート生成:

```bash
# 4種類テスト全て実行
dash test-suite .

# Wordレポート生成
dash test-suite . --word test-report.docx

# Markdownレポート生成
dash test-suite . --md test-report.md

# 特定タイプのみ実行
dash test-suite . --types UIT,Smoke
```

| テストタイプ | 説明 | テストファイル |
|-------------|------|---------------|
| UIT | 単体テスト | `*.spec.ts` |
| Smoke | スモークテスト | `e2e/smoke.spec.ts` |
| E2E | エンドツーエンドテスト | `e2e/mes-system.spec.ts` |
| UAT | 受け入れテスト | `e2e/uat.spec.ts` |

### AIコードアシスタント

Gemini 2.5でコード分析:

```bash
# コード分析
dash ai analyze src/main.py

# セキュリティ分析
dash ai analyze src/api.ts --focus security

# 修正提案
dash ai fix src/main.py -e "TypeError: Cannot read property"

# テスト生成
dash ai test src/utils.py

# コード説明
dash ai explain src/complex-algo.py

# コミットレビュー
dash ai review .
```

必要: `export GEMINI_API_KEY="your-api-key"`

## Git Hooks (Pre-push v3)

グローバルpre-pushフック。全プロジェクトのプッシュ前に自動チェック:

```bash
# グローバルフックのインストール
git config --global core.hooksPath ~/.config/git/hooks
cp scripts/pre-push ~/.config/git/hooks/pre-push
chmod +x ~/.config/git/hooks/pre-push
```

プロジェクトタイプに応じてステップ数を動的に調整:

| ステップ | フロントエンド | バックエンド | 説明 |
|---------|:---:|:---:|------|
| 絵文字スキャン | v | v | git diff変更ファイル + コミットメッセージのみ |
| コミットメッセージ形式 | v | v | 絵文字禁止、`type: 説明` 形式を推奨 |
| 機密データスキャン | v | v | GitGuardianまたはローカルルール |
| TypeScriptビルド | v | - | vue-tsc / ng build / tsc（自動検出） |
| Python Ruff lint | - | v | check + format |
| プロジェクト検証 | v | v | dash validate（簡体字・AI痕跡・品質） |

エラーはプッシュをブロック、警告は通知のみ。各ステップに経過時間を表示。

## Claude Code統合

### Skillインストール

```bash
mkdir -p ~/.claude/skills/agent-browser
curl -o ~/.claude/skills/agent-browser/SKILL.md \
  https://raw.githubusercontent.com/vercel-labs/agent-browser/main/skills/agent-browser/SKILL.md
```

インストール後、Claude Codeはブラウザ自動化タスクにagent-browserを自動的に使用します。

## 開発

```bash
# 開発依存関係インストール
pip install -e ".[dev]"

# テスト実行
pytest

# コードフォーマット
black .
```

## 謝辞

本プロジェクトは以下のオープンソースツールを使用しています:

- **[agent-browser](https://github.com/vercel-labs/agent-browser)** - Vercel Labsによるブラウザ自動化
- **[Playwright](https://playwright.dev/)** - MicrosoftのE2Eテストフレームワーク
- **[Google Gemini](https://ai.google.dev/)** - AIビジュアル分析エンジン
- **[Rich](https://github.com/Textualize/rich)** - ターミナルUI美化

## 更新履歴

### v2.0.0 (2026-05-20)

PyPIに公開。これ以降、READMEの更新履歴とパッケージバージョンを統一。v2.2 (2026-03-15) 以降〜2026-05-17の変更をまとめる。

- **セマンティック検証器**: 4種のセマンティック層検証器を追加 (Next.js SEO・セキュリティヘッダー、i18nキー整合性、a11y)、警告の詳細表示
- **Logto認証パターン検証**: Logto / Clerkと汎用6種のパターンを認識、public proxyは@public-proxy注釈で明示
- **Flat OpenSpecアダプター**: フラットなOpenSpecはorphanチェックを自動スキップ (specsは[[ref]]でopt-in)
- **禁止概念スキャン**: 削除済み概念 (傍通暦・五行・暦注・六害宿など) を自動ブロック
- **アーキテクチャ文書の完全性**: dash architecture check/diffコマンドを追加、pre-push手順5にアーキテクチャチェック
- **オープンソースツール統合**: 9個のOSSツールを統合、healthスコアの精緻化
- **品質・セキュリティ修正**: a11y精度向上 (テキストやsr-onlyを持つボタンを除外)、regex厳格化とtestディレクトリのスキップで誤検出削減、knowledge_ JSONファイルをallowlist化、ggshield stdin pipe修正、verifyコマンド追加

### v2.2 (2026-03-15)

- **大型ファイル分割**: 500行を超えるファイルの警告をすべて解消
  - cli.py 1528 → 62行、`commands/`ディレクトリに分割 (10モジュール)
  - test_suite.py 690 → 393行、`test_runners/`を抽出 (4 runner)
  - word_report.py 689 → 485行、`reporters/templates` + `charts`を抽出
  - report.py 667 → 453行、`reporters/report_data` + `screenshot`を抽出
  - quality.py 510 → 429行、用語定数を`constants.py`に抽出
  - browser.py 541 → 354行、便利関数を`browser_helpers.py`に移動
- **品質修正**: 中国大陸用語の修正、.gitignoreにnode_modules補完
- **dash validate でエラー0・警告0を達成**

### v2.1 (2026-03-14)

- **Pre-push Hook v3**: グローバル版とプロジェクト版を統合、動的ステップ数
  - TypeScriptビルドチェック (vue-tsc / ng build / tsc)
  - コミットメッセージ形式チェック（絵文字禁止）
  - 絵文字スキャンをgit diffに変更（高速化）
  - Python Ruff lint (check + format)
  - エラー/警告の分離、ステップごとの計時
- **品質チェック拡張**
  - 中国大陸用語の禁止語 (56組、出典: pjchender/cn2tw4programmer)
  - AI生成テキストパターン検出 (check_ai_slop)

### v2.0 (2026-02)

- OpenSpec仕様駆動開発 (SDD)
- プロジェクト健全性スコアリング
- コード統計ダッシュボード
- 4種テストスイート (UIT/Smoke/E2E/UAT)
- AIビジュアル分析 (Gemini)
- UptimeRobot監視管理

### v1.0 (2026-01)

- プロジェクト検証 (dash validate)
- 機密データスキャン (dash scan)
- E2Eスモークテスト (agent-browser)
- データベースマイグレーション (Alembic)
- dbdiagram.ioチャート生成

## ライセンス

MIT License - DashAI
