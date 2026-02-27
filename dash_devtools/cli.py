#!/usr/bin/env python3
"""
DashAI DevTools CLI - 統一入口

使用方式：
  dash validate /path/to/project
  dash migrate /path/to/project
  dash docs claude /path/to/project
  dash release status
"""

import click
from pathlib import Path
from rich.console import Console
from rich.table import Table

console = Console()

# 基礎路徑 (動態取得使用者 home 目錄)
GITHUB_BASE = Path.home() / 'Documents' / 'github'

# 預設專案清單 (使用動態基礎路徑)
DEFAULT_PROJECT_NAMES = [
    # 系統範例
    'demo-project-1',
    'demo-project-2',
    'demo-project-3',
]

DEFAULT_PROJECTS = [str(GITHUB_BASE / name) for name in DEFAULT_PROJECT_NAMES]


@click.group()
@click.version_option(version="2.0.0")
def main():
    """DashAI DevTools v2 - 大許開發工具集

    新功能：
      health  專案健康評分
      stats   程式碼統計
      watch   即時監控
    """
    pass


@main.command()
@click.argument('project', type=click.Path(), required=False)
@click.option('--all', 'validate_all', is_flag=True, help='驗證所有專案')
@click.option('--check', type=click.Choice(['security', 'migration', 'performance', 'code_quality', 'all', 'smart']),
              default='smart', help='指定檢查項目 (smart=自動偵測專案類型)')
@click.option('--fix', is_flag=True, help='自動修復發現的問題')
@click.option('--output', '-o', type=click.Path(), help='輸出報告路徑')
def validate(project, validate_all, check, fix, output):
    """驗證專案符合開發規範"""
    from .validators import run_validation
    from .fixers import run_auto_fix

    if validate_all:
        projects = DEFAULT_PROJECTS
    elif project:
        projects = [project]
    else:
        console.print("[red]請指定專案路徑或使用 --all[/red]")
        return

    results = run_validation(projects, checks=check, output=output)

    # 如果有錯誤且啟用自動修復
    has_errors = any(not r['passed'] for r in results)
    if fix and has_errors:
        console.print("\n[yellow][FIX] 執行自動修復...[/yellow]")
        fix_results = run_auto_fix(projects)
        for fr in fix_results:
            if fr['fixes']:
                console.print(f"  [green]✓[/green] {fr['project']}: 修復 {len(fr['fixes'])} 個問題")
                for f in fr['fixes']:
                    console.print(f"    • {f}")

        # 重新驗證
        console.print("\n[cyan]重新驗證...[/cyan]")
        results = run_validation(projects, checks=check, output=output)

    # 顯示結果表格
    table = Table(title="驗證結果")
    table.add_column("專案", style="cyan")
    table.add_column("狀態", style="green")
    table.add_column("錯誤", style="red")
    table.add_column("警告", style="yellow")

    for r in results:
        status = "✓ 通過" if r['passed'] else "✗ 失敗"
        table.add_row(
            r['project'],
            status,
            str(len(r.get('errors', []))),
            str(len(r.get('warnings', [])))
        )

    console.print(table)

    # 如果仍有錯誤，顯示詳細資訊
    failed = [r for r in results if not r['passed']]
    has_warnings = any(r.get('warnings') for r in results)

    if failed:
        console.print("\n[red]錯誤詳情：[/red]")
        for r in failed:
            console.print(f"  [cyan]{r['project']}[/cyan]")
            for e in r.get('errors', []):
                console.print(f"    [red]• {e}[/red]")

    # 顯示修復提示
    if not fix and (failed or has_warnings):
        console.print("\n[yellow]━━━ 修復提示 ━━━[/yellow]")
        console.print("[yellow]  dash validate <專案路徑> --fix[/yellow]")
        console.print("[dim]  自動修復：HTML 標籤修復、sl-icon-button label 屬性等[/dim]")


@main.command()
@click.argument('project', type=click.Path())
@click.option('--dry-run', is_flag=True, help='預覽模式，不實際修改')
@click.option('--from', 'from_framework', default='shoelace', help='來源框架')
@click.option('--to', 'to_framework', default='daisyui', help='目標框架')
def migrate(project, dry_run, from_framework, to_framework):
    """遷移 UI 框架"""
    from .migrators import run_migration

    console.print(f"[cyan]遷移專案: {project}[/cyan]")
    console.print(f"[cyan]{from_framework} → {to_framework}[/cyan]")

    if dry_run:
        console.print("[yellow]預覽模式 - 不會實際修改檔案[/yellow]")

    result = run_migration(project, dry_run=dry_run,
                          from_framework=from_framework,
                          to_framework=to_framework)

    if result['success']:
        console.print("[green]遷移完成！[/green]")
    else:
        console.print(f"[red]遷移失敗: {result.get('error')}[/red]")


@main.group()
def docs():
    """文件產生工具"""
    pass


@docs.command()
@click.argument('project', type=click.Path(), required=False)
@click.option('--all', 'gen_all', is_flag=True, help='產生所有專案的 CLAUDE.md')
def claude(project, gen_all):
    """產生 CLAUDE.md"""
    from .generators import generate_claude_md

    if gen_all:
        projects = DEFAULT_PROJECTS
    elif project:
        projects = [project]
    else:
        console.print("[red]請指定專案路徑或使用 --all[/red]")
        return

    for p in projects:
        result = generate_claude_md(p)
        if result['success']:
            console.print(f"[green]✓[/green] {Path(p).name}")
        else:
            console.print(f"[red]✗[/red] {Path(p).name}: {result.get('error')}")


@main.group()
def release():
    """版本發布管理"""
    pass


