"""
驗證工具集

- migration: UI 遷移驗證
- security: 安全性檢查
- performance: 效能檢查
- code_quality: 程式碼品質
"""

from .migration import MigrationValidator
from .security import SecurityValidator
from .performance import PerformanceValidator
from .code_quality import CodeQualityValidator

__all__ = [
    'MigrationValidator',
    'SecurityValidator',
    'PerformanceValidator',
    'CodeQualityValidator',
    'run_validation',
]


def run_validation(projects, checks='all', output=None):
    """執行驗證"""
    results = []

    for project in projects:
        result = {
            'project': project.split('/')[-1] if '/' in project else project,
            'path': project,
            'passed': True,
            'errors': [],
            'warnings': [],
            'checks': {}
        }

        validators = []
        if checks in ('all', 'migration'):
            validators.append(MigrationValidator(project))
        if checks in ('all', 'security'):
            validators.append(SecurityValidator(project))
        if checks in ('all', 'performance'):
            validators.append(PerformanceValidator(project))
        if checks in ('all', 'code_quality'):
            validators.append(CodeQualityValidator(project))

        for validator in validators:
            check_result = validator.run()
            result['checks'][validator.name] = check_result
            if not check_result.get('passed', True):
                result['passed'] = False
            result['errors'].extend(check_result.get('errors', []))
            result['warnings'].extend(check_result.get('warnings', []))

        results.append(result)

    return results
