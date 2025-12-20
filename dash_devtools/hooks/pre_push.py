"""
Pre-push 檢查
"""

from .pre_commit import run_pre_commit_check, SENSITIVE_PATTERNS
import re
from pathlib import Path


def run_pre_push_check(project_path):
    """執行 pre-push 檢查 (掃描整個專案)"""
    project = Path(project_path)
    issues = []

    # 忽略的目錄和檔案
    ignore_dirs = [
        'node_modules', '.git', 'dist', 'build', '.next', '__pycache__',
        'venv', '.venv', '.angular', '.cache', 'coverage'
    ]
    ignore_files = ['.env.example', '.env.sample', '.env.template']

    # 讀取 .gitignore 檔案
    gitignore_patterns = []
    gitignore_file = project / '.gitignore'
    if gitignore_file.exists():
        try:
            for line in gitignore_file.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith('#'):
                    gitignore_patterns.append(line)
        except Exception:
            pass

    def is_gitignored(file_path):
        """檢查檔案是否在 .gitignore 中"""
        rel_path = str(file_path.relative_to(project))
        file_name = file_path.name
        for pattern in gitignore_patterns:
            # 簡單匹配：完全匹配或 pattern 在路徑中
            if pattern == file_name or pattern == rel_path:
                return True
            if pattern.startswith('*.') and file_name.endswith(pattern[1:]):
                return True
            if pattern.endswith('/') and pattern[:-1] in rel_path.split('/'):
                return True
            if pattern in rel_path:
                return True
        return False

    # 掃描所有檔案（不含 .env，因為應該都在 .gitignore）
    extensions = ['*.js', '*.ts', '*.jsx', '*.tsx', '*.py', '*.json', '*.yaml', '*.yml']

    for ext in extensions:
        for file_path in project.rglob(ext):
            # 跳過忽略的目錄
            if any(ignore in str(file_path) for ignore in ignore_dirs):
                continue
            # 跳過範例檔案
            if file_path.name in ignore_files:
                continue
            # 跳過 .gitignore 中的檔案
            if is_gitignored(file_path):
                continue

            try:
                content = file_path.read_text(encoding='utf-8')
                for pattern, desc in SENSITIVE_PATTERNS:
                    matches = re.findall(pattern, content)
                    if matches:
                        issues.append({
                            'file': str(file_path.relative_to(project)),
                            'type': desc,
                            'count': len(matches)
                        })
            except Exception:
                pass

    return {
        'passed': len(issues) == 0,
        'issues': issues
    }
