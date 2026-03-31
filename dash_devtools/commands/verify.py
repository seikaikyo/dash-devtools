"""verify 指令 - 部署後驗證（Vercel 狀態 + Sentry 錯誤檢查）"""

import os
import subprocess
import json
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError

import click
from dash_devtools.cli import console

SENTRY_ORG = 'dashai-vs'

PROJECT_MAP = {
    'smart-factory-demo': {'url': 'https://factory.dashai.dev', 'sentry': 'factory'},
    'sukuyodo': {'url': 'https://shukuyo.dashai.dev', 'sentry': 'shukuyo'},
}


def detect_project(project_path: str) -> dict | None:
    """從目錄名稱偵測專案對應"""
    name = Path(project_path).resolve().name
    return PROJECT_MAP.get(name)


def check_vercel(project_url: str) -> tuple[str, str]:
    """檢查 Vercel 部署狀態，回傳 (status, detail)"""
    try:
        result = subprocess.run(
            ['vercel', 'ls'],
            capture_output=True, text=True, timeout=15,
            stdin=subprocess.DEVNULL,
        )
        if result.returncode != 0:
            return 'WARN', f'vercel ls 失敗: {result.stderr.strip()}'

        # 解析文字輸出：找第一行有 Ready/Error/Building 的
        lines = result.stdout.strip().splitlines()
        for line in lines:
            if 'Ready' in line:
                return 'READY', line.strip()
            if 'Error' in line:
                return 'ERROR', line.strip()
            if 'Building' in line:
                return 'BUILDING', line.strip()

        return 'READY', lines[-1].strip() if lines else '(無輸出)'
    except FileNotFoundError:
        return 'SKIP', '未安裝 vercel CLI'
    except subprocess.TimeoutExpired:
        return 'WARN', '逾時'
    except Exception as e:
        return 'WARN', str(e)


def check_sentry(project_slug: str) -> tuple[int, list[dict]]:
    """查詢 Sentry 未解決 error，回傳 (count, issues)"""
    token = os.environ.get('SENTRY_AUTH_TOKEN')
    if not token:
        return -1, []

    url = f'https://sentry.io/api/0/projects/{SENTRY_ORG}/{project_slug}/issues/?query=is:unresolved&sort=date&limit=10'
    req = Request(url, headers={'Authorization': f'Bearer {token}'})

    try:
        with urlopen(req, timeout=10) as resp:
            issues = json.loads(resp.read())
            if isinstance(issues, list):
                return len(issues), issues
            return 0, []
    except (URLError, json.JSONDecodeError, Exception):
        return -1, []


@click.command()
@click.argument('project', type=click.Path(), default='.')
@click.option('--url', help='指定驗證的 URL（覆寫自動偵測）')
def verify(project, url):
    """部署後驗證 - Vercel 狀態 + Sentry 錯誤檢查

    自動偵測當前專案，檢查最新部署狀態和未解決錯誤。

    使用範例：
      dash verify .
      dash verify /path/to/project
      dash verify --url https://factory.dashai.dev
    """
    console.print('\n[bold]--- 部署驗證報告 ---[/bold]\n')

    # 偵測專案
    proj = detect_project(project)
    if proj:
        project_url = url or proj['url']
        sentry_slug = proj['sentry']
        console.print(f'[dim]專案:[/dim] {Path(project).resolve().name} -> {project_url}')
    else:
        project_url = url or '(未偵測到)'
        sentry_slug = None
        console.print(f'[yellow]未偵測到已知專案，跳過 Sentry 檢查[/yellow]')

    console.print()

    # Step 1: Vercel
    console.print('[bold]Vercel 部署狀態[/bold]')
    state, detail = check_vercel(project_url)
    if state == 'READY':
        console.print(f'  [green]READY[/green] {detail}')
    elif state == 'SKIP':
        console.print(f'  [dim]SKIP[/dim] {detail}')
    elif state == 'BUILDING':
        console.print(f'  [yellow]BUILDING[/yellow] {detail}')
    elif state == 'ERROR':
        console.print(f'  [red]ERROR[/red] {detail}')
    else:
        console.print(f'  [yellow]{state}[/yellow] {detail}')

    console.print()

    # Step 2: Sentry
    count = 0
    console.print('[bold]Sentry 錯誤檢查[/bold]')
    if not sentry_slug:
        console.print('  [dim]SKIP[/dim] 無對應 Sentry 專案')
    elif not os.environ.get('SENTRY_AUTH_TOKEN'):
        console.print('  [yellow]SKIP[/yellow] 未設定 SENTRY_AUTH_TOKEN 環境變數')
    else:
        count, issues = check_sentry(sentry_slug)
        if count == -1:
            console.print('  [yellow]WARN[/yellow] Sentry API 查詢失敗')
        elif count == 0:
            console.print(f'  [green]OK[/green] {sentry_slug}: 0 筆未解決 error')
        else:
            console.print(f'  [red]ALERT[/red] {sentry_slug}: {count} 筆未解決 error')
            for issue in issues[:5]:
                level = issue.get('level', '?')
                title = issue.get('title', '?')
                cnt = issue.get('count', '?')
                console.print(f'    [{level}] {title} (x{cnt})')

    console.print()

    # 結論
    has_error = (state == 'ERROR') or (sentry_slug and count > 0)
    if has_error:
        console.print('[bold red]結論: 驗證發現問題，請處理[/bold red]\n')
    else:
        console.print('[bold green]結論: 部署驗證通過[/bold green]\n')


def register(main):
    main.add_command(verify)
