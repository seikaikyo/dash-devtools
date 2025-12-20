"""
Git Hooks 整合

提供 pre-commit 和 pre-push 安全檢查
"""

from .pre_commit import run_pre_commit_check
from .pre_push import run_pre_push_check

__all__ = ['run_pre_commit_check', 'run_pre_push_check', 'install_hooks']


def install_hooks(project_path):
    """安裝 git hooks 到專案"""
    from pathlib import Path
    import stat

    hooks_dir = Path(project_path) / '.git' / 'hooks'
    if not hooks_dir.exists():
        return {'success': False, 'error': '.git/hooks 目錄不存在'}

    # Pre-commit hook
    pre_commit = hooks_dir / 'pre-commit'
    pre_commit.write_text('''#!/bin/bash
# DashAI DevTools Pre-commit Hook
echo "🔍 掃描機敏資料..."
dash scan "$(git rev-parse --show-toplevel)"
''', encoding='utf-8')
    pre_commit.chmod(pre_commit.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    # Pre-push hook
    pre_push = hooks_dir / 'pre-push'
    pre_push.write_text('''#!/bin/bash
# DashAI DevTools Pre-push Hook
echo "🔍 掃描機敏資料..."
dash scan "$(git rev-parse --show-toplevel)"
if [ $? -ne 0 ]; then
    echo "❌ 安全檢查失敗，推送已取消"
    exit 1
fi
echo "✓ 安全檢查通過"
''', encoding='utf-8')
    pre_push.chmod(pre_push.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    return {'success': True}
