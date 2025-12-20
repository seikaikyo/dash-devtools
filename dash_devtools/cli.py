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
@click.version_option(version="1.0.0")
def main():
    """DashAI DevTools - 大許開發工具集"""
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
        console.print("[dim]  自動修復：下拉選單轉圖示按鈕、加入 title 屬性、卡片邊框等[/dim]")


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


if __name__ == '__main__':
    main()
