"""e2e, perf, report, watch 指令"""

import click
from dash_devtools.cli import console


@click.command()
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
    from ..e2e import run_e2e_test, check_agent_browser_installed
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


@click.command()
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
    from ..perf import run_perf_test, print_perf_report
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


@click.command()
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
    from ..report import run_report

    urls = list(url) if url else None
    run_report(
        project,
        include_tests=include_test,
        include_screenshots=screenshot,
        urls=urls,
        open_browser=open_browser
    )


@click.command()
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
    from ..watch import run_watch

    run_watch(project, auto_fix=auto_fix, interval=interval)


def register(main):
    main.add_command(e2e)
    main.add_command(perf)
    main.add_command(report)
    main.add_command(watch)