@release.command()
def status():
    """檢視版本狀態"""
    from .generators import get_release_status

    status = get_release_status()

    table = Table(title="專案版本狀態")
    table.add_column("專案", style="cyan")
    table.add_column("版本", style="green")
    table.add_column("最後更新", style="yellow")

    for project, info in status.items():
        table.add_row(project, info['version'], info['last_update'])

    console.print(table)


@release.command()
@click.argument('project', type=click.Path())
@click.option('--version', '-v', required=True, help='版本號')
def publish(project, version):
    """發布新版本"""
    from .generators import publish_release

    result = publish_release(project, version)

    if result['success']:
        console.print(f"[green]✓ 已發布 {version}[/green]")
    else:
        console.print(f"[red]✗ 發布失敗: {result.get('error')}[/red]")


@main.command()
@click.argument('image', type=click.Path())
@click.option('--output', '-o', type=click.Path(), help='輸出路徑')
def vision(image, output):
    """視覺 AI 分析"""
    from .vision import analyze_image

    result = analyze_image(image, output=output)
    console.print(result)


@main.command()
@click.argument('project', type=click.Path(), default='.')
def scan(project):
    """掃描機敏資料"""
    from .hooks import run_pre_push_check

    console.print("[yellow]🔍 掃描機敏資料...[/yellow]")
    result = run_pre_push_check(project)

    # 顯示使用的掃描引擎
    engine = result.get('engine', '本地規則')
    if engine == 'GitGuardian':
        console.print("[dim]  使用 GitGuardian 引擎[/dim]")

    if result['passed']:
        console.print("[green]✓ 安全檢查通過[/green]")
    else:
        console.print("[red]✗ 發現機敏資料！[/red]")
        for issue in result['issues']:
            console.print(f"  [red]• {issue['file']}: {issue['type']}[/red]")
        raise SystemExit(1)


@main.group()
def hooks():
    """Git Hooks 管理"""
    pass


@hooks.command()
@click.argument('project', type=click.Path(), default='.')
@click.option('--strict', is_flag=True, help='嚴格模式：測試失敗會阻止推送')
@click.option('--e2e', type=str, default=None, help='E2E 測試網址 (每次推送會執行煙霧測試)')
@click.option('--strict-e2e', is_flag=True, help='嚴格 E2E 模式：E2E 失敗會阻止推送')
@click.option('--mobile-e2e', is_flag=True, help='手機版 E2E 測試：同時檢查手機版水平溢出')
def install(project, strict, e2e, strict_e2e, mobile_e2e):
    """安裝 Git Hooks 到專案

    Pre-push 會執行：
    1. 檢查 Emoji
    2. 掃描機敏資料
    3. 驗證專案規範
    4. 執行測試
    5. E2E 煙霧測試 (如有設定)
    6. 手機版 E2E 測試 (如有設定)

    使用範例：
      dash hooks install .
      dash hooks install . --strict
      dash hooks install . --e2e https://example.com
      dash hooks install . --e2e https://example.com --strict-e2e
      dash hooks install . --e2e https://example.com --mobile-e2e
    """
    from .hooks import install_hooks

    result = install_hooks(project, strict_test=strict, e2e_url=e2e, strict_e2e=strict_e2e, mobile_e2e=mobile_e2e)

    if result['success']:
        console.print("[green]Git Hooks 已安裝[/green]")
        console.print("  已安裝：pre-commit, pre-push")
        console.print()
        console.print("  [dim]Pre-push 檢查項目：[/dim]")
        console.print("    1. 檢查 Emoji")
        console.print("    2. 掃描機敏資料")
        console.print("    3. 驗證專案規範")
        console.print("    4. 執行測試")
        console.print("    5. E2E 煙霧測試")
        if mobile_e2e:
            console.print("    6. 手機版 E2E 測試 (水平溢出檢查)")
        if strict:
            console.print()
            console.print("  [yellow]嚴格模式已啟用：測試失敗會阻止推送[/yellow]")
        if e2e:
            console.print()
            console.print(f"  [cyan]E2E 測試：{e2e}[/cyan]")
            if strict_e2e:
                console.print("  [yellow]嚴格 E2E 模式已啟用：E2E 失敗會阻止推送[/yellow]")
            if mobile_e2e:
                console.print("  [cyan]手機版 E2E 已啟用：會同時檢查 375x812 水平溢出[/cyan]")
    else:
        console.print(f"[red]安裝失敗: {result.get('error')}[/red]")


@main.command()
@click.argument('project', type=click.Path(), default='.')
@click.option('--copy', 'do_copy', is_flag=True, help='複製連結到剪貼簿')
@click.option('--open', 'do_open', is_flag=True, help='在瀏覽器開啟')
@click.option('--save', is_flag=True, help='儲存連結到 docs/dbdiagram-link.txt')
def dbdiagram(project, do_copy, do_open, save):
    """產生 dbdiagram.io 資料庫圖表連結

    從 Prisma schema 或 DBML 檔案產生可分享的連結。

    使用範例：
      dash dbdiagram /path/to/project
      dash dbdiagram . --open
      dash dbdiagram . --copy
    """
    from .dbdiagram import generate_dbdiagram_link, save_link_to_file

    console.print("[yellow]📊 產生 dbdiagram.io 連結...[/yellow]")

    result = generate_dbdiagram_link(project)

    if not result['success']:
        console.print(f"[red]✗ {result['error']}[/red]")
        raise SystemExit(1)

    link = result['link']
    console.print(f"[green]✓ 連結已產生[/green]")
    console.print(f"[dim]  來源: {result.get('dbml_path', 'N/A')}[/dim]")
    console.print("")
    console.print(f"[cyan]連結: {link[:80]}...[/cyan]")

    if save:
        output_path = save_link_to_file(project, link)
        console.print(f"[green]✓ 已儲存至 {output_path}[/green]")

    if do_copy:
        try:
            import subprocess
            subprocess.run(['pbcopy'], input=link.encode(), check=True)
            console.print("[green]✓ 已複製到剪貼簿[/green]")
        except Exception:
            console.print("[yellow]無法複製到剪貼簿，請手動複製[/yellow]")
            console.print(link)

    if do_open:
        try:
            import webbrowser
            webbrowser.open(link)
            console.print("[green]✓ 已在瀏覽器開啟[/green]")
        except Exception:
            console.print("[yellow]無法開啟瀏覽器[/yellow]")


