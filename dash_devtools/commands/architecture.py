"""architecture 指令 - 檢查專案架構文件完整性"""

import click
import os
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
from dash_devtools.cli import console, DEFAULT_PROJECTS


def _check_file(project_path, filename, required_for=None):
    """檢查檔案是否存在及新鮮度"""
    filepath = Path(project_path) / filename
    if not filepath.exists():
        if required_for and not required_for(project_path):
            return 'N/A', None
        return 'MISSING', None

    # 檢查新鮮度：用 git log 取最後修改日期
    try:
        result = subprocess.run(
            ['git', 'log', '-1', '--format=%ci', '--', filename],
            cwd=project_path, capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0 and result.stdout.strip():
            last_modified = datetime.fromisoformat(
                result.stdout.strip().replace(' +', '+').replace(' -', '-')
            )
            days_ago = (datetime.now(last_modified.tzinfo) - last_modified).days
            if days_ago > 30:
                return f'STALE ({days_ago}d)', days_ago
            return 'OK', days_ago
    except Exception:
        pass

    return 'OK', None


def _is_frontend(project_path):
    """判斷是否為前端專案"""
    return (Path(project_path) / 'package.json').exists()


def _is_backend(project_path):
    """判斷是否為後端專案"""
    p = Path(project_path)
    return (p / 'requirements.txt').exists() or (p / 'backend' / 'requirements.txt').exists()


def _not_frontend(project_path):
    return not _is_frontend(project_path)


def _not_backend(project_path):
    return not _is_backend(project_path)


def _run_check(project_path):
    """執行架構文件檢查"""
    p = Path(project_path).resolve()
    project_name = p.name

    checks = {
        'CLAUDE.md': _check_file(p, 'CLAUDE.md'),
        'OpenSpec': ('OK' if (p / 'openspec').is_dir() else 'MISSING', None),
    }

    # Design System：前端專案才檢查
    if _is_frontend(p):
        ds_path = p / '.interface-design' / 'system.md'
        # 也檢查 frontend 子目錄
        ds_path_sub = p / 'frontend' / '.interface-design' / 'system.md'
        if ds_path.exists() or ds_path_sub.exists():
            checks['Design System'] = ('OK', None)
        else:
            checks['Design System'] = ('MISSING', None)
    else:
        checks['Design System'] = ('N/A', None)

    # Backend Standards：後端專案才檢查
    if _is_backend(p):
        bs_path = p / 'BACKEND-STANDARDS.md'
        bs_path_sub = p / 'backend' / 'BACKEND-STANDARDS.md'
        if bs_path.exists() or bs_path_sub.exists():
            checks['BACKEND-STANDARDS.md'] = ('OK', None)
        else:
            checks['BACKEND-STANDARDS.md'] = ('MISSING', None)
    else:
        checks['BACKEND-STANDARDS.md'] = ('N/A', None)

    return project_name, checks


def _run_diff(project_path):
    """比對 CLAUDE.md 記錄的目錄結構 vs 實際結構"""
    p = Path(project_path).resolve()
    claude_md = p / 'CLAUDE.md'

    if not claude_md.exists():
        return None, 'CLAUDE.md 不存在，無法比對'

    content = claude_md.read_text(encoding='utf-8')

    # 從 CLAUDE.md 萃取 code block 中的目錄結構
    import re
    tree_blocks = re.findall(r'```\n?((?:src|frontend|backend)/.*?)```', content, re.DOTALL)

    if not tree_blocks:
        return None, 'CLAUDE.md 中未找到目錄結構定義'

    # 解析文件中記錄的目錄
    documented_dirs = set()
    for block in tree_blocks:
        for line in block.strip().split('\n'):
            line = line.strip().rstrip('/')
            # 移除 tree 符號和註解
            for prefix in ['├── ', '│   ', '└── ', '    ']:
                line = line.replace(prefix, '')
            line = line.split('#')[0].strip().rstrip('/')
            if line and not line.startswith('...'):
                documented_dirs.add(line)

    # 比對實際目錄
    diffs = []
    src_dir = p / 'src'
    if src_dir.exists():
        actual_dirs = set()
        for item in src_dir.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                actual_dirs.add(item.name)

        for d in actual_dirs - documented_dirs:
            diffs.append(f'+ src/{d}/ (CLAUDE.md 未記錄)')
        for d in documented_dirs - actual_dirs:
            if d in [name for name in documented_dirs if '/' not in name]:
                if not (src_dir / d).exists():
                    diffs.append(f'- src/{d}/ (CLAUDE.md 記錄但已刪除)')

    return diffs, None


@click.group()
def architecture():
    """架構文件完整性檢查

    檢查專案是否有完整的架構文件：
    - CLAUDE.md: 專案概述與開發指引
    - .interface-design/system.md: 前端設計系統
    - BACKEND-STANDARDS.md: 後端開發規範
    - openspec/: 變更提案目錄

    使用範例：
      dash architecture check .
      dash architecture check --all
      dash architecture diff .
    """
    pass


@architecture.command()
@click.argument('project', type=click.Path(), default='.')
@click.option('--all', 'check_all', is_flag=True, help='檢查所有專案')
def check(project, check_all):
    """檢查架構文件完整性"""
    from rich.table import Table

    if check_all:
        projects = DEFAULT_PROJECTS
    else:
        projects = [project]

    table = Table(title='架構文件檢查')
    table.add_column('專案', style='cyan')
    table.add_column('CLAUDE.md')
    table.add_column('Design System')
    table.add_column('OpenSpec')
    table.add_column('Backend Standards')

    for p in projects:
        if not Path(p).exists():
            continue
        try:
            name, checks = _run_check(p)
            row = [name]
            for key in ['CLAUDE.md', 'Design System', 'OpenSpec', 'BACKEND-STANDARDS.md']:
                status, days = checks.get(key, ('?', None))
                if status == 'OK':
                    cell = '[green]OK[/green]'
                    if days and days > 0:
                        cell += f' [dim]({days}d)[/dim]'
                elif status == 'N/A':
                    cell = '[dim]N/A[/dim]'
                elif status == 'MISSING':
                    cell = '[red]MISSING[/red]'
                elif status.startswith('STALE'):
                    cell = f'[yellow]{status}[/yellow]'
                else:
                    cell = status
                row.append(cell)
            table.add_row(*row)
        except Exception as e:
            table.add_row(Path(p).name, f'[red]Error: {e}[/red]', '', '', '')

    console.print(table)


@architecture.command()
@click.argument('project', type=click.Path(), default='.')
def diff(project):
    """比對 CLAUDE.md 記錄 vs 實際目錄結構"""
    diffs, error = _run_diff(project)

    if error:
        console.print(f'[yellow]{error}[/yellow]')
        return

    if not diffs:
        console.print('[green]目錄結構與 CLAUDE.md 一致[/green]')
    else:
        console.print('[yellow]差異：[/yellow]')
        for d in diffs:
            if d.startswith('+'):
                console.print(f'  [green]{d}[/green]')
            elif d.startswith('-'):
                console.print(f'  [red]{d}[/red]')
            else:
                console.print(f'  [yellow]{d}[/yellow]')


def register(main):
    """註冊 architecture 指令"""
    main.add_command(architecture)
