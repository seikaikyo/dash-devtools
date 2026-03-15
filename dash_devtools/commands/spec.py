"""spec group + 所有子指令"""

import click
from dash_devtools.cli import console


@click.group()
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
    from ..spec import OpenSpecWrapper

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
    from ..spec import OpenSpecWrapper

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
    from ..spec import OpenSpecWrapper

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
    from ..spec import OpenSpecWrapper

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
    from ..spec import OpenSpecWrapper

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
    from ..spec import OpenSpecWrapper

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
    from ..spec import get_spec_status

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


def register(main):
    main.add_command(spec)