# ============================================================
# 資料庫遷移指令
# ============================================================

@main.group()
def db():
    """資料庫遷移管理 (Alembic)

    子指令：
      init      初始化 Alembic
      status    檢視遷移狀態
      generate  產生新的遷移檔
      upgrade   升級到最新版本
      downgrade 降級到指定版本
    """
    pass


@db.command()
@click.argument('project', type=click.Path(), default='.')
def init(project):
    """初始化 Alembic 遷移環境

    使用範例：
      dash db init .
      dash db init /path/to/project
    """
    from .database import init_alembic

    console.print("[cyan]初始化 Alembic...[/cyan]")
    result = init_alembic(project)

    if result['success']:
        console.print("[green]✓ Alembic 初始化完成[/green]")
        console.print(f"  [dim]已建立: {result.get('alembic_dir')}[/dim]")
    else:
        console.print(f"[red]✗ 初始化失敗: {result.get('error')}[/red]")
        raise SystemExit(1)


@db.command('status')
@click.argument('project', type=click.Path(), default='.')
def db_status(project):
    """檢視遷移狀態

    顯示：
    - 目前資料庫版本
    - 待套用的遷移
    - Model 與遷移是否同步

    使用範例：
      dash db status .
    """
    from .database import get_migration_status

    console.print("[cyan]檢查遷移狀態...[/cyan]")
    result = get_migration_status(project)

    if not result['success']:
        console.print(f"[red]✗ {result.get('error')}[/red]")
        raise SystemExit(1)

    console.print(f"  目前版本: [cyan]{result.get('current', 'N/A')}[/cyan]")
    console.print(f"  最新版本: [cyan]{result.get('head', 'N/A')}[/cyan]")

    pending = result.get('pending', [])
    if pending:
        console.print(f"\n  [yellow]待套用遷移 ({len(pending)}):[/yellow]")
        for p in pending:
            console.print(f"    • {p}")
    else:
        console.print("\n  [green]✓ 已是最新版本[/green]")


@db.command()
@click.argument('project', type=click.Path(), default='.')
@click.option('--message', '-m', required=True, help='遷移描述')
@click.option('--autogenerate', '-a', is_flag=True, default=True, help='自動偵測 Model 變更')
def generate(project, message, autogenerate):
    """產生新的遷移檔

    使用範例：
      dash db generate . -m "add user table"
      dash db generate . -m "add index to email"
    """
    from .database import generate_migration

    console.print(f"[cyan]產生遷移: {message}[/cyan]")
    result = generate_migration(project, message, autogenerate=autogenerate)

    if result['success']:
        console.print("[green]✓ 遷移檔已產生[/green]")
        console.print(f"  [dim]{result.get('migration_file')}[/dim]")

        # 安全檢查
        if result.get('warnings'):
            console.print("\n[yellow]警告:[/yellow]")
            for w in result['warnings']:
                console.print(f"  [yellow]• {w}[/yellow]")
    else:
        console.print(f"[red]✗ 產生失敗: {result.get('error')}[/red]")
        raise SystemExit(1)


@db.command()
@click.argument('project', type=click.Path(), default='.')
@click.option('--revision', '-r', default='head', help='目標版本 (預設: head)')
@click.option('--dry-run', is_flag=True, help='預覽模式，顯示 SQL 但不執行')
def upgrade(project, revision, dry_run):
    """升級資料庫到指定版本

    使用範例：
      dash db upgrade .
      dash db upgrade . -r abc123
      dash db upgrade . --dry-run
    """
    from .database import run_upgrade

    if dry_run:
        console.print(f"[yellow]預覽模式 - 升級到 {revision}[/yellow]")
    else:
        console.print(f"[cyan]升級資料庫到 {revision}...[/cyan]")

    result = run_upgrade(project, revision, dry_run=dry_run)

    if result['success']:
        if dry_run:
            console.print("\n[dim]將執行的 SQL:[/dim]")
            console.print(result.get('sql', '(無變更)'))
        else:
            console.print("[green]✓ 升級完成[/green]")
            console.print(f"  [dim]新版本: {result.get('current')}[/dim]")
    else:
        console.print(f"[red]✗ 升級失敗: {result.get('error')}[/red]")
        raise SystemExit(1)


@db.command()
@click.argument('project', type=click.Path(), default='.')
@click.option('--revision', '-r', required=True, help='目標版本')
@click.option('--confirm', is_flag=True, help='確認執行危險操作')
def downgrade(project, revision, confirm):
    """降級資料庫到指定版本

    危險操作！會刪除資料。

    使用範例：
      dash db downgrade . -r abc123 --confirm
      dash db downgrade . -r -1 --confirm  # 降一個版本
    """
    from .database import run_downgrade

    if not confirm:
        console.print("[red]危險操作！降級可能導致資料遺失。[/red]")
        console.print("[yellow]請加上 --confirm 確認執行[/yellow]")
        raise SystemExit(1)

    console.print(f"[yellow]降級資料庫到 {revision}...[/yellow]")
    result = run_downgrade(project, revision)

    if result['success']:
        console.print("[green]✓ 降級完成[/green]")
        console.print(f"  [dim]新版本: {result.get('current')}[/dim]")
    else:
        console.print(f"[red]✗ 降級失敗: {result.get('error')}[/red]")
        raise SystemExit(1)


# ============================================================
# 新功能 v2.0
# ============================================================

