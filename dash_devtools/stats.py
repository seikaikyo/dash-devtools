"""
程式碼統計儀表板

視覺化專案統計資訊：
- 語言分佈
- 檔案數量與行數
- 複雜度指標
- 技術債務追蹤
"""

import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Tuple
from collections import defaultdict
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

console = Console()


# 語言設定
LANGUAGE_CONFIG = {
    '.py': {'name': 'Python', 'color': 'yellow', 'icon': ''},
    '.js': {'name': 'JavaScript', 'color': 'yellow', 'icon': ''},
    '.ts': {'name': 'TypeScript', 'color': 'blue', 'icon': ''},
    '.tsx': {'name': 'TSX', 'color': 'cyan', 'icon': ''},
    '.jsx': {'name': 'JSX', 'color': 'cyan', 'icon': ''},
    '.html': {'name': 'HTML', 'color': 'orange1', 'icon': ''},
    '.css': {'name': 'CSS', 'color': 'magenta', 'icon': ''},
    '.scss': {'name': 'SCSS', 'color': 'magenta', 'icon': ''},
    '.json': {'name': 'JSON', 'color': 'green', 'icon': ''},
    '.md': {'name': 'Markdown', 'color': 'white', 'icon': ''},
    '.vue': {'name': 'Vue', 'color': 'green', 'icon': ''},
    '.svelte': {'name': 'Svelte', 'color': 'orange1', 'icon': ''},
}

# 忽略的目錄
IGNORE_DIRS = {
    'node_modules', '.git', 'dist', 'build', '.next', '__pycache__',
    'venv', '.venv', '.angular', '.cache', 'coverage', '.nuxt',
    '.output', '.turbo', 'vendor'
}


@dataclass
class FileStats:
    """單一檔案統計"""
    path: str
    extension: str
    lines: int
    code_lines: int
    comment_lines: int
    blank_lines: int
    size_bytes: int


@dataclass
class LanguageStats:
    """語言統計"""
    name: str
    files: int = 0
    lines: int = 0
    code_lines: int = 0
    size_bytes: int = 0


@dataclass
class ProjectStats:
    """專案統計總覽"""
    name: str
    total_files: int = 0
    total_lines: int = 0
    total_code_lines: int = 0
    total_size_bytes: int = 0
    languages: Dict[str, LanguageStats] = field(default_factory=dict)
    largest_files: List[Tuple[str, int]] = field(default_factory=list)
    complexity_issues: List[str] = field(default_factory=list)


class StatsCollector:
    """程式碼統計收集器"""

    def __init__(self, project_path: str):
        self.project_path = Path(project_path)
        self.project_name = self.project_path.name

    def collect(self) -> ProjectStats:
        """收集專案統計"""
        stats = ProjectStats(name=self.project_name)
        file_stats_list = []

        for file_path in self.project_path.rglob('*'):
            # 跳過目錄
            if file_path.is_dir():
                continue

            # 跳過忽略的目錄
            if any(ignore in file_path.parts for ignore in IGNORE_DIRS):
                continue

            # 只處理已知的語言
            ext = file_path.suffix.lower()
            if ext not in LANGUAGE_CONFIG:
                continue

            try:
                file_stat = self._analyze_file(file_path)
                file_stats_list.append(file_stat)

                # 更新語言統計
                lang_name = LANGUAGE_CONFIG[ext]['name']
                if lang_name not in stats.languages:
                    stats.languages[lang_name] = LanguageStats(name=lang_name)

                lang_stats = stats.languages[lang_name]
                lang_stats.files += 1
                lang_stats.lines += file_stat.lines
                lang_stats.code_lines += file_stat.code_lines
                lang_stats.size_bytes += file_stat.size_bytes

                # 更新總計
                stats.total_files += 1
                stats.total_lines += file_stat.lines
                stats.total_code_lines += file_stat.code_lines
                stats.total_size_bytes += file_stat.size_bytes

                # 檢查複雜度問題
                if file_stat.lines > 500:
                    stats.complexity_issues.append(
                        f'{file_path.name}: {file_stat.lines} 行 (建議拆分)'
                    )

            except Exception:
                pass

        # 找出最大的檔案
        file_stats_list.sort(key=lambda x: x.lines, reverse=True)
        stats.largest_files = [
            (fs.path, fs.lines) for fs in file_stats_list[:10]
        ]

        return stats

    def _analyze_file(self, file_path: Path) -> FileStats:
        """分析單一檔案"""
        content = file_path.read_text(encoding='utf-8', errors='ignore')
        lines = content.splitlines()

        code_lines = 0
        comment_lines = 0
        blank_lines = 0

        ext = file_path.suffix.lower()
        in_block_comment = False

        for line in lines:
            stripped = line.strip()

            if not stripped:
                blank_lines += 1
                continue

            # Python 風格註解
            if ext == '.py':
                if stripped.startswith('#'):
                    comment_lines += 1
                elif stripped.startswith('"""') or stripped.startswith("'''"):
                    in_block_comment = not in_block_comment
                    comment_lines += 1
                elif in_block_comment:
                    comment_lines += 1
                else:
                    code_lines += 1

            # JS/TS 風格註解
            elif ext in ['.js', '.ts', '.jsx', '.tsx', '.css', '.scss']:
                if stripped.startswith('//'):
                    comment_lines += 1
                elif stripped.startswith('/*'):
                    in_block_comment = True
                    comment_lines += 1
                elif stripped.endswith('*/'):
                    in_block_comment = False
                    comment_lines += 1
                elif in_block_comment:
                    comment_lines += 1
                else:
                    code_lines += 1

            # HTML 風格
            elif ext == '.html':
                if '<!--' in stripped:
                    comment_lines += 1
                else:
                    code_lines += 1

            else:
                code_lines += 1

        return FileStats(
            path=str(file_path.relative_to(self.project_path)),
            extension=ext,
            lines=len(lines),
            code_lines=code_lines,
            comment_lines=comment_lines,
            blank_lines=blank_lines,
            size_bytes=file_path.stat().st_size
        )


