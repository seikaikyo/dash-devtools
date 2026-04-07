"""validate 指令"""

import click
from rich.table import Table
from dash_devtools.cli import console, DEFAULT_PROJECTS


@click.command()
@click.argument('project', type=click.Path(), required=False)
@click.option('--all', 'validate_all', is_flag=True, help='驗證所有專案')
@click.option('--check', type=click.Choice(['security', 'migration', 'performance', 'code_quality', 'all', 'smart']),
              default='smart', help='指定檢查類別 (smart=自動偵測專案類型)')
@click.option('--fix', is_flag=True, help='自動修復發現的問題')
@click.option('--output', '-o', type=click.Path(), help='輸出報告路徑')
def validate(project, validate_all, check, fix, output):
    """驗證專案符合開發規範"""
    from ..validators import run_validation
    from ..fixers import run_auto_fix

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

    if has_warnings:
        console.print("\n[yellow]警告詳情：[/yellow]")
        for r in results:
            if r.get('warnings'):
                console.print(f"  [cyan]{r['project']}[/cyan]")
                for w in r['warnings']:
                    console.print(f"    [yellow]• {w}[/yellow]")

    # 顯示修復提示
    if not fix and (failed or has_warnings):
        console.print("\n[yellow]━━━ 修復提示 ━━━[/yellow]")
        console.print("[yellow]  dash validate <專案路徑> --fix[/yellow]")
        console.print("[dim]  自動修復：HTML 標籤修復、空白事件處理器等[/dim]")


def register(main):
    main.add_command(validate)