@main.command()
@click.argument('project', type=click.Path(), default='.')
@click.option('--all', 'check_all', is_flag=True, help='檢查所有專案')
@click.option('--json', 'output_json', is_flag=True, help='輸出 JSON 格式')
def health(project, check_all, output_json):
    """專案健康評分

    類似 Lighthouse 的評分機制，量化專案品質：
    - 安全性: 機敏資料、依賴漏洞
    - 品質: 程式碼規範、檔案結構
    - 維護性: 技術債務、文件完整度
    - 效能: Bundle 大小、依賴數量

    使用範例：
      dash health .
      dash health /path/to/project
      dash health --all
    """
    from .health import run_health_check, HealthChecker
    import json as json_module

    if check_all:
        projects = DEFAULT_PROJECTS
    else:
        projects = [project]

    results = []
    for p in projects:
        try:
            if output_json:
                checker = HealthChecker(p)
                scores = checker.check_all()
                total = sum(s.score for s in scores.values()) // len(scores)
                results.append({
                    'project': checker.project_name,
                    'total_score': total,
                    'scores': {k: v.score for k, v in scores.items()}
                })
            else:
                result = run_health_check(p)
                results.append(result)
        except Exception as e:
            console.print(f"[red]錯誤: {p} - {e}[/red]")

    if output_json:
        console.print(json_module.dumps(results, indent=2, ensure_ascii=False))


@main.command()
@click.argument('project', type=click.Path(), default='.')
@click.option('--all', 'stats_all', is_flag=True, help='統計所有專案並比較')
def stats(project, stats_all):
    """程式碼統計

    視覺化專案統計資訊：
    - 語言分佈
    - 檔案數量與行數
    - 最大檔案排行
    - 複雜度警告

    使用範例：
      dash stats .
      dash stats /path/to/project
      dash stats --all
    """
    from .stats import run_stats, run_stats_all

    if stats_all:
        run_stats_all(DEFAULT_PROJECTS)
    else:
        run_stats(project)


@main.command('init-test')
@click.argument('project', type=click.Path(), default='.')
@click.option('--e2e', is_flag=True, help='同時設定 Playwright E2E 測試')
def init_test(project, e2e):
    """初始化測試框架

    自動偵測專案類型並設定適合的測試框架：
    - Vite 專案 → Vitest
    - Angular 專案 → Jest
    - 可選 Playwright E2E

    使用範例：
      dash init-test .
      dash init-test . --e2e
    """
    from .init_test import run_init_test

    run_init_test(project, include_e2e=e2e)


@main.command()
@click.argument('project', type=click.Path(), default='.')
@click.option('--all', 'test_all', is_flag=True, help='測試所有專案')
@click.option('--coverage', '-c', is_flag=True, help='產生覆蓋率報告')
@click.option('--verbose', '-v', is_flag=True, help='詳細輸出')
def test(project, test_all, coverage, verbose):
    """執行專案測試

    自動偵測測試框架並執行：
    - pytest (Python)
    - vitest/jest (JavaScript/TypeScript)
    - karma (Angular)

    使用範例：
      dash test .
      dash test . --coverage
      dash test --all
    """
    from .testing import run_test, run_test_all

    if test_all:
        run_test_all(DEFAULT_PROJECTS, coverage=coverage)
    else:
        run_test(project, coverage=coverage, verbose=verbose)


@main.command()
@click.argument('url', type=str)
@click.option('--check', type=click.Choice(['errors', 'load', 'all']), default='errors',
              help='檢查類型 (errors=JS錯誤, load=頁面載入, all=全部)')
@click.option('--timeout', '-t', type=int, default=30000, help='超時時間 (毫秒)')
@click.option('--screenshot', '-s', is_flag=True, help='失敗時自動截圖')
@click.option('--mobile', '-m', is_flag=True, help='手機版測試 (375x812)，檢查水平溢出')
@click.option('--json', 'output_json', is_flag=True, help='輸出 JSON 格式')
def e2e(url, check, timeout, screenshot, mobile, output_json):
    """E2E 煙霧測試

    使用 agent-browser 載入頁面並檢查：
    - JS console 錯誤 (Vue/React TypeError 等)
    - 頁面載入狀態
    - 載入時間
    - 手機版水平溢出 (--mobile)

    需要先安裝 agent-browser:
      npm install -g agent-browser
      agent-browser install

    使用範例：
      dash e2e https://example.com
      dash e2e https://example.com --check load
      dash e2e https://example.com --timeout 60000
      dash e2e https://example.com --screenshot
      dash e2e https://example.com --mobile
      dash e2e https://example.com --mobile --screenshot
      dash e2e https://example.com --json
    """
    from .e2e import run_e2e_test, check_agent_browser_installed
    import json as json_module

    # 檢查 agent-browser 是否安裝
    if not check_agent_browser_installed():
        console.print("[red]agent-browser 未安裝[/red]")
        console.print("[yellow]請執行: npm install -g agent-browser && agent-browser install[/yellow]")
        raise SystemExit(1)

    device_mode = "手機版 (375x812)" if mobile else "桌面版 (1920x1080)"
    console.print(f"[cyan]E2E 測試: {url}[/cyan]")
    options = [f"裝置: {device_mode}", f"檢查類型: {check}", f"超時: {timeout}ms"]
    if screenshot:
        options.append("失敗截圖: ON")
    console.print(f"[dim]  {' | '.join(options)}[/dim]")

    result = run_e2e_test(url, timeout=timeout, check_type=check, screenshot_on_fail=screenshot, mobile=mobile)

    if output_json:
        console.print(json_module.dumps(result, indent=2, ensure_ascii=False))
    else:
        if result['success']:
            console.print(f"[green]v 測試通過[/green]")
            console.print(f"  載入時間: {result['loadTime']}ms")
            console.print(f"  HTTP 狀態: {result['status']}")
            if mobile:
                console.print(f"  [green]手機版無水平溢出[/green]")
            if result.get('warnings'):
                console.print(f"  [yellow]警告: {len(result['warnings'])} 個[/yellow]")
        else:
            console.print(f"[red]x 測試失敗[/red]")
            console.print(f"  HTTP 狀態: {result['status']}")

            # 手機版特別提示
            if result.get('hasHorizontalScroll'):
                console.print(f"\n[red]手機版水平溢出問題：[/red]")
                console.print("  內容超出螢幕寬度，請檢查：")
                console.print("  1. overflow-x: hidden/auto 設定")
                console.print("  2. 頁籤/表格是否有 flex-wrap: nowrap + overflow-x: auto")
                console.print("  3. 寬度是否使用 100% 或 max-width")

            if result.get('errors'):
                console.print(f"\n[red]錯誤 ({len(result['errors'])}):[/red]")
                for err in result['errors'][:5]:
                    console.print(f"  - {err[:100]}...")

            # 顯示截圖路徑
            if result.get('screenshot'):
                console.print(f"\n[yellow]截圖已儲存: {result['screenshot']}[/yellow]")
                console.print("[dim]  使用 Read 工具查看截圖進行除錯[/dim]")

            raise SystemExit(1)


