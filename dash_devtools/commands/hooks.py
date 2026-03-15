"""hooks group + install 子指令"""

import click
from dash_devtools.cli import console


@click.group()
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
    from ..hooks import install_hooks

    result = install_hooks(project, strict_test=strict, e2e_url=e2e, strict_e2e=strict_e2e, mobile_e2e=mobile_e2e)

    if result['success']:
        console.print("[green]Git Hooks 已安裝[/green]")
        console.print("  已安裝：pre-commit, pre-push")
        console.print()
        console.print("  [dim]Pre-push 檢查內容：[/dim]")
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


def register(main):
    main.add_command(hooks)
