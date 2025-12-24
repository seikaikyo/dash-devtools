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

# 預設專案清單
DEFAULT_PROJECTS = [
    '${HOME}/Documents/github/VAC',
    '${HOME}/Documents/github/RFID',
    '${HOME}/Documents/github/jinkochino',
    '${HOME}/Documents/github/MCS',
    '${HOME}/Documents/github/MIDS',
    '${HOME}/Documents/github/GHG',
    '${HOME}/Documents/github/DEMO_8D',
    '${HOME}/Documents/github/BPM',
    '${HOME}/Documents/github/RMS',
    '${HOME}/Documents/github/SSO',
    '${HOME}/Documents/github/EAP',
    '${HOME}/Documents/github/MES',
]


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
@click.argument('project', type=click.Path(exists=True), required=False)
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
@click.argument('project', type=click.Path(exists=True))
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
@click.argument('project', type=click.Path(exists=True), required=False)
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
@click.argument('project', type=click.Path(exists=True))
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
@click.argument('image', type=click.Path(exists=True))
@click.option('--output', '-o', type=click.Path(), help='輸出路徑')
def vision(image, output):
    """視覺 AI 分析"""
    from .vision import analyze_image

    result = analyze_image(image, output=output)
    console.print(result)


@main.command()
@click.argument('project', type=click.Path(exists=True), default='.')
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
@click.argument('project', type=click.Path(exists=True), default='.')
@click.option('--strict', is_flag=True, help='嚴格模式：測試失敗會阻止推送')
def install(project, strict):
    """安裝 Git Hooks 到專案

    Pre-push 會執行：
    1. 檢查 Emoji
    2. 掃描機敏資料
    3. 驗證專案規範
    4. 執行測試

    使用範例：
      dash hooks install .
      dash hooks install . --strict
    """
    from .hooks import install_hooks

    result = install_hooks(project, strict_test=strict)

    if result['success']:
        console.print("[green]✓ Git Hooks 已安裝[/green]")
        console.print("  已安裝：pre-commit, pre-push")
        console.print()
        console.print("  [dim]Pre-push 檢查項目：[/dim]")
        console.print("    1. 檢查 Emoji")
        console.print("    2. 掃描機敏資料")
        console.print("    3. 驗證專案規範")
        console.print("    4. 執行測試")
        if strict:
            console.print()
            console.print("  [yellow]嚴格模式已啟用：測試失敗會阻止推送[/yellow]")
    else:
        console.print(f"[red]✗ 安裝失敗: {result.get('error')}[/red]")


@main.command()
@click.argument('project', type=click.Path(exists=True), default='.')
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
@click.argument('project', type=click.Path(exists=True), default='.')
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
@click.argument('project', type=click.Path(exists=True), default='.')
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
@click.argument('project', type=click.Path(exists=True), default='.')
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
@click.argument('project', type=click.Path(exists=True), default='.')
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
@click.argument('project', type=click.Path(exists=True), default='.')
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
@click.argument('project', type=click.Path(exists=True), default='.')
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
@click.argument('project', type=click.Path(exists=True), default='.')
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
@click.argument('project', type=click.Path(exists=True), default='.')
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
@click.argument('project', type=click.Path(exists=True), default='.')
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
@click.argument('project', type=click.Path(exists=True), default='.')
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
@click.argument('project', type=click.Path(exists=True), default='.')
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

@main.group()
def ai():
    """AI 程式碼助手 (Gemini)

    使用 Google Generative AI SDK。
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
@click.argument('file', type=click.Path(exists=True))
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
    except ImportError as e:
        console.print(f"[red]需要安裝 AI 套件: pip install dash-devtools[ai][/red]")
        console.print(f"[dim]{e}[/dim]")
    except ValueError as e:
        console.print(f"[red]{e}[/red]")


@ai.command()
@click.argument('file', type=click.Path(exists=True))
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
    except ImportError:
        console.print(f"[red]需要安裝 AI 套件: pip install dash-devtools[ai][/red]")
    except ValueError as e:
        console.print(f"[red]{e}[/red]")


@ai.command('test')
@click.argument('file', type=click.Path(exists=True))
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
    except ImportError:
        console.print(f"[red]需要安裝 AI 套件: pip install dash-devtools[ai][/red]")
    except ValueError as e:
        console.print(f"[red]{e}[/red]")


@ai.command()
@click.argument('file', type=click.Path(exists=True))
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
    except ImportError:
        console.print(f"[red]需要安裝 AI 套件: pip install dash-devtools[ai][/red]")
    except ValueError as e:
        console.print(f"[red]{e}[/red]")


@ai.command()
@click.argument('project', type=click.Path(exists=True), default='.')
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
    except ImportError:
        console.print(f"[red]需要安裝 AI 套件: pip install dash-devtools[ai][/red]")
    except ValueError as e:
        console.print(f"[red]{e}[/red]")
    except Exception as e:
        console.print(f"[red]錯誤: {e}[/red]")


if __name__ == '__main__':
    main()
