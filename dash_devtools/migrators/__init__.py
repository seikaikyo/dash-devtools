"""
遷移工具集
"""

from .shoelace_to_daisyui import ShoelaceToDaisyUIMigrator

__all__ = ['ShoelaceToDaisyUIMigrator', 'run_migration']


def run_migration(project, dry_run=False, from_framework='shoelace', to_framework='daisyui'):
    """執行遷移"""
    if from_framework == 'shoelace' and to_framework == 'daisyui':
        migrator = ShoelaceToDaisyUIMigrator(project, dry_run=dry_run)
        return migrator.run()
    else:
        return {'success': False, 'error': f'不支援的遷移: {from_framework} → {to_framework}'}