@main.command('test-suite')
@click.argument('project', type=click.Path(), default='.')
@click.option('--types', '-t', type=str, default='UIT,Smoke,E2E,UAT',
              help='測試類型 (逗號分隔): UIT,Smoke,E2E,UAT')
@click.option('--coverage', '-c', is_flag=True, default=True, help='包含覆蓋率報告')
@click.option('--report', '-r', type=click.Path(), help='輸出 JSON 報告路徑')
@click.option('--word', '-w', type=click.Path(), help='輸出 Word 報告路徑')
@click.option('--md', '-m', type=click.Path(), help='輸出 Markdown 報告路徑')
@click.option('--no-screenshots', is_flag=True, help='不擷取系統截圖')
def test_suite(project, types, coverage, report, word, md, no_screenshots):
    """四大類型測試套件

    執行完整測試套件，包含：
    - UIT: 單元測試 (Vitest/Jest/Pytest) + 覆蓋率
    - Smoke: 煙霧測試 (Playwright smoke.spec.ts)
    - E2E: 端對端測試 (Playwright mes-system.spec.ts)
    - UAT: 使用者驗收測試 (Playwright uat.spec.ts)

    報告格式：
    - --word: Word 文件 (含圖表、截圖)
    - --md: Markdown 文件 (適合 GitHub)
    - --report: JSON 原始資料

    使用範例：
      dash test-suite .
      dash test-suite . --types UIT,Smoke
      dash test-suite . --report ./test-report.json
      dash test-suite . --word ./test-report.docx
      dash test-suite . --md ./test-report.md
      dash test-suite . --word report.docx --no-screenshots
    """
    from .test_suite import run_test_suite, run_test_suite_report

    test_types = [t.strip() for t in types.split(',')]

    # 如果指定 Word 報告，使用 word_report 模組
    if word:
        from .word_report import run_and_generate_report
        result = run_and_generate_report(
            project,
            output_path=word,
            test_types=test_types,
            include_screenshots=not no_screenshots
        )
    elif md:
        from .markdown_report import run_and_generate_markdown_report
        result = run_and_generate_markdown_report(
            project,
            output_path=md,
            test_types=test_types,
        )
    elif report:
        result = run_test_suite_report(project, output_path=report)
    else:
        result = run_test_suite(project, test_types=test_types, coverage=coverage)

    if not result.get('success', True):
        raise SystemExit(1)


@main.command('gas-test')
@click.argument('project', type=click.Path(), default=str(Path.home() / 'Documents' / 'github' / 'GAS' / 'mes'))
@click.option('--types', '-t', type=str, default='UIT,Smoke,E2E,UAT',
              help='測試類型 (逗號分隔): UIT,Smoke,E2E,UAT')
@click.option('--word', '-w', type=click.Path(), help='輸出 Word 報告路徑')
@click.option('--url', '-u', type=str, help='GAS 部署 URL (預設使用 MES 正式環境)')
def gas_test(project, types, word, url):
    """GAS MES 四大測試套件

    針對 Google Apps Script MES 系統的專用測試：
    - UIT: 程式碼靜態分析 (Code.js, Database.js, HTML)
    - Smoke: 頁面載入測試 (各頁籤)
    - E2E: 完整流程測試 (登入→操作→驗證)
    - UAT: 角色權限驗證

    使用範例：
      dash gas-test
      dash gas-test /path/to/gas/mes
      dash gas-test --types UIT,Smoke
      dash gas-test --word report.docx
      dash gas-test --url https://script.google.com/macros/s/xxx/exec
    """
    from .gas_mes_test import run_gas_test, run_gas_test_with_report

    test_types = [t.strip() for t in types.split(',')]

    if word:
        result = run_gas_test_with_report(
            project,
            output_path=word,
            test_types=test_types,
            url=url
        )
    else:
        result = run_gas_test(project, test_types=test_types, url=url)

    if not result.get('success', True):
        raise SystemExit(1)


@main.command()
@click.argument('url', type=str)
@click.option('--category', '-c', type=str, default='performance,accessibility,best-practices,seo',
              help='測試類別 (逗號分隔)')
