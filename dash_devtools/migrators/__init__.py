"""
遷移工具集

注意：UI 框架遷移功能已棄用
- Shoelace / DaisyUI 均已從標準技術棧移除
- 標準前端方案：Vite + Vue 3 + PrimeVue / Angular + PrimeNG
"""

__all__ = ['run_migration']


def run_migration(project, dry_run=False, from_framework=None, to_framework=None):
    """執行遷移

    注意：此功能已棄用。
    標準前端方案為 Vite + Vue 3 + PrimeVue 或 Angular + PrimeNG。
    """
    return {
        'success': False,
        'error': '遷移功能已棄用。標準前端方案為 Vite + Vue 3 + PrimeVue 或 Angular + PrimeNG。'
    }
