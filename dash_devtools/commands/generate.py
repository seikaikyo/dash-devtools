"""changelog, git-stats, bundle 指令

整合 gitchangelog, gitinspector, vite-bundle-visualizer。
"""

import click
import subprocess
import sys
from pathlib import Path
from datetime import datetime
from dash_devtools.cli import console


# === dash changelog ===

@click.command()
@click.argument('project', type=click.Path(exists=True), default='.')
@click.option('--output', '-o', type=click.Path(), help='輸出檔案路徑')
@click.option('--format', 'fmt', type=click.Choice(['markdown', 'rst']),
              default='markdown', help='輸出格式')
@click.option('--since', default=None, help='起始 tag 或 commit')
def changelog(project, output, fmt, since):
    """自動產生 CHANGELOG (git log 分析)

    從 git commit history 產生結構化的 CHANGELOG。
    支援 feat/fix/refactor/docs 等 conventional commit 格式。

    使用範例：
      dash changelog .
      dash changelog . -o CHANGELOG.md
      dash changelog . --since v1.0.0
    """
    project_path = Path(project).resolve()

    # 確認是 git repo
    if not (project_path / '.git').exists():
        console.print(f"[red]{project_path.name} 不是 git repository[/red]")
        raise SystemExit(1)

    console.print(f"[cyan]產生 CHANGELOG: {project_path.name}[/cyan]\n")

    # 取得 git log
    cmd = ['git', 'log', '--pretty=format:%H|%s|%an|%ai', '--no-merges']
    if since:
        cmd.append(f'{since}..HEAD')

    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(project_path))

    if result.returncode != 0:
        console.print(f"[red]git log 失敗: {result.stderr}[/red]")
        raise SystemExit(1)

    if not result.stdout.strip():
        console.print("[yellow]沒有 commit 記錄[/yellow]")
        return

    # 解析 commits
    categories = {
        'feat': [],
        'fix': [],
        'refactor': [],
        'docs': [],
        'test': [],
        'chore': [],
        'other': [],
    }

    for line in result.stdout.strip().split('\n'):
        parts = line.split('|', 3)
        if len(parts) < 4:
            continue
        hash_val, subject, author, date = parts
        short_hash = hash_val[:8]

        # 解析 conventional commit 類型
        categorized = False
        for cat_key in ['feat', 'fix', 'refactor', 'docs', 'test', 'chore']:
            if subject.lower().startswith(f'{cat_key}:') or subject.lower().startswith(f'{cat_key}('):
                # 移除前綴
                msg = subject.split(':', 1)[-1].strip() if ':' in subject else subject
                categories[cat_key].append({
                    'hash': short_hash,
                    'message': msg,
                    'author': author,
                    'date': date[:10],
                })
                categorized = True
                break

        if not categorized:
            categories['other'].append({
                'hash': short_hash,
                'message': subject,
                'author': author,
                'date': date[:10],
            })

    # 產生 changelog
    category_labels = {
        'feat': '新功能',
        'fix': '修復',
        'refactor': '重構',
        'docs': '文件',
        'test': '測試',
        'chore': '維護',
        'other': '其他',
    }

    lines = []
    today = datetime.now().strftime('%Y-%m-%d')
    lines.append(f"# Changelog\n")
    lines.append(f"產生時間: {today}\n")

    total = sum(len(v) for v in categories.values())
    lines.append(f"共 {total} 個 commits\n")

    for cat_key, label in category_labels.items():
        items = categories[cat_key]
        if not items:
            continue
        lines.append(f"\n## {label}\n")
        for item in items:
            lines.append(f"- {item['message']} (`{item['hash']}`) - {item['author']}")

    content = '\n'.join(lines) + '\n'

    if output:
        output_path = Path(output)
        output_path.write_text(content, encoding='utf-8')
        console.print(f"[green]CHANGELOG 已寫入: {output_path}[/green]")
    else:
        console.print(content)

    # 統計
    from rich.table import Table
    table = Table(title="Commit 分類統計")
    table.add_column("類型", style="cyan")
    table.add_column("數量", justify="right")

    for cat_key, label in category_labels.items():
        count = len(categories[cat_key])
        if count > 0:
            table.add_row(label, str(count))

    console.print(table)


# === dash git-stats ===

