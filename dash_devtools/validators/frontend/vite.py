"""
Vite 專案驗證器 v2.2

支援：
- Vue 3 + Vite + PrimeVue (標準架構)

檢查內容：
1. 禁用技術偵測 (DaisyUI/TailwindCSS/Shoelace)
2. Vue SFC 語法檢查
3. 禁止 Emoji 圖示
4. HTML 標籤完整性
5. 空白按鈕/事件處理器
6. Bundle 大小
"""

import re
import json
import subprocess
from fnmatch import fnmatch
from pathlib import Path


# 常見 Emoji 圖示（這些應該用圖示庫取代）
ICON_EMOJI_PATTERNS = [
    r'[\U0001F527\U0001F528\U0001F529]',  # wrench/hammer
    r'[\U0001F504\U0001F503]',  # refresh
    r'[\U0001F50D\U0001F50E]',  # search
    r'[\u2699]',  # gear
    r'[\U0001F5D1]',  # trash
    r'[\u270F]',  # pencil
    r'[\u2795]',  # plus
    r'[\u2796]',  # minus
    r'[\u2705]',  # check mark
    r'[\u274C]',  # cross mark
    r'[\u26A0]',  # warning
    r'[\U0001F6A8]',  # alert
    r'[\u2139]',  # info
    r'[\U0001F3E2]',  # building
    r'[\U0001F4CB]',  # clipboard
    r'[\U0001F4C5\U0001F4C6]',  # calendar
    r'[\U0001F464\U0001F465]',  # person/people
    r'[\U0001F512\U0001F513]',  # lock
    r'[\U0001F510]',  # key lock
    r'[\u231B\u23F3]',  # hourglass
    r'[1-9]\uFE0F?\u20E3',  # 1️⃣ 2️⃣ etc
]


