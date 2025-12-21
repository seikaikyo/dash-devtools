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
def install(project):
    """安裝 Git Hooks 到專案"""
    from .hooks import install_hooks

    result = install_hooks(project)

    if result['success']:
        console.print("[green]✓ Git Hooks 已安裝[/green]")
        console.print("  已安裝：pre-commit, pre-push")
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


if __name__ == '__main__':
    main()
