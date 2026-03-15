"""migrate, docs, release, vision, scan, doctor, monitor 指令"""

import click
from pathlib import Path
from rich.table import Table
from dash_devtools.cli import console, DEFAULT_PROJECTS


@click.command()
@click.argument('project', type=click.Path())
@click.option('--dry-run', is_flag=True, help='預覽模式，不實際修改')
@click.option('--from', 'from_framework', default=None, help='來源框架（已棄用）')
@click.option('--to', 'to_framework', default=None, help='目標框架（已棄用）')
def migrate(project, dry_run, from_framework, to_framework):
    """遷移 UI 框架（已棄用）"""
    from ..migrators import run_migration

    console.print("[yellow]UI 框架遷移功能已棄用。[/yellow]")
    console.print("[dim]標準前端方案為 Vite + Vue 3 + PrimeVue 或 Angular + PrimeNG。[/dim]")

    result = run_migration(project, dry_run=dry_run,
                          from_framework=from_framework,
                          to_framework=to_framework)

    console.print(f"[red]{result.get('error')}[/red]")


@click.group()
def docs():
    """文件產生工具"""
    pass


@docs.command()
@click.argument('project', type=click.Path(), required=False)
@click.option('--all', 'gen_all', is_flag=True, help='產生所有專案的 CLAUDE.md')
def claude(project, gen_all):
    """產生 CLAUDE.md"""
    from ..generators import generate_claude_md

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


@click.group()
def release():
    """版本發布管理"""
    pass


@release.command()
def status():
    """檢視版本狀態"""
    from ..generators import get_release_status

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
    from ..generators import publish_release

    result = publish_release(project, version)

    if result['success']:
        console.print(f"[green]✓ 已發布 {version}[/green]")
    else:
        console.print(f"[red]✗ 發布失敗: {result.get('error')}[/red]")


@click.command()
@click.argument('image', type=click.Path())
@click.option('--output', '-o', type=click.Path(), help='輸出路徑')
def vision(image, output):
    """視覺 AI 分析"""
    from ..vision import analyze_image

    result = analyze_image(image, output=output)
    console.print(result)


@click.command()
@click.argument('project', type=click.Path(), default='.')
def scan(project):
    """掃描機敏資料"""
    from ..hooks import run_pre_push_check

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


@click.command()
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


@click.group()
def monitor():
    """UptimeRobot 服務監控管理

    管理 Render 免費方案的 keep-alive 監控 (UptimeRobot)。

    子指令：
      list      列出所有監控
      add       新增 Render 服務監控
      remove    移除監控
    """
    pass


@monitor.command('list')
def monitor_list():
    """列出所有 UptimeRobot 監控"""
    from ..monitor import list_monitors

    try:
        monitors = list_monitors()
    except RuntimeError as e:
        console.print(f"[red]x {e}[/red]")
        raise SystemExit(1)

    if not monitors:
        console.print("[dim]尚無任何監控[/dim]")
        return

    table = Table(title="UptimeRobot 監控清單")
    table.add_column("名稱", style="cyan")
    table.add_column("URL", style="dim")
    table.add_column("狀態")
    table.add_column("間隔", justify="right")

    for m in monitors:
        status_style = "green" if m["status_code"] == 2 else "red"
        table.add_row(
            m["name"],
            m["url"],
            f"[{status_style}]{m['status']}[/{status_style}]",
            f"{m['interval'] // 60}m",
        )

    console.print(table)


@monitor.command('add')
@click.argument('service_name')
@click.option('--url', '-u', default=None, help='自訂監控 URL (預設: https://{name}.onrender.com/health)')
def monitor_add(service_name, url):
    """新增 Render 服務監控

    SERVICE_NAME: Render 服務名稱 (如 sukuyodo-backend)
    """
    from ..monitor import add_monitor

    try:
        result = add_monitor(service_name, url)
    except RuntimeError as e:
        console.print(f"[red]x {e}[/red]")
        raise SystemExit(1)

    if result["success"]:
        console.print(f"[green]v 已新增監控: {result['name']}[/green]")
        console.print(f"  URL: {result['url']}")
        console.print(f"  間隔: 5 分鐘 (HEAD)")
    else:
        console.print(f"[yellow]! {result['error']}[/yellow]")


@monitor.command('remove')
@click.argument('service_name')
def monitor_remove(service_name):
    """移除監控

    SERVICE_NAME: monitor 名稱或 ID
    """
    from ..monitor import remove_monitor

    try:
        result = remove_monitor(service_name)
    except RuntimeError as e:
        console.print(f"[red]x {e}[/red]")
        raise SystemExit(1)

    if result["success"]:
        console.print(f"[green]v 已移除監控: {result['name']}[/green]")
        console.print(f"  URL: {result['url']}")
    else:
        console.print(f"[red]x {result['error']}[/red]")
        raise SystemExit(1)


def register(main):
    main.add_command(migrate)
    main.add_command(docs)
    main.add_command(release)
    main.add_command(vision)
    main.add_command(scan)
    main.add_command(doctor)
    main.add_command(monitor)
