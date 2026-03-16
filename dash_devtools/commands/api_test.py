"""api-test 指令

整合 schemathesis，從 OpenAPI schema 自動產生 API 測試。
"""

import click
import subprocess
import sys
from dash_devtools.cli import console


@click.command('api-test')
@click.argument('url')
@click.option('--method', '-m', multiple=True, help='只測試指定 HTTP method (可多次指定)')
@click.option('--endpoint', '-e', multiple=True, help='只測試指定端點 (可多次指定)')
@click.option('--count', '-c', type=int, default=50, help='每個端點的測試次數')
@click.option('--auth', '-a', default=None, help='Bearer token')
@click.option('--base-url', '-b', default=None, help='覆蓋 base URL')
@click.option('--dry-run', is_flag=True, help='只顯示偵測到的端點，不執行測試')
@click.option('--workers', '-w', type=int, default=1, help='並行 worker 數量')
def api_test(url, method, endpoint, count, auth, base_url, dry_run, workers):
    """FastAPI 自動化 API 測試 (schemathesis)

    從 OpenAPI schema (通常是 /openapi.json) 自動產生 property-based 測試。
    自動偵測邊界案例、500 errors、schema 不一致等問題。

    URL 可以是：
      - OpenAPI schema URL: https://api.example.com/openapi.json
      - FastAPI 根 URL: https://api.example.com (自動加 /openapi.json)
      - 本地 URL: http://localhost:8000

    使用範例：
      dash api-test https://api.example.com
      dash api-test http://localhost:8000 --count 100
      dash api-test https://api.example.com --endpoint /api/users --method GET
      dash api-test https://api.example.com --auth "my-token"
      dash api-test https://api.example.com --dry-run
    """
    # 自動補 /openapi.json
    schema_url = url
    if not any(url.endswith(suffix) for suffix in ['.json', '.yaml', '.yml']):
        schema_url = url.rstrip('/') + '/openapi.json'

    console.print(f"[cyan]Schemathesis API 測試[/cyan]")
    console.print(f"[dim]Schema: {schema_url}[/dim]")
    console.print(f"[dim]每端點測試次數: {count}[/dim]\n")

    # 建構 schemathesis 指令
    cmd = [sys.executable, '-m', 'schemathesis', 'run', schema_url]

    # 選項
    cmd.extend(['--hypothesis-max-examples', str(count)])

    if base_url:
        cmd.extend(['--base-url', base_url])

    if auth:
        cmd.extend(['--header', f'Authorization: Bearer {auth}'])

    if dry_run:
        cmd.append('--dry-run')

    if workers > 1:
        cmd.extend(['--workers', str(workers)])

    for m in method:
        cmd.extend(['--method', m.upper()])

    for e in endpoint:
        cmd.extend(['--endpoint', e])

    # 加入常用檢查
    cmd.extend([
        '--checks', 'all',
        '--stateful', 'links',
    ])

    if dry_run:
        console.print("[yellow]Dry run: 偵測端點中...[/yellow]\n")
    else:
        console.print("[yellow]執行測試中...[/yellow]\n")

    result = subprocess.run(cmd, text=True, cwd=None)

    if result.returncode == 0:
        console.print("\n[green]API 測試通過[/green]")
    elif result.returncode == 1:
        console.print("\n[red]API 測試發現問題！[/red]")
        raise SystemExit(1)
    elif result.returncode == 127 or 'No module named' in str(result.stderr or ''):
        console.print(
            "[red]schemathesis 未安裝。[/red]\n"
            "  安裝指令: [cyan]pip install dash-devtools[api-test][/cyan]"
        )
        raise SystemExit(1)
    else:
        console.print(f"\n[yellow]測試結束 (exit code: {result.returncode})[/yellow]")
        raise SystemExit(result.returncode)


def register(main):
    main.add_command(api_test)
