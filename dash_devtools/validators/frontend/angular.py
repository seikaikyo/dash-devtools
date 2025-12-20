"""
Angular 專案驗證器

檢查項目：
1. PrimeNG 設定
2. 組件結構
3. Service 注入
4. 模組匯入
5. 表單雙向綁定
"""

import re
import json
from pathlib import Path


class AngularValidator:
    """Angular 專案驗證器"""

    name = 'angular'

    # 忽略目錄
    IGNORE_DIRS = [
        'node_modules', '.git', 'dist', '.angular', '__pycache__'
    ]

    def __init__(self, project_path):
        self.project_path = Path(project_path)
        self.project_name = self.project_path.name
        self.src_path = self.project_path / 'src'
        self.result = {
            'name': self.name,
            'passed': True,
            'errors': [],
            'warnings': [],
            'checks': {}
        }

    def run(self):
        """執行所有驗證"""
        if not self.project_path.exists():
            self.result['passed'] = False
            self.result['errors'].append(f'專案路徑不存在: {self.project_path}')
            return self.result

        self.check_primeng_config()
        self.check_component_structure()
        self.check_imports()
        self.check_form_bindings()
        self.check_service_injection()

        return self.result

    def check_primeng_config(self):
        """檢查 PrimeNG 設定"""
        app_config = self.src_path / 'app' / 'app.config.ts'

        if not app_config.exists():
            self.result['checks']['primeng_config'] = {'skipped': '無 app.config.ts'}
            return

        try:
            content = app_config.read_text(encoding='utf-8')
            has_provider = 'providePrimeNG' in content
            has_theme = '@primeng/themes' in content

            self.result['checks']['primeng_config'] = {
                'has_provider': has_provider,
                'has_theme': has_theme
            }

            if not has_provider:
                self.result['warnings'].append('缺少 providePrimeNG 設定')
            if not has_theme:
                self.result['warnings'].append('缺少 PrimeNG 主題設定')
        except Exception:
            pass

    def check_component_structure(self):
        """檢查組件結構"""
        issues = []

        for file_path in self.src_path.rglob('*.component.ts'):
            if self._should_skip(file_path):
                continue
            try:
                content = file_path.read_text(encoding='utf-8')
                rel_path = str(file_path.relative_to(self.project_path))
                line_count = len(content.splitlines())

                # 檢查組件大小
                if line_count > 500:
                    issues.append({
                        'file': rel_path,
                        'issue': f'組件過大 ({line_count} 行)',
                        'severity': 'warning'
                    })

                # 檢查是否有 standalone
                if 'standalone: true' not in content and '@Component' in content:
                    issues.append({
                        'file': rel_path,
                        'issue': '建議使用 standalone component',
                        'severity': 'info'
                    })

            except Exception:
                pass

        self.result['checks']['component_structure'] = {
            'count': len(issues),
            'issues': issues
        }

        for issue in issues:
            if issue['severity'] == 'warning':
                self.result['warnings'].append(f"{issue['file']}: {issue['issue']}")

    def check_imports(self):
        """檢查模組匯入"""
        issues = []

        # 檢查是否有遺漏的 PrimeNG 模組匯入
        primeng_components = {
            'p-table': 'TableModule',
            'p-button': 'ButtonModule',
            'p-dialog': 'DialogModule',
            'p-drawer': 'DrawerModule',
            'p-inputtext': 'InputTextModule',
            'p-select': 'SelectModule',
            'p-datepicker': 'DatePickerModule',
            'p-inputnumber': 'InputNumberModule',
            'p-tag': 'TagModule',
            'p-tabs': 'TabsModule',
            'pInputText': 'InputTextModule',
        }

        for file_path in self.src_path.rglob('*.component.ts'):
            if self._should_skip(file_path):
                continue
            try:
                content = file_path.read_text(encoding='utf-8')
                rel_path = str(file_path.relative_to(self.project_path))

                for component, module in primeng_components.items():
                    if component in content and module not in content:
                        issues.append({
                            'file': rel_path,
                            'component': component,
                            'missing_module': module
                        })
            except Exception:
                pass

        self.result['checks']['imports'] = {
            'count': len(issues),
            'issues': issues
        }

        if issues:
            for issue in issues[:5]:
                self.result['errors'].append(
                    f"{issue['file']}: 使用 {issue['component']} 但未匯入 {issue['missing_module']}"
                )
            self.result['passed'] = False

    def check_form_bindings(self):
        """檢查表單綁定"""
        issues = []

        for file_path in self.src_path.rglob('*.html'):
            if self._should_skip(file_path):
                continue
            try:
                content = file_path.read_text(encoding='utf-8')
                rel_path = str(file_path.relative_to(self.project_path))

                # 檢查是否有未綁定的 input
                # 找出 <input> 但沒有 [(ngModel)] 或 [formControl]
                inputs = re.findall(r'<input[^>]*>', content)
                for inp in inputs:
                    if 'ngModel' not in inp and 'formControl' not in inp and 'type="submit"' not in inp:
                        # 可能是有意為之，只記錄警告
                        pass

                # 檢查 PrimeNG 組件綁定
                primeng_inputs = re.findall(r'<p-(?:inputtext|inputnumber|select|datepicker)[^>]*>', content)
                for pinput in primeng_inputs:
                    if 'ngModel' not in pinput and 'formControl' not in pinput:
                        issues.append({
                            'file': rel_path,
                            'issue': 'PrimeNG 輸入元件缺少資料綁定'
                        })

            except Exception:
                pass

        self.result['checks']['form_bindings'] = {
            'count': len(issues),
            'issues': issues
        }

        if issues:
            for issue in issues[:3]:
                self.result['warnings'].append(f"{issue['file']}: {issue['issue']}")

    def check_service_injection(self):
        """檢查 Service 注入"""
        issues = []

        for file_path in self.src_path.rglob('*.service.ts'):
            if self._should_skip(file_path):
                continue
            try:
                content = file_path.read_text(encoding='utf-8')
                rel_path = str(file_path.relative_to(self.project_path))

                # 檢查是否有 @Injectable
                if 'class ' in content and '@Injectable' not in content:
                    issues.append({
                        'file': rel_path,
                        'issue': '缺少 @Injectable 裝飾器'
                    })

                # 檢查是否使用 providedIn: 'root'
                if '@Injectable' in content and "providedIn: 'root'" not in content:
                    issues.append({
                        'file': rel_path,
                        'issue': "建議使用 providedIn: 'root'"
                    })

            except Exception:
                pass

        self.result['checks']['service_injection'] = {
            'count': len(issues),
            'issues': issues
        }

        for issue in issues:
            self.result['warnings'].append(f"{issue['file']}: {issue['issue']}")

    def _should_skip(self, file_path):
        """檢查是否應該跳過該檔案"""
        return any(ignore in str(file_path) for ignore in self.IGNORE_DIRS)
