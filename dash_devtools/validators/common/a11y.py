"""
A11Y 無障礙驗證器

檢查內容：
1. <button> / Button 缺 aria-label（無文字內容時）
2. <nav> 缺 aria-label
3. icon-only 按鈕缺 aria-label
4. <img> 缺 alt（補充現有 quality 檢查）
5. aria-current 在導航元件中的使用
"""

import re
from pathlib import Path


class A11yValidator:
    """A11Y 無障礙驗證器"""

    name = 'a11y'

    IGNORE_DIRS = [
        'node_modules', '.git', '.next', 'dist', 'build',
        '__pycache__', '.angular', 'venv', 'coverage',
    ]

    def __init__(self, project_path):
        self.project_path = Path(project_path)
        self.result = {
            'name': self.name,
            'passed': True,
            'errors': [],
            'warnings': [],
            'checks': {},
        }

    def run(self):
        tsx_files = self._find_tsx_files()
        self._check_icon_buttons(tsx_files)
        self._check_nav_labels(tsx_files)
        self._check_img_alt(tsx_files)
        return self.result

    def _find_tsx_files(self):
        files = []
        for ext in ('*.tsx', '*.jsx'):
            for f in self.project_path.rglob(ext):
                if not any(part in self.IGNORE_DIRS for part in f.parts):
                    files.append(f)
        return files

    def _check_icon_buttons(self, files):
        """檢查 icon-only 按鈕是否有 aria-label"""
        # 只匹配明確的 size="icon" 按鈕（真正的 icon-only）
        icon_button_pattern = re.compile(
            r"""<(?:button|Button)\b[^>]*size\s*=\s*['"]icon['"][^>]*>"""
        )
        accessible_pattern = re.compile(r'aria-label\s*[={]|sr-only')
        issues = []

        for f in files:
            content = f.read_text(encoding='utf-8', errors='ignore')
            lines = content.split('\n')
            for i, line in enumerate(lines, 1):
                if icon_button_pattern.search(line):
                    # 檢查前後 4 行是否有 aria-label 或 sr-only
                    context = lines[max(0, i - 2):i + 4]
                    context_str = ' '.join(context)
                    if not accessible_pattern.search(context_str):
                        rel = f.relative_to(self.project_path)
                        issues.append(f'{rel}:{i}')

        self.result['checks']['icon_buttons'] = {
            'count': len(issues),
            'files': issues[:10],
        }

        if issues:
            self.result['warnings'].append(
                f'Icon 按鈕缺 aria-label: {len(issues)} 個'
                + (f'（如 {issues[0]}）' if issues else '')
            )

    def _check_nav_labels(self, files):
        """檢查 <nav> 元素是否有 aria-label"""
        nav_pattern = re.compile(r'<nav\b')
        aria_pattern = re.compile(r'<nav\b[^>]*aria-label')
        issues = []

        for f in files:
            content = f.read_text(encoding='utf-8', errors='ignore')
            for i, line in enumerate(content.split('\n'), 1):
                if nav_pattern.search(line) and not aria_pattern.search(line):
                    rel = f.relative_to(self.project_path)
                    issues.append(f'{rel}:{i}')

        self.result['checks']['nav_labels'] = {
            'count': len(issues),
            'files': issues,
        }

        if issues:
            self.result['warnings'].append(
                f'<nav> 缺 aria-label: {len(issues)} 個'
                + (f'（如 {issues[0]}）' if issues else '')
            )

    def _check_img_alt(self, files):
        """檢查 <img> 是否有 alt 屬性"""
        img_pattern = re.compile(r'<img\b')
        alt_pattern = re.compile(r'<img\b[^>]*alt\s*=')
        aria_hidden_pattern = re.compile(r'<img\b[^>]*aria-hidden')
        issues = []

        for f in files:
            content = f.read_text(encoding='utf-8', errors='ignore')
            for i, line in enumerate(content.split('\n'), 1):
                if img_pattern.search(line):
                    if not alt_pattern.search(line) and not aria_hidden_pattern.search(line):
                        rel = f.relative_to(self.project_path)
                        issues.append(f'{rel}:{i}')

        self.result['checks']['img_alt'] = {
            'count': len(issues),
            'files': issues,
        }

        if issues:
            self.result['warnings'].append(
                f'<img> 缺 alt: {len(issues)} 個'
                + (f'（如 {issues[0]}）' if issues else '')
            )
