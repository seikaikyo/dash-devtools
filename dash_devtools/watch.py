"""
即時監控模式

監控檔案變更並自動執行驗證：
- 檔案儲存時自動驗證
- 即時顯示問題
- 可選自動修復
"""

import time
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, Set, Optional
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.layout import Layout

console = Console()

# 監控的檔案類型
WATCH_EXTENSIONS = {'.js', '.ts', '.jsx', '.tsx', '.py', '.html', '.css', '.scss', '.vue'}

# 忽略的目錄
IGNORE_DIRS = {
    'node_modules', '.git', 'dist', 'build', '.next', '__pycache__',
    'venv', '.venv', '.angular', '.cache', 'coverage'
}


class FileWatcher:
    """檔案監控器"""

    def __init__(self, project_path: str, auto_fix: bool = False):
        self.project_path = Path(project_path)
        self.project_name = self.project_path.name
        self.auto_fix = auto_fix
        self.file_hashes: Dict[str, str] = {}
        self.change_log: list = []
        self.error_count = 0
        self.warning_count = 0
        self.fix_count = 0
        self.start_time = datetime.now()

    def _get_file_hash(self, file_path: Path) -> Optional[str]:
        """計算檔案 hash"""
        try:
            content = file_path.read_bytes()
            return hashlib.md5(content).hexdigest()
        except Exception:
            return None

    def _scan_files(self) -> Dict[str, str]:
        """掃描所有監控的檔案"""
        files = {}
        for file_path in self.project_path.rglob('*'):
            if file_path.is_dir():
                continue

            # 跳過忽略的目錄
            if any(ignore in file_path.parts for ignore in IGNORE_DIRS):
                continue

            # 只監控特定類型
            if file_path.suffix.lower() not in WATCH_EXTENSIONS:
                continue

            file_hash = self._get_file_hash(file_path)
            if file_hash:
                rel_path = str(file_path.relative_to(self.project_path))
                files[rel_path] = file_hash

        return files

    def _check_changes(self) -> Set[str]:
        """檢查檔案變更"""
        current_files = self._scan_files()
        changed_files = set()

        # 檢查修改和新增的檔案
        for path, hash_value in current_files.items():
            if path not in self.file_hashes:
                changed_files.add(path)
                self._log_change(path, 'new')
            elif self.file_hashes[path] != hash_value:
                changed_files.add(path)
                self._log_change(path, 'modified')

        # 檢查刪除的檔案
        for path in self.file_hashes:
            if path not in current_files:
                self._log_change(path, 'deleted')

        self.file_hashes = current_files
        return changed_files

    def _log_change(self, path: str, change_type: str):
        """記錄變更"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        icons = {'new': '+', 'modified': '*', 'deleted': '-'}
        colors = {'new': 'green', 'modified': 'yellow', 'deleted': 'red'}

        self.change_log.append({
            'time': timestamp,
            'path': path,
            'type': change_type,
            'icon': icons[change_type],
            'color': colors[change_type]
        })

        # 只保留最近 20 筆
        if len(self.change_log) > 20:
            self.change_log = self.change_log[-20:]

    def _validate_file(self, file_path: str) -> dict:
        """驗證單一檔案"""
        full_path = self.project_path / file_path
        issues = []
        warnings = []
        fixes = []

        try:
            content = full_path.read_text(encoding='utf-8')
            lines = content.splitlines()

            # 檢查檔案行數
            if len(lines) > 500:
                warnings.append(f'檔案過長 ({len(lines)} 行)')

            # 檢查 console.log (JS/TS)
            if full_path.suffix in ['.js', '.ts', '.jsx', '.tsx']:
                for i, line in enumerate(lines, 1):
                    if 'console.log' in line and '//' not in line.split('console.log')[0]:
                        warnings.append(f'第 {i} 行: console.log 需移除')

            # 檢查 TODO/FIXME
            for i, line in enumerate(lines, 1):
                if 'TODO' in line or 'FIXME' in line:
                    warnings.append(f'第 {i} 行: 有待處理項目')

            # 檢查 Emoji（禁止在程式碼中使用）
            import re
            emoji_pattern = re.compile(
                "["
                "\U0001F600-\U0001F64F"
                "\U0001F300-\U0001F5FF"
                "\U0001F680-\U0001F6FF"
                "\U0001F1E0-\U0001F1FF"
                "]+",
                flags=re.UNICODE
            )
            for i, line in enumerate(lines, 1):
                if emoji_pattern.search(line):
                    issues.append(f'第 {i} 行: 程式碼中禁止使用 Emoji')

        except Exception as e:
            issues.append(f'讀取錯誤: {e}')

        return {
            'path': file_path,
            'issues': issues,
            'warnings': warnings,
            'fixes': fixes
        }

    def generate_display(self) -> Panel:
        """產生顯示畫面"""
        layout = Layout()

        # 標題
        elapsed = datetime.now() - self.start_time
        elapsed_str = f"{int(elapsed.total_seconds() // 60)}:{int(elapsed.total_seconds() % 60):02d}"

        header = Text()
        header.append(f"  {self.project_name}", style="bold cyan")
        header.append(f"  [監控中]", style="bold green")
        header.append(f"  {elapsed_str}", style="dim")
        if self.auto_fix:
            header.append("  [自動修復]", style="yellow")

        # 狀態列
        status = Text()
        status.append(f"\n  檔案: {len(self.file_hashes)}", style="dim")
        status.append(f"  |  錯誤: ", style="dim")
        status.append(f"{self.error_count}", style="red" if self.error_count else "green")
        status.append(f"  |  警告: ", style="dim")
        status.append(f"{self.warning_count}", style="yellow" if self.warning_count else "green")
        if self.fix_count:
            status.append(f"  |  已修復: ", style="dim")
            status.append(f"{self.fix_count}", style="cyan")

        # 變更日誌
        log_text = Text()
        log_text.append("\n  最近變更:\n", style="dim")

        if self.change_log:
            for entry in reversed(self.change_log[-8:]):
                log_text.append(f"    {entry['time']} ", style="dim")
                log_text.append(f"[{entry['icon']}] ", style=entry['color'])
                log_text.append(f"{entry['path']}\n", style="white")
        else:
            log_text.append("    等待檔案變更...\n", style="dim")

        # 說明
        footer = Text()
        footer.append("\n  按 Ctrl+C 停止監控", style="dim")

        content = Text()
        content.append_text(header)
        content.append_text(status)
        content.append_text(log_text)
        content.append_text(footer)

        return Panel(
            content,
            title="[bold]Dash Watch[/bold]",
            border_style="cyan",
            padding=(1, 2)
        )

    def run(self, interval: float = 1.0):
        """執行監控"""
        # 初始掃描
        self.file_hashes = self._scan_files()

        console.print(f"\n[cyan]開始監控 {self.project_name}...[/cyan]")
        console.print(f"[dim]監控 {len(self.file_hashes)} 個檔案[/dim]\n")

        try:
            with Live(self.generate_display(), refresh_per_second=2, console=console) as live:
                while True:
                    changed_files = self._check_changes()

                    # 驗證變更的檔案
                    for file_path in changed_files:
                        result = self._validate_file(file_path)

                        if result['issues']:
                            self.error_count += len(result['issues'])
                        if result['warnings']:
                            self.warning_count += len(result['warnings'])

                    # 更新顯示
                    live.update(self.generate_display())

                    time.sleep(interval)

        except KeyboardInterrupt:
            console.print("\n[yellow]監控已停止[/yellow]")

        return {
            'duration': str(datetime.now() - self.start_time),
            'files_watched': len(self.file_hashes),
            'changes': len(self.change_log),
            'errors': self.error_count,
            'warnings': self.warning_count
        }


def run_watch(project_path: str, auto_fix: bool = False, interval: float = 1.0) -> dict:
    """執行監控模式"""
    watcher = FileWatcher(project_path, auto_fix=auto_fix)
    return watcher.run(interval=interval)
