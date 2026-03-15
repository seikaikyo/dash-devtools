"""dbdiagram, db group + 子指令"""

import click
from dash_devtools.cli import console


@click.command()
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
    from ..dbdiagram import generate_dbdiagram_link, save_link_to_file

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


@click.group()
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
    from ..database import init_alembic

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
    from ..database import get_migration_status

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
    from ..database import generate_migration

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
    from ..database import run_upgrade

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
    from ..database import run_downgrade

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


def register(main):
    main.add_command(dbdiagram)
    main.add_command(db)
