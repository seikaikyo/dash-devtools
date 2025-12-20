"""
Vite 專案驗證器

檢查項目：
1. Tailwind CSS 4 設定
2. DaisyUI 5 設定
3. Shoelace 殘留
4. HTML 標籤完整性
5. 空白按鈕/事件處理器
6. Bundle 大小
"""

import re
import json
from pathlib import Path


class ViteValidator:
    """Vite 專案驗證器"""

    name = 'vite'

    # 忽略目錄
    IGNORE_DIRS = [
        'node_modules', '.git', 'dist', 'build', '.cache'
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

        self.check_tailwind_config()
        self.check_daisyui_config()
        self.check_shoelace_remnants()
        self.check_css_variables()
        self.check_incomplete_html_tags()
        self.check_empty_buttons()
        self.check_empty_event_handlers()
        self.check_table_structure()
        self.check_dropdown_structure()
        self.check_form_structure()
        self.check_ux_patterns()
        self.check_bundle_size()

        return self.result

    def check_tailwind_config(self):
        """檢查 Tailwind CSS 4 設定"""
        vite_config = self.project_path / 'vite.config.js'

        if not vite_config.exists():
            self.result['checks']['tailwind_config'] = {'skipped': '無 vite.config.js'}
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
                self.result['errors'].append('Tailwind CSS 4 設定不完整')
        except Exception:
            pass

    def check_daisyui_config(self):
        """檢查 DaisyUI 5 設定"""
        # 檢查 CSS 中是否有 @plugin "daisyui"
        main_css = self.src_path / 'styles' / 'main.css'
        if not main_css.exists():
            main_css = self.src_path / 'main.css'
        if not main_css.exists():
            main_css = self.src_path / 'styles.css'

        has_plugin = False
        has_theme = False

        if main_css.exists():
            try:
                content = main_css.read_text(encoding='utf-8')
                has_plugin = '@plugin "daisyui"' in content or "@plugin 'daisyui'" in content
            except Exception:
                pass

        # 檢查 HTML 是否有 data-theme
        index_html = self.project_path / 'index.html'
        if index_html.exists():
            try:
                content = index_html.read_text(encoding='utf-8')
                has_theme = 'data-theme=' in content
            except Exception:
                pass

        self.result['checks']['daisyui_config'] = {
            'has_plugin': has_plugin,
            'has_theme': has_theme
        }

        if not has_theme:
            self.result['warnings'].append('HTML 缺少 data-theme 屬性（可能導致深色模式問題）')

    def check_shoelace_remnants(self):
        """檢查 Shoelace 元件殘留"""
        if not self.src_path.exists():
            return

        pattern = r'<sl-[a-z-]+'
        total_count = 0
        file_issues = {}

        for file_path in self.src_path.rglob('*.js'):
            if self._should_skip(file_path):
                continue
            try:
                content = file_path.read_text(encoding='utf-8')
                matches = re.findall(pattern, content)
                if matches:
                    rel_path = str(file_path.relative_to(self.project_path))
                    file_issues[rel_path] = len(matches)
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

    def check_css_variables(self):
        """檢查 Shoelace CSS 變數殘留"""
        if not self.src_path.exists():
            return

        pattern = r'--sl-[a-z-]+'
        total_count = 0
        file_issues = {}

        for ext in ['*.js', '*.css']:
            for file_path in self.src_path.rglob(ext):
                if self._should_skip(file_path):
                    continue
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
            self.result['warnings'].append(f'Shoelace CSS 變數殘留: {total_count} 個')

    def check_incomplete_html_tags(self):
        """檢查不完整的 HTML 標籤"""
        if not self.src_path.exists():
            return

        tags_to_check = ['select', 'textarea', 'table', 'ul', 'ol']
        issues = []

        for file_path in self.src_path.rglob('*.js'):
            if self._should_skip(file_path):
                continue
            try:
                content = file_path.read_text(encoding='utf-8')
                rel_path = str(file_path.relative_to(self.project_path))

                for tag in tags_to_check:
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

        pattern = r'<button[^>]*>\s*\n?\s*</button>'
        issues = []

        for file_path in self.src_path.rglob('*.js'):
            if self._should_skip(file_path):
                continue
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

        pattern = r"addEventListener\s*\(\s*['\"]['\"]"
        issues = []

        for file_path in self.src_path.rglob('*.js'):
            if self._should_skip(file_path):
                continue
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

    def check_table_structure(self):
        """檢查表格結構完整性"""
        if not self.src_path.exists():
            return

        issues = []

        for file_path in self.src_path.rglob('*.js'):
            if self._should_skip(file_path):
                continue
            try:
                content = file_path.read_text(encoding='utf-8')
                rel_path = str(file_path.relative_to(self.project_path))

                # 檢查 table 是否有 thead 和 tbody
                table_count = len(re.findall(r'<table[^>]*>', content))
                thead_count = len(re.findall(r'<thead[^>]*>', content))
                tbody_count = len(re.findall(r'<tbody[^>]*>', content))

                if table_count > 0:
                    if thead_count < table_count:
                        issues.append({
                            'file': rel_path,
                            'issue': f'表格缺少 <thead> ({table_count} 個 table，{thead_count} 個 thead)'
                        })
                    if tbody_count < table_count:
                        issues.append({
                            'file': rel_path,
                            'issue': f'表格缺少 <tbody> ({table_count} 個 table，{tbody_count} 個 tbody)'
                        })

                # 檢查 tr 和 td/th 配對
                tr_count = len(re.findall(r'<tr[^>]*>', content))
                tr_close_count = len(re.findall(r'</tr>', content))
                if tr_count > tr_close_count:
                    issues.append({
                        'file': rel_path,
                        'issue': f'表格行缺少閉合標籤 (缺 {tr_count - tr_close_count} 個 </tr>)'
                    })

            except Exception:
                pass

        self.result['checks']['table_structure'] = {
            'count': len(issues),
            'issues': issues
        }

        if issues:
            for issue in issues[:5]:
                self.result['warnings'].append(f"{issue['file']}: {issue['issue']}")

    def check_dropdown_structure(self):
        """檢查 DaisyUI Dropdown 結構"""
        if not self.src_path.exists():
            return

        issues = []

        for file_path in self.src_path.rglob('*.js'):
            if self._should_skip(file_path):
                continue
            try:
                content = file_path.read_text(encoding='utf-8')
                rel_path = str(file_path.relative_to(self.project_path))

                # DaisyUI dropdown 需要特定結構
                # <div class="dropdown">
                #   <div tabindex="0" ...>觸發器</div>
                #   <ul tabindex="0" class="dropdown-content ...">內容</ul>
                # </div>

                dropdown_count = len(re.findall(r'class="[^"]*dropdown[^"]*"', content))
                dropdown_content_count = len(re.findall(r'class="[^"]*dropdown-content[^"]*"', content))
                tabindex_count = len(re.findall(r'tabindex="0"', content))

                if dropdown_count > 0:
                    if dropdown_content_count < dropdown_count:
                        issues.append({
                            'file': rel_path,
                            'issue': f'Dropdown 缺少 dropdown-content ({dropdown_count} 個 dropdown，{dropdown_content_count} 個 content)'
                        })
                    # 每個 dropdown 需要至少 2 個 tabindex="0"
                    if tabindex_count < dropdown_count * 2:
                        issues.append({
                            'file': rel_path,
                            'issue': f'Dropdown 可能缺少 tabindex="0" (需要 {dropdown_count * 2} 個，只有 {tabindex_count} 個)'
                        })

            except Exception:
                pass

        self.result['checks']['dropdown_structure'] = {
            'count': len(issues),
            'issues': issues
        }

        if issues:
            for issue in issues[:3]:
                self.result['warnings'].append(f"{issue['file']}: {issue['issue']}")

    def check_form_structure(self):
        """檢查表單結構"""
        if not self.src_path.exists():
            return

        issues = []

        for file_path in self.src_path.rglob('*.js'):
            if self._should_skip(file_path):
                continue
            try:
                content = file_path.read_text(encoding='utf-8')
                rel_path = str(file_path.relative_to(self.project_path))

                # 檢查 select 是否有 option
                select_matches = list(re.finditer(r'<select[^>]*>', content))
                for match in select_matches:
                    # 找到對應的 </select>
                    start = match.end()
                    end = content.find('</select>', start)
                    if end != -1:
                        select_content = content[start:end]
                        if '<option' not in select_content:
                            issues.append({
                                'file': rel_path,
                                'issue': '下拉選單缺少選項 (<option>)'
                            })

                # 檢查 label 和 input 配對
                labels = re.findall(r'<label[^>]*for="([^"]+)"', content)
                for label_for in labels:
                    if f'id="{label_for}"' not in content:
                        issues.append({
                            'file': rel_path,
                            'issue': f'Label for="{label_for}" 找不到對應的 input'
                        })

            except Exception:
                pass

        self.result['checks']['form_structure'] = {
            'count': len(issues),
            'issues': issues
        }

        if issues:
            for issue in issues[:5]:
                self.result['warnings'].append(f"{issue['file']}: {issue['issue']}")

    def check_ux_patterns(self):
        """檢查 UI/UX 模式"""
        if not self.src_path.exists():
            return

        issues = []

        for file_path in self.src_path.rglob('*.js'):
            if self._should_skip(file_path):
                continue
            try:
                content = file_path.read_text(encoding='utf-8')
                rel_path = str(file_path.relative_to(self.project_path))

                # 1. 表格內的下拉選單操作（建議改用圖示按鈕）
                # 偵測: <td> 內有 dropdown
                if '<td>' in content or '<td ' in content:
                    td_dropdown = len(re.findall(r'<td[^>]*>[\s\S]*?dropdown[\s\S]*?</td>', content))
                    if td_dropdown > 0:
                        issues.append({
                            'file': rel_path,
                            'issue': f'表格內使用下拉選單 ({td_dropdown} 處)，建議改用圖示按鈕',
                            'severity': 'ux'
                        })

                # 2. 缺少 title 屬性的圖示按鈕
                icon_buttons = re.findall(r'<button[^>]*class="[^"]*btn[^"]*"[^>]*>[\s]*<i[^>]*></i>[\s]*</button>', content)
                buttons_without_title = [b for b in icon_buttons if 'title=' not in b]
                if buttons_without_title:
                    issues.append({
                        'file': rel_path,
                        'issue': f'圖示按鈕缺少 title 屬性 ({len(buttons_without_title)} 個)',
                        'severity': 'a11y'
                    })

                # 3. 巢狀過深的選單（超過 2 層）
                nested_menus = len(re.findall(r'dropdown-content[\s\S]*?dropdown-content', content))
                if nested_menus > 0:
                    issues.append({
                        'file': rel_path,
                        'issue': '發現巢狀選單，可能影響使用體驗',
                        'severity': 'ux'
                    })

                # 4. 白底卡片缺乏視覺區分（DaisyUI card 問題）
                # 偵測 class="card bg-base-100" 但外層 CSS 可能沒有邊框
                white_cards = len(re.findall(r'class="[^"]*card[^"]*bg-base-100[^"]*"', content))
                if white_cards > 0:
                    # 檢查 CSS 是否有處理 .card.bg-base-100 邊框
                    css_files = list(self.src_path.rglob('*.css'))
                    has_card_border = False
                    for css_file in css_files:
                        try:
                            css_content = css_file.read_text(encoding='utf-8')
                            if '.card.bg-base-100' in css_content and 'border' in css_content:
                                has_card_border = True
                                break
                        except Exception:
                            pass

                    if not has_card_border:
                        issues.append({
                            'file': rel_path,
                            'issue': f'白底卡片 ({white_cards} 個) 缺乏邊框，可能難以辨識',
                            'severity': 'ui'
                        })

            except Exception:
                pass

        self.result['checks']['ux_patterns'] = {
            'count': len(issues),
            'issues': issues
        }

        if issues:
            for issue in issues[:5]:
                severity = issue.get('severity', 'ux')
                prefix_map = {'ux': '[UX]', 'a11y': '[A11Y]', 'ui': '[UI]'}
                prefix = prefix_map.get(severity, '[UX]')
                self.result['warnings'].append(f"{prefix} {issue['file']}: {issue['issue']}")

    def check_bundle_size(self):
        """檢查 Bundle 大小"""
        dist_path = self.project_path / 'dist'
        if not dist_path.exists():
            self.result['checks']['bundle_size'] = {'skipped': '無 dist 目錄'}
            return

        css_size = 0
        js_size = 0

        for f in dist_path.rglob('*.css'):
            css_size += f.stat().st_size

        for f in dist_path.rglob('*.js'):
            js_size += f.stat().st_size

        css_kb = css_size / 1024
        js_kb = js_size / 1024

        self.result['checks']['bundle_size'] = {
            'css_kb': round(css_kb, 2),
            'js_kb': round(js_kb, 2)
        }

        if css_kb > 200:
            self.result['warnings'].append(f'CSS Bundle 過大: {css_kb:.2f} KB (建議 < 200 KB)')
        if js_kb > 500:
            self.result['warnings'].append(f'JS Bundle 過大: {js_kb:.2f} KB (建議 < 500 KB)')

    def _should_skip(self, file_path):
        """檢查是否應該跳過該檔案"""
        return any(ignore in str(file_path) for ignore in self.IGNORE_DIRS)
