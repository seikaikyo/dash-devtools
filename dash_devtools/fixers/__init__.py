"""
自動修復模組
"""

from pathlib import Path
from .migration_fixer import MigrationFixer


def run_auto_fix(projects):
    """執行所有專案的自動修復"""
    results = []

    for project_path in projects:
        project = Path(project_path)
        project_name = project.name

        fixes = []

        # 執行遷移修復
        fixer = MigrationFixer(project)
        migration_fixes = fixer.fix_all()
        fixes.extend(migration_fixes)

        results.append({
            'project': project_name,
            'fixes': fixes
        })

    return results