@click.option('--timeout', '-t', type=int, default=120000, help='超時時間 (毫秒)')
@click.option('--json', 'output_json', is_flag=True, help='輸出 JSON 格式')
@click.option('--verbose', '-v', is_flag=True, help='詳細輸出')
def perf(url, category, timeout, output_json, verbose):
    """Lighthouse 效能測試

    分析網站效能並提供改善建議：
    - Performance (效能分數)
    - Accessibility (無障礙)
    - Best Practices (最佳實踐)
    - SEO (搜尋引擎優化)

    使用範例：
      dash perf https://example.com
      dash perf https://example.com -c performance
      dash perf https://example.com --json
      dash perf https://example.com -v
    """
    from .perf import run_perf_test, print_perf_report, check_lighthouse_installed
    import json as json_module

    console.print(f"[cyan]Lighthouse 效能測試: {url}[/cyan]")
    console.print(f"[dim]  類別: {category} | 超時: {timeout}ms[/dim]")
    console.print()

    with console.status("[bold green]正在分析效能..."):
        result = run_perf_test(url, categories=category, timeout=timeout)

    if output_json:
        console.print(json_module.dumps(result, indent=2, ensure_ascii=False))
    else:
        print_perf_report(result, verbose=verbose)

    # 效能分數低於 50 則 exit 1
    if result.get('success') and result.get('scores', {}).get('performance', 0) < 50:
        raise SystemExit(1)
    elif not result.get('success'):
        raise SystemExit(1)


@main.command()
@click.argument('project', type=click.Path(), default='.')
@click.option('--test/--no-test', 'include_test', default=True, help='是否執行測試')
@click.option('--screenshot', '-s', is_flag=True, help='擷取 UI 截圖')
@click.option('--url', '-u', multiple=True, help='截圖的 URL (可多個)')
@click.option('--open/--no-open', 'open_browser', default=True, help='是否開啟瀏覽器')
def report(project, include_test, screenshot, url, open_browser):
    """產生完整專案報告

    整合健康評分、程式碼統計、測試結果、UI 截圖，
    產生專業的 HTML 報告。

    使用範例：
      dash report .
      dash report . --screenshot
      dash report . --screenshot -u http://localhost:3000
      dash report . --no-test
    """
    from .report import run_report

    urls = list(url) if url else None
    run_report(
        project,
        include_tests=include_test,
        include_screenshots=screenshot,
        urls=urls,
        open_browser=open_browser
    )


@main.command()
@click.argument('project', type=click.Path(), default='.')
@click.option('--fix', 'auto_fix', is_flag=True, help='發現問題自動修復')
@click.option('--interval', '-i', type=float, default=1.0, help='檢查間隔(秒)')
def watch(project, auto_fix, interval):
    """即時監控模式

    監控檔案變更並自動執行驗證：
    - 檔案儲存時自動驗證
    - 即時顯示問題
    - 可選自動修復

    使用範例：
      dash watch .
      dash watch /path/to/project
      dash watch . --fix
    """
    from .watch import run_watch

    run_watch(project, auto_fix=auto_fix, interval=interval)


# ============================================================
# AI 引擎指令
# ============================================================

def _handle_ai_error(e: Exception) -> None:
    """處理 AI 相關錯誤，提供精確的修復建議"""
    error_msg = str(e).lower()

    if 'google.genai' in error_msg or 'google-genai' in error_msg:
        console.print("[red]缺少 Google GenAI SDK[/red]")
        console.print("[yellow]請執行: pip install google-genai[/yellow]")
    elif 'dotenv' in error_msg:
        console.print("[red]缺少 python-dotenv[/red]")
        console.print("[yellow]請執行: pip install python-dotenv[/yellow]")
    elif 'gemini_api_key' in error_msg:
        # 顯示完整的錯誤訊息（包含診斷資訊）
        console.print(f"[red]{e}[/red]")
    elif isinstance(e, ImportError):
        console.print(f"[red]模組載入失敗: {e}[/red]")
        console.print("[yellow]請執行: pip install google-genai python-dotenv[/yellow]")
    elif isinstance(e, ValueError):
        console.print(f"[red]設定錯誤: {e}[/red]")
    else:
        console.print(f"[red]錯誤: {e}[/red]")


@main.group()
def ai():
    """AI 程式碼助手 (Gemini 2.5)

    使用 Google GenAI SDK (新版)。
    需設定環境變數 GEMINI_API_KEY。

    子指令：
      analyze   分析程式碼
      fix       建議修復方案
      test      生成測試
      explain   解釋程式碼
      review    審查 commit
    """
    pass


@ai.command()
@click.argument('file', type=click.Path())
@click.option('--focus', '-f', type=click.Choice(['general', 'security', 'performance', 'quality']),
              default='general', help='分析重點')
def analyze(file, focus):
    """分析程式碼

    使用範例：
      dash ai analyze src/main.py
      dash ai analyze src/api.ts --focus security
    """
    try:
        from .ai_engine import get_ai
        ai_engine = get_ai()

        with open(file, 'r', encoding='utf-8') as f:
            code = f.read()

        console.print(f"[cyan]分析中: {file}[/cyan]")
        console.print(f"[dim]重點: {focus}[/dim]\n")

        response = ai_engine.analyze_code(code, focus=focus)
        if response.success:
            console.print(response.content)
        else:
            console.print(f"[red]錯誤: {response.error}[/red]")
    except Exception as e:
        _handle_ai_error(e)


@ai.command()
@click.argument('file', type=click.Path())
@click.option('--error', '-e', required=True, help='錯誤訊息')
def fix(file, error):
    """建議修復方案

    使用範例：
      dash ai fix src/main.py -e "TypeError: Cannot read property"
    """
    try:
        from .ai_engine import get_ai
        ai_engine = get_ai()

        with open(file, 'r', encoding='utf-8') as f:
            code = f.read()

        console.print(f"[cyan]分析錯誤: {file}[/cyan]\n")

        response = ai_engine.suggest_fix(code, error)
        if response.success:
            console.print(response.content)
        else:
            console.print(f"[red]錯誤: {response.error}[/red]")
    except Exception as e:
        _handle_ai_error(e)


