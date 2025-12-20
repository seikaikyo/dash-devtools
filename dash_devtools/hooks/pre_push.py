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
    ignore_files = ['.env.example', '.env.sample']

    # 掃描所有檔案
    extensions = ['*.js', '*.ts', '*.jsx', '*.tsx', '*.py', '*.json', '*.yaml', '*.yml', '*.env', '*.env.*']

    for ext in extensions:
        for file_path in project.rglob(ext):
            # 跳過忽略的目錄
            if any(ignore in str(file_path) for ignore in ignore_dirs):
                continue
            # 跳過範例檔案
            if file_path.name in ignore_files:
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
