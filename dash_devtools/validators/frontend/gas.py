"""
Google Apps Script (GAS) 專案驗證器 v1.1

支援 UI 框架：
- DaisyUI + Vue 3 CDN（主要）
- Shoelace（向下相容）

檢查項目：
1. appsscript.json 設定
2. Code.js 版本號管理
3. HTML 模板品質（v-for :key、標籤閉合）
4. DaisyUI 主題設定
5. Shoelace 綁定語法（僅限 Shoelace 專案）
"""

import re
import json
from pathlib import Path


class GasValidator:
    """Google Apps Script 專案驗證器"""

    name = 'gas'

    def __init__(self, project_path):
        self.project_path = Path(project_path)
        self.project_name = self.project_path.name
        self.result = {
            'name': self.name,
            'passed': True,
            'errors': [],
            'warnings': [],
            'checks': {}
        }
        # 偵測 UI 框架
        self.ui_framework = self._detect_ui_framework()
        self.has_vue = self._detect_vue()

    def _detect_ui_framework(self) -> str | None:
        """偵測 UI 框架（從 HTML 檔案判斷）"""
        for html_file in self.project_path.glob('*.html'):
            try:
                content = html_file.read_text(encoding='utf-8')
                # DaisyUI 優先檢測（更常見）
                if 'daisyui' in content.lower():
                    return 'daisyui'
                elif 'shoelace' in content.lower() or 'sl-' in content:
                    return 'shoelace'
            except Exception:
                pass
        return None

    def _detect_vue(self) -> bool:
        """偵測是否使用 Vue"""
        for html_file in self.project_path.glob('*.html'):
            try:
                content = html_file.read_text(encoding='utf-8')
                if 'vue' in content.lower() and ('v-if' in content or 'v-for' in content or ':' in content):
                    return True
            except Exception:
                pass
        return False

    def run(self):
        """執行所有驗證"""
        if not self.project_path.exists():
            self.result['passed'] = False
            self.result['errors'].append(f'專案路徑不存在: {self.project_path}')
            return self.result

        # 檢查 appsscript.json
        self.check_appsscript_config()

        # UI 框架特定檢查
        if self.ui_framework == 'daisyui':
            self.check_daisyui_setup()
        elif self.ui_framework == 'shoelace':
            self.check_shoelace_binding()
            if self.has_vue:
                self.check_vue_custom_element()

        # Code.js 版本檢查
        self.check_version_management()

        # HTML 品質檢查
        self.check_html_quality()

        return self.result

    def check_appsscript_config(self):
        """檢查 appsscript.json 設定"""
        config_file = self.project_path / 'appsscript.json'

        if not config_file.exists():
            self.result['passed'] = False
            self.result['errors'].append('缺少 appsscript.json')
            return

        try:
            config = json.loads(config_file.read_text(encoding='utf-8'))

            runtime = config.get('runtimeVersion', 'DEPRECATED_ES5')
            webapp = config.get('webapp', {})

            self.result['checks']['appsscript_config'] = {
                'runtime': runtime,
                'has_webapp': bool(webapp),
                'access': webapp.get('access', 'unknown')
            }

            if runtime == 'DEPRECATED_ES5':
                self.result['warnings'].append('建議使用 V8 runtime')

        except json.JSONDecodeError as e:
            self.result['passed'] = False
            self.result['errors'].append(f'appsscript.json 格式錯誤: {e}')

    def check_daisyui_setup(self):
        """檢查 DaisyUI 設定"""
        has_theme = False
        theme_value = None

        # 檢查 index.html 的 data-theme 設定
        index_html = self.project_path / 'index.html'
        if index_html.exists():
            try:
                content = index_html.read_text(encoding='utf-8')
                theme_match = re.search(r'data-theme\s*=\s*["\']([^"\']+)["\']', content)
                if theme_match:
                    has_theme = True
                    theme_value = theme_match.group(1)
            except Exception:
                pass

        self.result['checks']['daisyui_setup'] = {
            'has_theme': has_theme,
            'theme': theme_value,
            'ui_framework': 'daisyui'
        }

        if not has_theme:
            self.result['warnings'].append(
                'DaisyUI 未設定 data-theme，建議在 <html> 加入：\n'
                '  <html data-theme="light">'
            )

    def check_shoelace_binding(self):
        """檢查 Shoelace 元件綁定語法（僅限 Shoelace 專案）"""
        issues = []

        # 錯誤的 v-model 使用模式
        wrong_patterns = [
            (r'<sl-input[^>]*v-model\s*=\s*["\'][^"\']+["\']', 'sl-input'),
            (r'<sl-select[^>]*v-model\s*=\s*["\'][^"\']+["\']', 'sl-select'),
            (r'<sl-checkbox[^>]*v-model\s*=\s*["\'][^"\']+["\']', 'sl-checkbox'),
            (r'<sl-textarea[^>]*v-model\s*=\s*["\'][^"\']+["\']', 'sl-textarea'),
            (r'<sl-radio-group[^>]*v-model\s*=\s*["\'][^"\']+["\']', 'sl-radio-group'),
        ]

        for html_file in self.project_path.glob('*.html'):
            try:
                content = html_file.read_text(encoding='utf-8')
                rel_path = html_file.name

                for pattern, component in wrong_patterns:
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    if matches:
                        issues.append({
                            'file': rel_path,
                            'component': component,
                            'count': len(matches)
                        })

            except Exception:
                pass

        self.result['checks']['shoelace_binding'] = {
            'issues_count': len(issues),
            'issues': issues
        }

        if issues:
            self.result['passed'] = False
            for issue in issues:
                self.result['errors'].append(
                    f"Shoelace 綁定錯誤: {issue['file']} - {issue['component']} 使用 v-model（應改用 :value + @sl-input）"
                )

            self.result['warnings'].append(
                '正確寫法範例：\n'
                '  <sl-input :value="formData.name" @sl-input="e => formData.name = e.target.value"></sl-input>\n'
                '  <sl-select :value="formData.type" @sl-change="e => formData.type = e.target.value"></sl-select>'
            )

    def check_vue_custom_element(self):
        """檢查 Vue isCustomElement 設定（僅限 Shoelace 專案）"""
        has_config = False
        config_location = None

        for html_file in self.project_path.glob('*.html'):
            try:
                content = html_file.read_text(encoding='utf-8')

                if 'isCustomElement' in content:
                    has_config = True
                    config_location = html_file.name

                    if "tag.startsWith('sl-')" in content or "tag.startsWith(\"sl-\")" in content:
                        break

            except Exception:
                pass

        self.result['checks']['vue_custom_element'] = {
            'has_config': has_config,
            'config_location': config_location
        }

        if not has_config:
            self.result['warnings'].append(
                'Vue 未設定 isCustomElement，可能導致 Shoelace 元件警告\n'
                '  建議在 Vue 初始化時加入：\n'
                "  app.config.compilerOptions.isCustomElement = tag => tag.startsWith('sl-');"
            )

    def check_version_management(self):
        """檢查 Code.js 版本號管理"""
        code_js = self.project_path / 'Code.js'

        if not code_js.exists():
            self.result['checks']['version_management'] = {'skipped': '無 Code.js'}
            return

        try:
            content = code_js.read_text(encoding='utf-8')

            # 尋找版本號
            version_match = re.search(r"case\s+['\"]getVersion['\"]:\s*\n?\s*return\s*{\s*success:\s*true,\s*data:\s*['\"]([^'\"]+)['\"]", content)

            if version_match:
                version = version_match.group(1)
                self.result['checks']['version_management'] = {
                    'version': version,
                    'has_version_api': True
                }
            else:
                self.result['checks']['version_management'] = {
                    'has_version_api': False
                }
                self.result['warnings'].append(
                    'Code.js 未找到 getVersion API，建議加入版本管理：\n'
                    "  case 'getVersion':\n"
                    "    return { success: true, data: '1.0.0' };"
                )

        except Exception as e:
            self.result['checks']['version_management'] = {'error': str(e)}

    def check_html_quality(self):
        """檢查 HTML 品質"""
        html_files = list(self.project_path.glob('*.html'))
        issues = []

        for html_file in html_files:
            try:
                content = html_file.read_text(encoding='utf-8')
                rel_path = html_file.name
                file_issues = []

                # 檢查 v-for 是否有 :key
                v_for_without_key = re.findall(r'v-for="[^"]*"(?![^>]*:key)', content)
                if v_for_without_key:
                    file_issues.append(f'v-for 缺少 :key ({len(v_for_without_key)} 處)')

                # 檢查空的事件處理器
                empty_handlers = re.findall(r'@\w+\s*=\s*["\']["\']', content)
                if empty_handlers:
                    file_issues.append(f'空的事件處理器 ({len(empty_handlers)} 處)')

                # 檢查未閉合的 HTML 標籤（簡單檢查）
                tags_to_check = ['div', 'span', 'table', 'ul', 'ol', 'select']
                for tag in tags_to_check:
                    open_count = len(re.findall(rf'<{tag}[^>]*(?<!/)>', content))
                    close_count = len(re.findall(rf'</{tag}>', content))
                    self_closing = len(re.findall(rf'<{tag}[^>]*/>', content))
                    open_count -= self_closing

                    if open_count > close_count + 2:
                        file_issues.append(f'<{tag}> 標籤可能未正確閉合')

                if file_issues:
                    issues.append({
                        'file': rel_path,
                        'issues': file_issues
                    })

            except Exception:
                pass

        self.result['checks']['html_quality'] = {
            'total_files': len(html_files),
            'files_with_issues': len(issues),
            'issues': issues
        }

        for issue in issues:
            for problem in issue['issues']:
                if '缺少' in problem or '未正確閉合' in problem:
                    self.result['warnings'].append(f"HTML: {issue['file']} - {problem}")