@ai.command('test')
@click.argument('file', type=click.Path())
@click.option('--framework', '-f', default='auto', help='測試框架 (auto/pytest/jest/vitest)')
@click.option('--coverage', '-c', type=click.Choice(['basic', 'comprehensive', 'edge-cases']),
              default='comprehensive', help='覆蓋範圍')
def generate_test(file, framework, coverage):
    """生成測試程式碼

    使用範例：
      dash ai test src/utils.py
      dash ai test src/api.ts --framework jest
    """
    try:
        from .ai_engine import get_ai
        ai_engine = get_ai()

        with open(file, 'r', encoding='utf-8') as f:
            code = f.read()

        console.print(f"[cyan]產生測試: {file}[/cyan]\n")

        response = ai_engine.generate_tests(code, framework=framework, coverage=coverage)
        if response.success:
            console.print(response.content)
        else:
            console.print(f"[red]錯誤: {response.error}[/red]")
    except Exception as e:
        _handle_ai_error(e)


@ai.command()
@click.argument('file', type=click.Path())
@click.option('--detail', '-d', type=click.Choice(['brief', 'medium', 'detailed']),
              default='medium', help='詳細程度')
def explain(file, detail):
    """解釋程式碼

    使用範例：
      dash ai explain src/complex-algo.py
      dash ai explain src/auth.ts --detail detailed
    """
    try:
        from .ai_engine import get_ai
        ai_engine = get_ai()

        with open(file, 'r', encoding='utf-8') as f:
            code = f.read()

        console.print(f"[cyan]解釋: {file}[/cyan]\n")

        response = ai_engine.explain_code(code, detail_level=detail)
        if response.success:
            console.print(response.content)
        else:
            console.print(f"[red]錯誤: {response.error}[/red]")
    except Exception as e:
        _handle_ai_error(e)


@ai.command()
@click.argument('project', type=click.Path(), default='.')
def review(project):
    """審查最新 commit

    使用範例：
      dash ai review .
    """
    import subprocess
    try:
        from .ai_engine import get_ai
        ai_engine = get_ai()

        # 取得最新 commit 的 diff
        result = subprocess.run(
            ['git', 'diff', 'HEAD~1', 'HEAD'],
            cwd=project,
            capture_output=True,
            text=True
        )
        diff = result.stdout

        # 取得 commit message
        msg_result = subprocess.run(
            ['git', 'log', '-1', '--pretty=%B'],
            cwd=project,
            capture_output=True,
            text=True
        )
        commit_msg = msg_result.stdout.strip()

        console.print(f"[cyan]審查 commit: {commit_msg[:50]}...[/cyan]\n")

        response = ai_engine.review_commit(diff, commit_msg)
        if response.success:
            console.print(response.content)
        else:
            console.print(f"[red]錯誤: {response.error}[/red]")
    except Exception as e:
        _handle_ai_error(e)


# ============================================================
# OpenSpec 指令 (Spec-Driven Development)
# ============================================================

@main.group()
def spec():
    """OpenSpec 規格驅動開發

    使用 Spec-Driven Development (SDD) 工作流程管理功能規格。

    子指令：
      init      初始化 OpenSpec
      list      列出活動變更
      view      互動式儀表板
      show      顯示變更詳情
      validate  驗證規格格式
      archive   歸檔完成的變更
      status    快速狀態總覽
    """
    pass


@spec.command('init')
@click.argument('project', type=click.Path(), default='.')
def spec_init(project):
    """初始化 OpenSpec

    在專案中建立 openspec/ 目錄結構。

    使用範例：
      dash spec init .
      dash spec init /path/to/project
    """
    from .spec import OpenSpecWrapper

    console.print("[cyan]初始化 OpenSpec...[/cyan]")
    result = OpenSpecWrapper.init(project)

    if result.success:
        console.print("[green]v OpenSpec 初始化完成[/green]")
        console.print(f"  [dim]openspec/ 目錄已建立[/dim]")
        console.print(f"  [dim]specs/    - 功能規格[/dim]")
        console.print(f"  [dim]changes/  - 活動變更[/dim]")
    else:
        console.print(f"[red]x {result.error}[/red]")
        raise SystemExit(1)


@spec.command('list')
@click.argument('project', type=click.Path(), default='.')
def spec_list(project):
    """列出活動變更

    顯示所有待處理的變更提案。

    使用範例：
      dash spec list .
    """
    from .spec import OpenSpecWrapper

    result = OpenSpecWrapper.list_changes(project)

    if result.success:
        changes = result.data.get('changes', [])
        count = result.data.get('count', 0)

        if count == 0:
            console.print("[dim]目前沒有活動變更[/dim]")
        else:
            console.print(f"[cyan]活動變更 ({count}):[/cyan]")
            for change in changes:
                console.print(f"  - {change}")
    else:
        console.print(f"[red]x {result.error}[/red]")
        raise SystemExit(1)


@spec.command('view')
@click.argument('project', type=click.Path(), default='.')
def spec_view(project):
    """互動式儀表板

    開啟 OpenSpec 互動式 TUI 儀表板。

    使用範例：
      dash spec view .
    """
    from .spec import OpenSpecWrapper

    if not OpenSpecWrapper._check_installed():
        console.print("[red]openspec 未安裝[/red]")
        console.print("[yellow]請執行: npm install -g @fission-ai/openspec@latest[/yellow]")
        raise SystemExit(1)

    OpenSpecWrapper.view(project)


@spec.command('show')
@click.argument('project', type=click.Path(), default='.')
@click.argument('change_name', type=str)
def spec_show(project, change_name):
    """顯示變更詳情

    顯示指定變更提案的完整內容。

    使用範例：
      dash spec show . my-feature
    """
    from .spec import OpenSpecWrapper

    result = OpenSpecWrapper.show(project, change_name)

    if result.success:
        console.print(f"[cyan]變更: {change_name}[/cyan]")
        console.print()
        console.print(result.data.get('content', ''))
    else:
        console.print(f"[red]x {result.error}[/red]")
        raise SystemExit(1)


