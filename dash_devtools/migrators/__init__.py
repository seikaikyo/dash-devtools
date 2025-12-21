"""
遷移工具集

注意：Shoelace → DaisyUI 遷移器已棄用
目前維持 Shoelace 作為非 Angular 專案的標準 UI 框架
"""

__all__ = ['run_migration']


def run_migration(project, dry_run=False, from_framework='shoelace', to_framework='daisyui'):
    """執行遷移

    注意：此功能已暫停使用
    - Shoelace 維持為標準 UI 框架
    - 遷移需要完整理解設計邏輯後才能進行
    """
    return {
        'success': False,
        'error': '遷移功能已暫停。UI 框架遷移需要完整理解設計邏輯後手動進行。'
    }
