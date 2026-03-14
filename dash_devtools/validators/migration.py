"""
UI 框架驗證器

檢查內容：
1. 禁止使用 Emoji 作為圖示（應用 PrimeIcons）
2. 重複 class 屬性
3. 不完整 HTML 標籤
4. 空白按鈕
5. 空白事件處理器
"""

import re
from pathlib import Path


# 常見 Emoji 圖示（這些應該用 PrimeIcons 取代）
ICON_EMOJI_PATTERNS = [
    # 工具與操作
    r'[\U0001F527\U0001F528\U0001F529]',  # wrench/hammer
    r'[\U0001F504\U0001F503]',  # refresh
    r'[\U0001F50D\U0001F50E]',  # search
    r'[\u2699\uFE0F]?',  # gear
    r'[\U0001F5D1\uFE0F]?',  # trash
    r'[\u270F\uFE0F]?',  # pencil
    r'[\u2795]',  # plus
    r'[\u2796]',  # minus
    # 狀態指示
    r'[\u2705]',  # check mark
    r'[\u274C]',  # cross mark
    r'[\u26A0\uFE0F]?',  # warning
    r'[\U0001F6A8]',  # alert
    r'[\u2139\uFE0F]?',  # info
    # 物件與符號
    r'[\U0001F3E2]',  # building
    r'[\U0001F4CB]',  # clipboard
    r'[\U0001F4C5\U0001F4C6]',  # calendar
    r'[\U0001F464\U0001F465]',  # person/people
    r'[\U0001F512\U0001F513]',  # lock
    r'[\U0001F510]',  # key lock
    r'[\u231B]',  # hourglass
    r'[\u23F3]',  # hourglass flowing
    # 數字圓圈
    r'[1-9]\uFE0F?\u20E3',  # 1-circle etc
]


class MigrationValidator:
    """UI 框架驗證器"""

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

        # 判斷專案類型
        is_angular = (self.project_path / 'angular.json').exists()
        has_primevue = self._has_primevue()

        if is_angular:
            self.result['checks']['framework'] = 'Angular + PrimeNG'
        elif has_primevue:
            self.result['checks']['framework'] = 'Vue 3 + PrimeVue'

        # Emoji 圖示檢查（所有專案適用）
        self.check_emoji_icons()

        # 通用檢查
        self.check_duplicate_classes()
        self.check_incomplete_html_tags()
        self.check_empty_buttons()
        self.check_empty_event_handlers()

        return self.result

    def _has_primevue(self):
        """檢查是否為 PrimeVue 專案"""
        pkg_path = self.project_path / 'package.json'
        if not pkg_path.exists():
            return False
        try:
            content = pkg_path.read_text(encoding='utf-8')
            return 'primevue' in content
        except Exception:
            return False

    def check_emoji_icons(self):
        """檢查 Emoji 圖示（應用 PrimeIcons 取代）"""
        if not self.src_path.exists():
            return

        total_count = 0
        file_issues = {}

        # 合併所有 emoji 模式
        combined_pattern = '|'.join(ICON_EMOJI_PATTERNS)

        for ext in ['*.js', '*.html', '*.vue', '*.ts']:
            for file_path in self.src_path.rglob(ext):
                try:
                    content = file_path.read_text(encoding='utf-8')
                    # 排除 console.log 中的 emoji（允許 log 用 emoji）
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
                f'Emoji 圖示: {total_count} 個（建議改用 PrimeIcons）'
            )

    def _extract_template_strings(self, content):
        """提取 HTML 樣板字串內容"""
        # 匹配 `...` 樣板字串
        template_matches = re.findall(r'`[^`]*`', content, re.DOTALL)
        # Vue template
        vue_template = re.findall(r'<template[^>]*>([\s\S]*?)</template>', content)
        return '\n'.join(template_matches + vue_template)

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

    def check_incomplete_html_tags(self):
        """檢查不完整的 HTML 標籤"""
        if not self.src_path.exists():
            return

        tags_to_check = ['select', 'textarea', 'table', 'ul', 'ol']
        issues = []

        for file_path in self.src_path.rglob('*.js'):
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
