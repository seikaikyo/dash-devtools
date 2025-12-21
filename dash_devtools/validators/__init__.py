"""
驗證工具集

新架構：依專案類型自動選擇驗證器

- common: 通用驗證（安全、品質）- 所有專案
- frontend/vite: Vite + Shoelace
- frontend/angular: Angular + PrimeNG
- backend/nodejs: Node.js API
- backend/python: Python 後端/AI
"""

from pathlib import Path
from .detector import ProjectDetector
from .common import SecurityValidator, QualityValidator
from .frontend import ViteValidator, AngularValidator
from .backend import NodejsValidator, PythonValidator

# 保留舊的匯入（向後相容）
from .migration import MigrationValidator
from .security import SecurityValidator as LegacySecurityValidator
from .performance import PerformanceValidator
from .code_quality import CodeQualityValidator

__all__ = [
    # 新架構
    'ProjectDetector',
    'SecurityValidator',
    'QualityValidator',
    'ViteValidator',
    'AngularValidator',
    'NodejsValidator',
    'PythonValidator',
    # 舊架構（向後相容）
    'MigrationValidator',
    'PerformanceValidator',
    'CodeQualityValidator',
    # 函數
    'run_validation',
    'run_smart_validation',
]


def run_smart_validation(projects, output=None):
    """智慧驗證：自動偵測專案類型並執行對應驗證器"""
    results = []

    for project in projects:
        project_path = Path(project)
        project_name = project_path.name

        result = {
            'project': project_name,
            'path': str(project_path),
            'passed': True,
            'errors': [],
            'warnings': [],
            'checks': {},
            'project_type': None
        }

        # 偵測專案類型
        detector = ProjectDetector(project_path)
        project_info = detector.detect()
        result['project_type'] = project_info

        validators = []

        # 通用驗證器（所有專案都跑）
        validators.append(SecurityValidator(project_path))
        validators.append(QualityValidator(project_path))

        # 前端驗證器
        if project_info['frontend'] == 'angular':
            validators.append(AngularValidator(project_path))
        elif project_info['frontend'] in ['vite', 'vanilla']:
            validators.append(ViteValidator(project_path))

        # 後端驗證器
        if project_info['backend'] == 'nodejs':
            validators.append(NodejsValidator(project_path))
        elif project_info['backend'] == 'python':
            validators.append(PythonValidator(project_path))

        # 執行驗證
        for validator in validators:
            try:
                check_result = validator.run()
                result['checks'][validator.name] = check_result
                if not check_result.get('passed', True):
                    result['passed'] = False
                result['errors'].extend(check_result.get('errors', []))
                result['warnings'].extend(check_result.get('warnings', []))
            except Exception as e:
                result['checks'][validator.name] = {
                    'error': str(e),
                    'passed': False
                }
                result['errors'].append(f'{validator.name} 驗證器錯誤: {e}')

        results.append(result)

    return results


def run_validation(projects, checks='all', output=None):
    """執行驗證（向後相容模式）

    如果 checks='smart'，使用新的智慧驗證
    否則使用舊的驗證邏輯
    """
    if checks == 'smart':
        return run_smart_validation(projects, output)

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
            validators.append(LegacySecurityValidator(project))
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
