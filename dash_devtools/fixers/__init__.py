"""
自動修復模組

修復器：
- MigrationFixer: HTML 標籤、事件處理器
- UxFixer: UI/UX 問題（下拉選單、按鈕 title）
"""

from pathlib import Path
from .migration_fixer import MigrationFixer
from .ux_fixer import UxFixer


def run_auto_fix(projects, fix_types=None):
    """執行所有專案的自動修復

    Args:
        projects: 專案路徑列表
        fix_types: 要執行的修復類型 ('migration', 'ux', 'all')
    """
    if fix_types is None:
        fix_types = 'all'

    results = []

    for project_path in projects:
        project = Path(project_path)
        project_name = project.name

        fixes = []

        # 執行遷移修復
        if fix_types in ('all', 'migration'):
            fixer = MigrationFixer(project)
            migration_fixes = fixer.fix_all()
            fixes.extend(migration_fixes)

        # 執行 UX 修復
        if fix_types in ('all', 'ux'):
            ux_fixer = UxFixer(project)
            ux_fixes = ux_fixer.fix_all()
            fixes.extend(ux_fixes)

        results.append({
            'project': project_name,
            'fixes': fixes
        })

    return results