@spec.command('validate')
@click.argument('project', type=click.Path(), default='.')
@click.argument('change_name', type=str)
def spec_validate(project, change_name):
    """驗證規格格式

    檢查變更提案的格式是否正確。

    使用範例：
      dash spec validate . my-feature
    """
    from .spec import OpenSpecWrapper

    console.print(f"[cyan]驗證: {change_name}[/cyan]")
    result = OpenSpecWrapper.validate(project, change_name)

    if result.success and result.data.get('valid'):
        console.print("[green]v 規格格式正確[/green]")
    else:
        console.print(f"[red]x 驗證失敗[/red]")
        if result.error:
            console.print(f"  [red]{result.error}[/red]")
        raise SystemExit(1)


@spec.command('archive')
@click.argument('project', type=click.Path(), default='.')
@click.argument('change_name', type=str)
@click.option('--yes', '-y', is_flag=True, help='自動確認歸檔')
def spec_archive(project, change_name, yes):
    """歸檔完成的變更

    將已完成的變更提案移至歸檔目錄。

    使用範例：
      dash spec archive . my-feature
      dash spec archive . my-feature -y
    """
    from .spec import OpenSpecWrapper

    if not yes:
        console.print(f"[yellow]確定要歸檔 '{change_name}'？[/yellow]")
        console.print("[dim]使用 -y 跳過確認[/dim]")
        if not click.confirm("繼續"):
            return

    result = OpenSpecWrapper.archive(project, change_name, yes=True)

    if result.success:
        console.print(f"[green]v {result.message}[/green]")
    else:
        console.print(f"[red]x {result.error}[/red]")
        raise SystemExit(1)


@spec.command('status')
@click.argument('project', type=click.Path(), default='.')
def spec_status(project):
    """快速狀態總覽

    顯示 OpenSpec 的狀態摘要。

    使用範例：
      dash spec status .
    """
    from .spec import get_spec_status

    status = get_spec_status(project)

    if not status['initialized']:
        console.print("[yellow]OpenSpec 尚未初始化[/yellow]")
        console.print("[dim]執行: dash spec init .[/dim]")
        return

    console.print("[cyan]OpenSpec 狀態[/cyan]")
    console.print(f"  規格數量:     {status['specs_count']}")
    console.print(f"  活動變更:     {status['changes_count']}")
    console.print(f"  已歸檔:       {status['archive_count']}")

    if status['stale_changes']:
        console.print()
        console.print(f"[yellow]過期變更 (超過 7 天):[/yellow]")
        for change in status['stale_changes']:
            console.print(f"  [yellow]-[/yellow] {change}")


@main.command()
def doctor():
    """診斷開發環境

    顯示系統資訊、Python 路徑、套件版本等，方便偵錯。

    使用範例：
      dash doctor
    """
    import sys
    import os
    import platform
    from pathlib import Path

    console.print("[cyan]═══ DashAI DevTools 診斷資訊 ═══[/cyan]\n")

    # 系統資訊
    console.print("[yellow]系統資訊[/yellow]")
    console.print(f"  作業系統: {platform.system()} {platform.release()}")
    console.print(f"  Python 版本: {sys.version.split()[0]}")
    console.print(f"  Python 執行檔: {sys.executable}")
    console.print()

    # 工作目錄
    console.print("[yellow]工作目錄[/yellow]")
    console.print(f"  當前目錄: {os.getcwd()}")
    console.print(f"  家目錄: {Path.home()}")
    console.print()

    # Python 路徑
    console.print("[yellow]Python 路徑 (sys.path)[/yellow]")
    for i, p in enumerate(sys.path, 1):
        console.print(f"  {i}. {p}")
    console.print()

    # 套件資訊
    console.print("[yellow]已安裝套件[/yellow]")
    try:
        import importlib.metadata
        dist = importlib.metadata.distribution('dash-devtools')
        console.print(f"  dash-devtools: {dist.version}")
        console.print(f"  安裝位置: {dist.locate_file('')}")
    except Exception as e:
        console.print(f"  [red]無法取得套件資訊: {e}[/red]")
    console.print()

    # 依賴套件
    console.print("[yellow]核心依賴套件[/yellow]")
    deps = ['click', 'rich', 'pyyaml', 'jinja2']
    for dep in deps:
        try:
            import importlib.metadata
            ver = importlib.metadata.version(dep)
            console.print(f"  ✓ {dep}: {ver}")
        except:
            console.print(f"  ✗ {dep}: [red]未安裝[/red]")
    console.print()

    # 可選依賴
    console.print("[yellow]可選依賴套件[/yellow]")
    optional_deps = [
        ('google-genai', 'AI 功能'),
        ('opencv-python', 'Vision 功能'),
        ('pillow', 'Vision 功能'),
    ]
    for dep, desc in optional_deps:
        try:
            import importlib.metadata
            ver = importlib.metadata.version(dep)
            console.print(f"  ✓ {dep}: {ver} ({desc})")
        except:
            console.print(f"  ✗ {dep}: [dim]未安裝 ({desc})[/dim]")
    console.print()

    # 環境變數
    console.print("[yellow]相關環境變數[/yellow]")
    env_vars = ['GEMINI_API_KEY', 'GITGUARDIAN_API_KEY']
    for var in env_vars:
        val = os.environ.get(var)
        if val:
            console.print(f"  ✓ {var}: [dim]已設定[/dim]")
        else:
            console.print(f"  ✗ {var}: [dim]未設定[/dim]")
    console.print()

    console.print("[green]診斷完成！[/green]")


if __name__ == '__main__':
    main()