@click.command('git-stats')
@click.argument('project', type=click.Path(exists=True), default='.')
@click.option('--since', default=None, help='起始日期 (YYYY-MM-DD)')
@click.option('--top', type=int, default=10, help='顯示前 N 位貢獻者')
def git_stats(project, since, top):
    """Git 貢獻者統計

    分析 git 歷史，顯示貢獻者統計、程式碼變動、活躍時段等。

    使用範例：
      dash git-stats .
      dash git-stats . --since 2026-01-01
      dash git-stats . --top 5
    """
    project_path = Path(project).resolve()

    if not (project_path / '.git').exists():
        console.print(f"[red]{project_path.name} 不是 git repository[/red]")
        raise SystemExit(1)

    console.print(f"[cyan]Git 統計: {project_path.name}[/cyan]\n")

    # 貢獻者統計
    cmd = ['git', 'shortlog', '-sne', 'HEAD']
    if since:
        cmd.extend(['--since', since])

    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(project_path))

    if not result.stdout.strip():
        console.print("[yellow]沒有 commit 記錄[/yellow]")
        return

    from rich.table import Table

    # 解析貢獻者
    contributors = []
    for line in result.stdout.strip().split('\n'):
        line = line.strip()
        if not line:
            continue
        parts = line.split('\t', 1)
        if len(parts) == 2:
            count = int(parts[0].strip())
            name = parts[1].strip()
            contributors.append({'name': name, 'commits': count})

    contributors.sort(key=lambda x: x['commits'], reverse=True)
    display = contributors[:top]
    total_commits = sum(c['commits'] for c in contributors)

    table = Table(title=f"貢獻者排行 (共 {total_commits} commits)")
    table.add_column("#", justify="right", style="dim")
    table.add_column("貢獻者", style="cyan")
    table.add_column("Commits", justify="right")
    table.add_column("占比", justify="right")

    for i, c in enumerate(display, 1):
        pct = c['commits'] / total_commits * 100
        table.add_row(str(i), c['name'], str(c['commits']), f"{pct:.1f}%")

    console.print(table)

    # 最近 30 天活動
    cmd = ['git', 'log', '--pretty=format:%ai', '--since=30 days ago']
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(project_path))

    if result.stdout.strip():
        dates = {}
        for line in result.stdout.strip().split('\n'):
            date = line[:10]
            dates[date] = dates.get(date, 0) + 1

        if dates:
            console.print(f"\n[cyan]最近 30 天活動[/cyan]")
            console.print(f"  活躍天數: {len(dates)}")
            console.print(f"  總 commits: {sum(dates.values())}")
            if dates:
                max_date = max(dates, key=dates.get)
                console.print(f"  最活躍日: {max_date} ({dates[max_date]} commits)")

    # 檔案類型統計
    cmd = ['git', 'log', '--pretty=format:', '--name-only', '-50']
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(project_path))

    if result.stdout.strip():
        from collections import Counter
        extensions = Counter()
        for line in result.stdout.strip().split('\n'):
            line = line.strip()
            if not line:
                continue
            ext = Path(line).suffix or '(none)'
            extensions[ext] += 1

        if extensions:
            console.print(f"\n[cyan]近期修改檔案類型 (最近 50 commits)[/cyan]")
            ext_table = Table()
            ext_table.add_column("副檔名", style="cyan")
            ext_table.add_column("次數", justify="right")

            for ext, count in extensions.most_common(10):
                ext_table.add_row(ext, str(count))
            console.print(ext_table)


# === dash bundle ===

@click.command()
@click.argument('project', type=click.Path(exists=True), default='.')
@click.option('--open', 'open_browser', is_flag=True, help='自動開啟分析報告')
@click.option('--template', type=click.Choice(['treemap', 'sunburst', 'network']),
              default='treemap', help='圖表類型')
def bundle(project, open_browser, template):
    """Vite bundle 分析 (vite-bundle-visualizer)

    分析 Vite 專案的 bundle 大小和組成。
    需要 Node.js 環境，使用 npx 執行。

    使用範例：
      dash bundle .
      dash bundle . --open
      dash bundle . --template sunburst
    """
    project_path = Path(project).resolve()

    # 檢查是否是 Vite 專案
    has_vite = (project_path / 'vite.config.ts').exists() or \
               (project_path / 'vite.config.js').exists()

    if not has_vite:
        console.print(f"[red]{project_path.name} 不是 Vite 專案 (找不到 vite.config.ts/js)[/red]")
        raise SystemExit(1)

    console.print(f"[cyan]Vite bundle 分析: {project_path.name}[/cyan]\n")

    # 檢查 npx
    npx_check = subprocess.run(['which', 'npx'], capture_output=True)
    if npx_check.returncode != 0:
        console.print("[red]npx 未安裝，需要 Node.js 環境[/red]")
        raise SystemExit(1)

    cmd = ['npx', '--yes', 'vite-bundle-visualizer', '--template', template]
    if not open_browser:
        cmd.append('--no-open')

    console.print("[dim]執行 vite-bundle-visualizer (可能需要先 build)...[/dim]")
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(project_path))

    if result.stdout:
        console.print(result.stdout)
    if result.stderr:
        # 過濾 npm 噪音
        for line in result.stderr.strip().split('\n'):
            if line.strip() and 'npm warn' not in line.lower():
                console.print(f"  {line}")

    if result.returncode == 0:
        # 找到產生的報告檔案
        report_files = list(project_path.glob('stats.html')) + \
                       list(project_path.glob('stats-*.html'))
        if report_files:
            console.print(f"\n[green]分析報告: {report_files[0]}[/green]")
        else:
            console.print("\n[green]分析完成[/green]")

        # 順便顯示 dist 大小
        dist_path = project_path / 'dist'
        if dist_path.exists():
            total_size = sum(f.stat().st_size for f in dist_path.rglob('*') if f.is_file())
            console.print(f"\n[cyan]dist 目錄大小: {_format_size(total_size)}[/cyan]")

            # JS/CSS 各自大小
            js_size = sum(f.stat().st_size for f in dist_path.rglob('*.js') if f.is_file())
            css_size = sum(f.stat().st_size for f in dist_path.rglob('*.css') if f.is_file())
            if js_size:
                console.print(f"  JavaScript: {_format_size(js_size)}")
            if css_size:
                console.print(f"  CSS: {_format_size(css_size)}")
    else:
        console.print(f"\n[red]分析失敗 (exit code: {result.returncode})[/red]")
        raise SystemExit(result.returncode)


def _format_size(size_bytes):
    """格式化檔案大小"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def register(main):
    main.add_command(changelog)
    main.add_command(git_stats)
    main.add_command(bundle)
