"""
UI 遷移驗證器

檢查項目：
1. Shoelace 元件殘留 (<sl-*>)
2. 重複 class 屬性
3. Shoelace CSS 變數 (--sl-*)
4. Tailwind 設定完整性
5. CSS Bundle 大小
"""

import re
import json
import subprocess
from pathlib import Path
from datetime import datetime


class MigrationValidator:
    """UI 遷移驗證器"""

    name = 'migration'

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

        self.check_shoelace_remnants()
        self.check_duplicate_classes()
        self.check_css_variables()
        self.check_tailwind_config()
        self.check_package_json()
        self.check_incomplete_html_tags()
        self.check_empty_buttons()
        self.check_empty_event_handlers()

        return self.result

    def check_shoelace_remnants(self):
        """檢查 Shoelace 元件殘留"""
        if not self.src_path.exists():
            return

        patterns = [
            (r'<sl-[a-z-]+', 'Shoelace 標籤'),
        ]

        total_count = 0
        file_issues = {}

        for pattern, desc in patterns:
            for file_path in self.src_path.rglob('*.js'):
                try:
                    content = file_path.read_text(encoding='utf-8')
                    matches = re.findall(pattern, content)
                    if matches:
                        rel_path = str(file_path.relative_to(self.project_path))
                        if rel_path not in file_issues:
                            file_issues[rel_path] = 0
                        file_issues[rel_path] += len(matches)
                        total_count += len(matches)
                except Exception:
                    pass

        self.result['checks']['shoelace_remnants'] = {
            'count': total_count,
            'files': file_issues
        }

        if total_count > 0:
            self.result['passed'] = False
            self.result['errors'].append(f'Shoelace 殘留: {total_count} 個')

    def check_duplicate_classes(self):
        """檢查重複 class 屬性"""
        if not self.src_path.exists():
            return

        pattern = r'class="[^"]*"\s+class="'
        total_count = 0
        file_issues = {}

        for file_path in self.src_path.rglob('*.js'):
            try:
                content = file_path.read_text(encoding='utf-8')
                matches = re.findall(pattern, content)
                if matches:
                    rel_path = str(file_path.relative_to(self.project_path))
                    file_issues[rel_path] = len(matches)
                    total_count += len(matches)
            except Exception:
                pass

        self.result['checks']['duplicate_classes'] = {
            'count': total_count,
            'files': file_issues
        }

        if total_count > 0:
            self.result['passed'] = False
            self.result['errors'].append(f'重複 class: {total_count} 個')

    def check_css_variables(self):
        """檢查 Shoelace CSS 變數殘留"""
        if not self.src_path.exists():
            return

        pattern = r'--sl-[a-z-]+'
        total_count = 0
        file_issues = {}

        for ext in ['*.js', '*.css']:
            for file_path in self.src_path.rglob(ext):
                try:
                    content = file_path.read_text(encoding='utf-8')
                    matches = re.findall(pattern, content)
                    if matches:
                        rel_path = str(file_path.relative_to(self.project_path))
                        file_issues[rel_path] = len(matches)
                        total_count += len(matches)
                except Exception:
                    pass

        self.result['checks']['css_variables'] = {
            'count': total_count,
            'files': file_issues
        }

        if total_count > 0:
            self.result['warnings'].append(f'CSS 變數殘留: {total_count} 個')

    def check_tailwind_config(self):
        """檢查 Tailwind 設定"""
        # Angular 專案使用自己的建構系統，跳過此檢查
        angular_json = self.project_path / 'angular.json'
        if angular_json.exists():
            self.result['checks']['tailwind_config'] = {
                'skipped': 'Angular 專案'
            }
            return

        vite_config = self.project_path / 'vite.config.js'

        if not vite_config.exists():
            return

        try:
            content = vite_config.read_text(encoding='utf-8')
            has_import = '@tailwindcss/vite' in content
            has_plugin = 'tailwindcss()' in content

            self.result['checks']['tailwind_config'] = {
                'has_import': has_import,
                'has_plugin': has_plugin
            }

            if not has_import or not has_plugin:
                self.result['passed'] = False
                self.result['errors'].append('Tailwind 設定不完整')
        except Exception:
            pass

    def check_package_json(self):
        """檢查 package.json"""
        pkg_path = self.project_path / 'package.json'

        if not pkg_path.exists():
            return

        # 判斷是否為 Angular 專案
        angular_json = self.project_path / 'angular.json'
        is_angular = angular_json.exists()

        try:
            pkg = json.loads(pkg_path.read_text(encoding='utf-8'))
            deps = {**pkg.get('dependencies', {}), **pkg.get('devDependencies', {})}

            has_tailwind = 'tailwindcss' in deps
            has_daisyui = 'daisyui' in deps
            has_vite_plugin = '@tailwindcss/vite' in deps
            has_shoelace = '@shoelace-style/shoelace' in deps

            self.result['checks']['package_json'] = {
                'has_tailwind': has_tailwind,
                'has_daisyui': has_daisyui,
                'has_vite_plugin': has_vite_plugin,
                'has_shoelace': has_shoelace,
                'is_angular': is_angular
            }

            # Angular 專案不需要 @tailwindcss/vite
            if not is_angular and not has_vite_plugin:
                self.result['passed'] = False
                self.result['errors'].append('缺少 @tailwindcss/vite')

            if has_shoelace:
                self.result['warnings'].append('Shoelace 依賴未移除')

        except Exception:
            pass

    def check_incomplete_html_tags(self):
        """檢查不完整的 HTML 標籤"""
        if not self.src_path.exists():
            return

        # 檢查 select 標籤是否有正確閉合
        tags_to_check = ['select', 'textarea', 'table', 'ul', 'ol']
        issues = []

        for file_path in self.src_path.rglob('*.js'):
            try:
                content = file_path.read_text(encoding='utf-8')
                rel_path = str(file_path.relative_to(self.project_path))

                for tag in tags_to_check:
                    # 計算開始和結束標籤數量
                    open_count = len(re.findall(rf'<{tag}[^>]*>', content))
                    close_count = len(re.findall(rf'</{tag}>', content))

                    if open_count > close_count:
                        diff = open_count - close_count
                        issues.append({
                            'file': rel_path,
                            'tag': tag,
                            'missing': diff
                        })
            except Exception:
                pass

        self.result['checks']['incomplete_html'] = {
            'count': len(issues),
            'issues': issues
        }

        if issues:
            self.result['passed'] = False
            for issue in issues[:5]:
                self.result['errors'].append(
                    f"HTML 標籤不完整: {issue['file']} 缺少 {issue['missing']} 個 </{issue['tag']}>"
                )

    def check_empty_buttons(self):
        """檢查空白按鈕內容"""
        if not self.src_path.exists():
            return

        # 找出空白按鈕: <button ...>空白或只有空格</button>
        # 或 <button ...>\n\n</button>
        pattern = r'<button[^>]*>\s*\n?\s*</button>'
        issues = []

        for file_path in self.src_path.rglob('*.js'):
            try:
                content = file_path.read_text(encoding='utf-8')
                matches = re.findall(pattern, content)
                if matches:
                    rel_path = str(file_path.relative_to(self.project_path))
                    issues.append({
                        'file': rel_path,
                        'count': len(matches)
                    })
            except Exception:
                pass

        self.result['checks']['empty_buttons'] = {
            'count': sum(i['count'] for i in issues),
            'files': issues
        }

        if issues:
            total = sum(i['count'] for i in issues)
            self.result['warnings'].append(f'空白按鈕: {total} 個')

    def check_empty_event_handlers(self):
        """檢查空白事件處理器"""
        if not self.src_path.exists():
            return

        # 找出 addEventListener('', ...) 或 addEventListener("", ...)
        pattern = r"addEventListener\s*\(\s*['\"]['\"]"
        issues = []

        for file_path in self.src_path.rglob('*.js'):
            try:
                content = file_path.read_text(encoding='utf-8')
                matches = re.findall(pattern, content)
                if matches:
                    rel_path = str(file_path.relative_to(self.project_path))
                    issues.append({
                        'file': rel_path,
                        'count': len(matches)
                    })
            except Exception:
                pass

        self.result['checks']['empty_event_handlers'] = {
            'count': sum(i['count'] for i in issues) if issues else 0,
            'files': issues
        }

        if issues:
            self.result['passed'] = False
            for issue in issues:
                self.result['errors'].append(
                    f"空白事件處理器: {issue['file']} 有 {issue['count']} 個"
                )