class ViteValidator:
    """Vite 專案驗證器 (支援 Vue 3 + PrimeVue)"""

    name = 'vite'

    IGNORE_DIRS = [
        'node_modules', '.git', 'dist', 'build', '.cache', '.vercel'
    ]

    def __init__(self, project_path):
        self.project_path = Path(project_path)
        self.project_name = self.project_path.name
        self.src_path = self.project_path / 'src'
        self.scanignore = self._parse_scanignore()
        self.result = {
            'name': self.name,
            'passed': True,
            'errors': [],
            'warnings': [],
            'checks': {}
        }
        # 偵測專案類型
        self.ui_framework = self._detect_ui_framework()
        self.is_vue = self._detect_vue()

    def _detect_ui_framework(self) -> str | None:
        """偵測 UI 框架"""
        pkg_path = self.project_path / 'package.json'
        if not pkg_path.exists():
            return None

        try:
            pkg = json.loads(pkg_path.read_text(encoding='utf-8'))
            deps = {**pkg.get('dependencies', {}), **pkg.get('devDependencies', {})}

            if 'daisyui' in deps:
                return 'daisyui'
            if 'tailwindcss' in deps:
                return 'tailwind'
        except Exception:
            pass
        return None

    def _detect_vue(self) -> bool:
        """偵測是否為 Vue 專案"""
        pkg_path = self.project_path / 'package.json'
        if not pkg_path.exists():
            return False

        try:
            pkg = json.loads(pkg_path.read_text(encoding='utf-8'))
            deps = {**pkg.get('dependencies', {}), **pkg.get('devDependencies', {})}
            return 'vue' in deps
        except Exception:
            return False

    def run(self):
        """執行所有驗證"""
        if not self.project_path.exists():
            self.result['passed'] = False
            self.result['errors'].append(f'專案路徑不存在: {self.project_path}')
            return self.result

        # 禁用技術偵測
        self.check_banned_frameworks()

        # Vue SFC 檢查
        if self.is_vue:
            self.check_vue_sfc()

        # 通用檢查
        self.check_emoji_icons()
        self.check_incomplete_html_tags()
        self.check_empty_buttons()
        self.check_bundle_size()

        return self.result

    def check_banned_frameworks(self):
        """偵測禁用技術 (DaisyUI / TailwindCSS)"""
        pkg_path = self.project_path / 'package.json'
        if not pkg_path.exists():
            return

        try:
            pkg = json.loads(pkg_path.read_text(encoding='utf-8'))
            deps = {**pkg.get('dependencies', {}), **pkg.get('devDependencies', {})}
        except Exception:
            return

        banned = []
        if 'daisyui' in deps:
            banned.append(f"DaisyUI {deps.get('daisyui', '')}")
        if 'tailwindcss' in deps or '@tailwindcss/vite' in deps:
            ver = deps.get('tailwindcss') or deps.get('@tailwindcss/vite', '')
            banned.append(f"TailwindCSS {ver}")
        if '@shoelace-style/shoelace' in deps:
            banned.append(f"Shoelace {deps.get('@shoelace-style/shoelace', '')}")

        self.result['checks']['banned_frameworks'] = {
            'banned': banned
        }

        if banned:
            self.result['warnings'].append(
                f"偵測到禁用技術: {', '.join(banned)}。建議重構至 Vite + Vue 3 + PrimeVue"
            )

    def check_vue_sfc(self):
        """檢查 Vue SFC 語法"""
        if not self.src_path.exists():
            return

        vue_files = list(self.src_path.rglob('*.vue'))
        issues = []

        for file_path in vue_files:
            if self._should_skip(file_path):
                continue

            try:
                content = file_path.read_text(encoding='utf-8')
                rel_path = str(file_path.relative_to(self.project_path))
                file_issues = []

                # 1. 檢查基本結構
                has_template = '<template>' in content or '<template ' in content
                has_script = '<script' in content

                if not has_template:
                    file_issues.append('缺少 <template> 區塊')

                # 2. 檢查 script setup 語法
                if '<script setup' in content:
                    # 檢查是否有未使用的 import
                    imports = re.findall(r'import\s+{([^}]+)}\s+from', content)
                    for import_group in imports:
                        items = [i.strip() for i in import_group.split(',')]
                        for item in items:
                            # 簡單檢查：import 的元件是否在 template 中使用
                            clean_item = item.split(' as ')[-1].strip()
                            template_match = re.search(r'<template[^>]*>([\s\S]*)</template>', content)
                            if template_match:
                                template_content = template_match.group(1)
                                # 檢查元件使用 (PascalCase 或 kebab-case)
                                kebab_case = re.sub(r'(?<!^)(?=[A-Z])', '-', clean_item).lower()
                                if clean_item not in template_content and kebab_case not in template_content:
                                    # 可能是未使用的 import，但不確定，只記錄為 info
                                    pass

                # 3. 檢查 template 中的常見錯誤
                template_match = re.search(r'<template[^>]*>([\s\S]*)</template>', content)
                if template_match:
                    template = template_match.group(1)

                    # 檢查 v-for 是否有 :key
                    v_for_without_key = re.findall(r'v-for="[^"]*"(?![^>]*:key)', template)
                    if v_for_without_key:
                        file_issues.append(f'v-for 缺少 :key ({len(v_for_without_key)} 處)')

                    # 檢查空的 @click
                    empty_click = re.findall(r'@click="\s*"', template)
                    if empty_click:
                        file_issues.append(f'空的 @click 事件處理器 ({len(empty_click)} 處)')

                if file_issues:
                    issues.append({
                        'file': rel_path,
                        'issues': file_issues
                    })

            except Exception:
                pass

        self.result['checks']['vue_sfc'] = {
            'total_files': len(vue_files),
            'files_with_issues': len(issues),
            'issues': issues
        }

        # 只有嚴重問題才報錯
        for issue in issues:
            for problem in issue['issues']:
                if '缺少' in problem:
                    self.result['errors'].append(f"Vue SFC: {issue['file']} - {problem}")
                else:
                    self.result['warnings'].append(f"Vue SFC: {issue['file']} - {problem}")

    def check_vue_tsc(self):
        """執行 vue-tsc 類型檢查"""
        pkg_path = self.project_path / 'package.json'
        has_vue_tsc = False

        if pkg_path.exists():
            try:
                content = pkg_path.read_text(encoding='utf-8')
                has_vue_tsc = 'vue-tsc' in content
            except Exception:
                pass

        if not has_vue_tsc:
            self.result['checks']['vue_tsc'] = {'skipped': '未安裝 vue-tsc'}
            return

        try:
            result = subprocess.run(
                ['npx', 'vue-tsc', '--noEmit'],
                cwd=self.project_path,
                capture_output=True,
                text=True,
                timeout=60
            )

            self.result['checks']['vue_tsc'] = {
                'passed': result.returncode == 0,
                'output': result.stdout[:500] if result.stdout else result.stderr[:500]
            }

            if result.returncode != 0:
                self.result['warnings'].append('vue-tsc 類型檢查有警告或錯誤')

        except subprocess.TimeoutExpired:
            self.result['checks']['vue_tsc'] = {'error': '執行逾時'}
        except Exception as e:
            self.result['checks']['vue_tsc'] = {'error': str(e)}

    def check_emoji_icons(self):
        """檢查 Emoji 圖示"""
        if not self.src_path.exists():
            return

        total_count = 0
        file_issues = {}
        combined_pattern = '|'.join(ICON_EMOJI_PATTERNS)

        # 根據專案類型決定要檢查的副檔名
        extensions = ['*.js', '*.ts', '*.html']
        if self.is_vue:
            extensions.append('*.vue')

        for ext in extensions:
            for file_path in self.src_path.rglob(ext):
                if self._should_skip(file_path):
                    continue
                try:
                    content = file_path.read_text(encoding='utf-8')
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
            icon_lib = 'PrimeIcons (pi pi-xxx)' if self.is_vue else 'PrimeIcons'
            self.result['warnings'].append(
                f'Emoji 圖示: {total_count} 個（應改用 {icon_lib}）'
            )

    def _extract_template_strings(self, content):
        """提取模板字串內容"""
        # JavaScript 模板字串
        template_matches = re.findall(r'`[^`]*`', content, re.DOTALL)
        # Vue template
        vue_template = re.findall(r'<template[^>]*>([\s\S]*?)</template>', content)
        return '\n'.join(template_matches + vue_template)

    def check_incomplete_html_tags(self):
        """檢查不完整的 HTML 標籤"""
        if not self.src_path.exists():
            return

        tags_to_check = ['select', 'textarea', 'table', 'ul', 'ol', 'div']
        issues = []

        extensions = ['*.js', '*.ts']
        if self.is_vue:
            extensions.append('*.vue')

        for ext in extensions:
            for file_path in self.src_path.rglob(ext):
                if self._should_skip(file_path):
                    continue
                try:
                    content = file_path.read_text(encoding='utf-8')
                    rel_path = str(file_path.relative_to(self.project_path))

                    # 檢查 [pattern:HTML 標籤不完整] 排除
                    if self._is_pattern_ignored(rel_path, 'HTML 標籤不完整'):
                        continue

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

        patterns = [
            r'<button[^>]*>\s*\n?\s*</button>',
        ]
        issues = []

        extensions = ['*.js', '*.ts']
        if self.is_vue:
            extensions.append('*.vue')

        for ext in extensions:
            for file_path in self.src_path.rglob(ext):
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

    def check_bundle_size(self):
        """檢查 Bundle 大小"""
        dist_path = self.project_path / 'dist'
        if not dist_path.exists():
            self.result['checks']['bundle_size'] = {'skipped': '無 dist 目錄'}
            return

        css_size = sum(f.stat().st_size for f in dist_path.rglob('*.css'))
        js_size = sum(f.stat().st_size for f in dist_path.rglob('*.js'))

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

    def _parse_scanignore(self):
        """解析 .scanignore 檔案"""
        scanignore_file = self.project_path / '.scanignore'
        result = {'paths': [], 'pattern_paths': []}

        if not scanignore_file.exists():
            return result

        try:
            for line in scanignore_file.read_text(encoding='utf-8').splitlines():
                line = line.strip()
                if not line or line.startswith('#'):
                    continue

                pattern_match = re.match(r'^\[pattern:(.+?)\]\s+(.+)$', line)
                if pattern_match:
                    pattern_name = pattern_match.group(1).strip()
                    path_glob = pattern_match.group(2).strip()
                    result['pattern_paths'].append((pattern_name, path_glob))
                else:
                    result['paths'].append(line)
        except Exception:
            pass

        return result

    def _is_pattern_ignored(self, rel_path, pattern_name):
        """檢查檔案是否被 .scanignore 的特定 pattern 排除"""
        for p_name, p_glob in self.scanignore['pattern_paths']:
            if p_name == pattern_name:
                if fnmatch(rel_path, p_glob):
                    return True
                if rel_path == p_glob:
                    return True
        return False

    def _should_skip(self, file_path):
        """檢查是否應該跳過該檔案"""
        return any(ignore in str(file_path) for ignore in self.IGNORE_DIRS)
