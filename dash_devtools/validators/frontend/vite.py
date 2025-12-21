"""
Vite 專案驗證器

檢查項目：
1. Shoelace 正確設定
2. 禁止 Emoji 圖示（應用 sl-icon）
3. HTML 標籤完整性
4. 空白按鈕/事件處理器
5. 表單與表格結構
6. Bundle 大小
"""

import re
import json
from pathlib import Path


# 常見 Emoji 圖示（這些應該用 sl-icon 取代）
ICON_EMOJI_PATTERNS = [
    # 工具與操作
    r'[\U0001F527\U0001F528\U0001F529]',  # wrench/hammer
    r'[\U0001F504\U0001F503]',  # refresh
    r'[\U0001F50D\U0001F50E]',  # search
    r'[\u2699]',  # gear
    r'[\U0001F5D1]',  # trash
    r'[\u270F]',  # pencil
    r'[\u2795]',  # plus
    r'[\u2796]',  # minus
    # 狀態指示
    r'[\u2705]',  # check mark
    r'[\u274C]',  # cross mark
    r'[\u26A0]',  # warning
    r'[\U0001F6A8]',  # alert
    r'[\u2139]',  # info
    # 物件與符號
    r'[\U0001F3E2]',  # building
    r'[\U0001F4CB]',  # clipboard
    r'[\U0001F4C5\U0001F4C6]',  # calendar
    r'[\U0001F464\U0001F465]',  # person/people
    r'[\U0001F512\U0001F513]',  # lock
    r'[\U0001F510]',  # key lock
    r'[\u231B\u23F3]',  # hourglass
    # 數字圓圈
    r'[1-9]\uFE0F?\u20E3',  # 1️⃣ 2️⃣ etc
]


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

        self.check_shoelace_setup()
        self.check_emoji_icons()
        self.check_incomplete_html_tags()
        self.check_empty_buttons()
        self.check_empty_event_handlers()
        self.check_table_structure()
        self.check_form_structure()
        self.check_ux_patterns()
        self.check_bundle_size()

        return self.result

    def check_shoelace_setup(self):
        """檢查 Shoelace 設定"""
        index_html = self.project_path / 'index.html'
        has_shoelace_css = False
        has_shoelace_js = False
        shoelace_version = None

        if index_html.exists():
            try:
                content = index_html.read_text(encoding='utf-8')
                has_shoelace_css = 'shoelace' in content.lower() and '.css' in content
                has_shoelace_js = 'shoelace' in content.lower() and '.js' in content

                # 嘗試取得版本
                version_match = re.search(r'shoelace@([\d.]+)', content)
                if version_match:
                    shoelace_version = version_match.group(1)
            except Exception:
                pass

        # 檢查 package.json
        pkg_path = self.project_path / 'package.json'
        has_shoelace_dep = False

        if pkg_path.exists():
            try:
                content = pkg_path.read_text(encoding='utf-8')
                has_shoelace_dep = '@shoelace-style/shoelace' in content
            except Exception:
                pass

        self.result['checks']['shoelace_setup'] = {
            'has_css': has_shoelace_css,
            'has_js': has_shoelace_js,
            'has_dependency': has_shoelace_dep,
            'version': shoelace_version
        }

        # Shoelace 是預期的，缺少才是問題
        if not has_shoelace_css and not has_shoelace_dep:
            self.result['warnings'].append('未偵測到 Shoelace 設定')

    def check_emoji_icons(self):
        """檢查 Emoji 圖示（應用 sl-icon 取代）"""
        if not self.src_path.exists():
            return

        total_count = 0
        file_issues = {}

        # 合併所有 emoji 模式
        combined_pattern = '|'.join(ICON_EMOJI_PATTERNS)

        for ext in ['*.js', '*.html']:
            for file_path in self.src_path.rglob(ext):
                if self._should_skip(file_path):
                    continue
                try:
                    content = file_path.read_text(encoding='utf-8')
                    # 只檢查 HTML 樣板字串中的 emoji
                    template_content = self._extract_template_strings(content)

                    matches = re.findall(combined_pattern, template_content)
                    if matches:
                        rel_path = str(file_path.relative_to(self.project_path))
                        file_issues[rel_path] = len(matches)
                        total_count += len(matches)
                except Exception:
                    pass

        self.result['checks']['emoji_icons'] = {
            'count': total_count,
            'files': file_issues
        }

        if total_count > 0:
            self.result['warnings'].append(
                f'Emoji 圖示: {total_count} 個（應改用 sl-icon）'
            )

    def _extract_template_strings(self, content):
        """提取 HTML 樣板字串內容"""
        template_matches = re.findall(r'`[^`]*`', content, re.DOTALL)
        return '\n'.join(template_matches)

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

        # 原生 button 和 sl-button 都檢查
        patterns = [
            r'<button[^>]*>\s*\n?\s*</button>',
            r'<sl-button[^>]*>\s*\n?\s*</sl-button>'
        ]
        issues = []

        for file_path in self.src_path.rglob('*.js'):
            if self._should_skip(file_path):
                continue
            try:
                content = file_path.read_text(encoding='utf-8')
                total_matches = 0
                for pattern in patterns:
                    matches = re.findall(pattern, content)
                    total_matches += len(matches)

                if total_matches > 0:
                    rel_path = str(file_path.relative_to(self.project_path))
                    issues.append({
                        'file': rel_path,
                        'count': total_matches
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
                            'issue': f'表格缺少 <thead>'
                        })
                    if tbody_count < table_count:
                        issues.append({
                            'file': rel_path,
                            'issue': f'表格缺少 <tbody>'
                        })

                # 檢查 tr 閉合
                tr_count = len(re.findall(r'<tr[^>]*>', content))
                tr_close_count = len(re.findall(r'</tr>', content))
                if tr_count > tr_close_count:
                    issues.append({
                        'file': rel_path,
                        'issue': f'表格行缺少 </tr> ({tr_count - tr_close_count} 個)'
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

                # 檢查 select/sl-select 是否有 option
                select_matches = list(re.finditer(r'<(?:sl-)?select[^>]*>', content))
                for match in select_matches:
                    start = match.end()
                    # 找對應閉合標籤
                    if 'sl-select' in match.group():
                        end = content.find('</sl-select>', start)
                    else:
                        end = content.find('</select>', start)

                    if end != -1:
                        select_content = content[start:end]
                        if '<option' not in select_content and '<sl-option' not in select_content:
                            issues.append({
                                'file': rel_path,
                                'issue': '下拉選單缺少選項'
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

                # 1. 圖示按鈕缺少 title
                # 找 sl-button 只有 sl-icon 沒有文字
                icon_only_buttons = re.findall(
                    r'<sl-button[^>]*>[\s\n]*<sl-icon[^>]*>[\s\n]*</sl-icon>[\s\n]*</sl-button>',
                    content
                )
                buttons_without_title = [b for b in icon_only_buttons if 'title=' not in b]
                if buttons_without_title:
                    issues.append({
                        'file': rel_path,
                        'issue': f'圖示按鈕缺少 title 屬性 ({len(buttons_without_title)} 個)',
                        'severity': 'a11y'
                    })

                # 2. 表格內操作按鈕數量過多（建議用 sl-dropdown）
                if '<td>' in content or '<td ' in content:
                    # 找 td 內有多個按鈕
                    td_matches = re.findall(r'<td[^>]*>([\s\S]*?)</td>', content)
                    for td_content in td_matches:
                        button_count = len(re.findall(r'<(?:sl-)?button', td_content))
                        if button_count > 3:
                            issues.append({
                                'file': rel_path,
                                'issue': f'表格儲存格按鈕過多 ({button_count} 個)，建議用下拉選單',
                                'severity': 'ux'
                            })
                            break

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