def render_stats_report(stats: ProjectStats):
    """渲染統計報告"""

    # 標題
    title = Text()
    title.append(f"\n  {stats.name} ", style="bold white")
    title.append("程式碼統計\n", style="dim")
    console.print(Panel(title, border_style="cyan"))

    # 總覽
    size_kb = stats.total_size_bytes / 1024
    size_display = f"{size_kb:.1f} KB" if size_kb < 1024 else f"{size_kb/1024:.1f} MB"

    console.print(f"  [dim]檔案數:[/dim] [cyan]{stats.total_files:,}[/cyan]")
    console.print(f"  [dim]總行數:[/dim] [cyan]{stats.total_lines:,}[/cyan]")
    console.print(f"  [dim]程式碼行數:[/dim] [cyan]{stats.total_code_lines:,}[/cyan]")
    console.print(f"  [dim]大小:[/dim] [cyan]{size_display}[/cyan]")
    console.print()

    # 語言分佈 - 水平條狀圖
    console.print("  [bold]語言分佈[/bold]")
    console.print()

    if stats.languages:
        max_lines = max(lang.lines for lang in stats.languages.values())
        bar_width = 35

        # 按行數排序
        sorted_langs = sorted(
            stats.languages.values(),
            key=lambda x: x.lines,
            reverse=True
        )

        for lang in sorted_langs[:8]:  # 最多顯示 8 種語言
            # 找出對應的顏色
            color = 'white'
            for ext, config in LANGUAGE_CONFIG.items():
                if config['name'] == lang.name:
                    color = config['color']
                    break

            filled = int((lang.lines / max_lines) * bar_width) if max_lines > 0 else 0
            percentage = (lang.lines / stats.total_lines * 100) if stats.total_lines > 0 else 0

            bar = Text()
            bar.append(f"  {lang.name:12} ", style="white")
            bar.append("█" * filled, style=color)
            bar.append("░" * (bar_width - filled), style="dim")
            bar.append(f" {percentage:5.1f}%", style=color)
            bar.append(f" ({lang.lines:,} 行)", style="dim")

            console.print(bar)

    console.print()

    # 最大的檔案
    if stats.largest_files:
        console.print("  [bold]最大檔案 Top 5[/bold]")
        console.print()

        for i, (path, lines) in enumerate(stats.largest_files[:5], 1):
            color = 'red' if lines > 500 else 'yellow' if lines > 300 else 'green'
            console.print(f"    {i}. [{color}]{lines:4} 行[/{color}] {path}")

    console.print()

    # 複雜度警告
    if stats.complexity_issues:
        console.print("  [bold yellow]複雜度警告[/bold yellow]")
        console.print()
        for issue in stats.complexity_issues[:5]:
            console.print(f"    [yellow]![/yellow] {issue}")
        console.print()

    return {
        'project': stats.name,
        'total_files': stats.total_files,
        'total_lines': stats.total_lines,
        'languages': {k: {'files': v.files, 'lines': v.lines} for k, v in stats.languages.items()},
        'complexity_issues': len(stats.complexity_issues)
    }


def run_stats(project_path: str) -> dict:
    """執行程式碼統計"""
    collector = StatsCollector(project_path)
    stats = collector.collect()
    return render_stats_report(stats)


def run_stats_all(projects: List[str]) -> dict:
    """多專案統計比較"""
    results = []

    # 標題
    console.print(Panel(
        Text("\n  專案統計比較\n", style="bold white"),
        border_style="cyan"
    ))

    # 建立比較表格
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("專案", style="white")
    table.add_column("檔案", justify="right")
    table.add_column("行數", justify="right")
    table.add_column("主要語言", justify="center")
    table.add_column("大小", justify="right")

    for project in projects:
        try:
            collector = StatsCollector(project)
            stats = collector.collect()

            # 找出主要語言
            main_lang = '-'
            if stats.languages:
                main_lang = max(stats.languages.values(), key=lambda x: x.lines).name

            size_kb = stats.total_size_bytes / 1024
            size_display = f"{size_kb:.0f} KB" if size_kb < 1024 else f"{size_kb/1024:.1f} MB"

            table.add_row(
                stats.name,
                f"{stats.total_files:,}",
                f"{stats.total_lines:,}",
                main_lang,
                size_display
            )

            results.append({
                'project': stats.name,
                'files': stats.total_files,
                'lines': stats.total_lines
            })

        except Exception as e:
            table.add_row(project.split('/')[-1], "-", "-", "-", f"[red]錯誤[/red]")

    console.print(table)

    return {'projects': results}
