"""
自動修復模組

修復器：
- MigrationFixer: HTML 標籤、事件處理器
- UxFixer: UI/UX 問題（下拉選單、按鈕 title、卡片邊框）
- VersionBumper: 版本號自動更新
"""

from pathlib import Path
from .migration_fixer import MigrationFixer
from .ux_fixer import UxFixer
from .version_bumper import bump_version_if_fixed


def run_auto_fix(projects, fix_types=None, bump_version=True):
    """執行所有專案的自動修復

    Args:
        projects: 專案路徑列表
        fix_types: 要執行的修復類型 ('migration', 'ux', 'all')
        bump_version: 是否自動更新版本號 (預設 True)
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

        # 如果有修復，自動更新版本號
        if fixes and bump_version:
            version_fixes = bump_version_if_fixed(project, fixes)
            fixes.extend(version_fixes)

        results.append({
            'project': project_name,
            'fixes': fixes
        })

    return results
