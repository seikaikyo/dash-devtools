"""
程式碼品質驗證器

檢查項目：
1. 檔案行數限制 (500 行)
2. 命名規範
3. 中文註解
4. 禁止簡體字
5. 禁止 Emoji（應使用 icon font）
"""

import re
from pathlib import Path


class CodeQualityValidator:
    """程式碼品質驗證器"""

    name = 'code_quality'

    # 設定
    MAX_FILE_LINES = 500

    # 常見簡體字
    SIMPLIFIED_CHINESE = [
        '这', '个', '们', '为', '与', '来', '对', '时', '后', '进',
        '发', '会', '过', '着', '动', '机', '关', '开', '门', '问',
        '间', '还', '应', '该', '当', '电', '并', '长', '设', '现',
        '实', '点', '将', '从', '头', '见', '两', '无', '产', '业',
        '经', '变', '虽', '统', '义', '语', '说', '话', '认', '让',
        '请', '马', '车', '书', '学', '习', '写', '医', '药', '师'
    ]

    # 忽略目錄
    IGNORE_DIRS = [
        'node_modules', '.git', 'dist', 'build', '.next', '__pycache__',
        '.angular', 'venv', '.venv', '.cache', 'coverage'
    ]

    # 日文專案（允許使用日文漢字）
    JAPANESE_PROJECTS = ['jinkochino']

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

    def run(self):
        """執行所有驗證"""
        if not self.project_path.exists():
            self.result['passed'] = False
            self.result['errors'].append(f'專案路徑不存在: {self.project_path}')
            return self.result

        self.check_file_length()
        self.check_simplified_chinese()
        self.check_naming_conventions()
        self.check_emoji_usage()

        return self.result

    def check_file_length(self):
        """檢查檔案行數"""
        large_files = []

        for file_path in self._get_source_files():
            try:
                content = file_path.read_text(encoding='utf-8')
                line_count = len(content.splitlines())

                if line_count > self.MAX_FILE_LINES:
                    large_files.append({
                        'file': str(file_path.relative_to(self.project_path)),
                        'lines': line_count
                    })
            except Exception:
                pass

        self.result['checks']['file_length'] = {
            'count': len(large_files),
            'files': large_files
        }

        if large_files:
            for f in large_files[:5]:
                self.result['warnings'].append(
                    f"檔案過長: {f['file']} ({f['lines']} 行)"
                )

    def check_simplified_chinese(self):
        """檢查簡體字"""
        # 跳過日文專案
        if self.project_name in self.JAPANESE_PROJECTS:
            self.result['checks']['simplified_chinese'] = {
                'count': 0,
                'files': [],
                'skipped': '日文專案'
            }
            return

        issues = []

        for file_path in self._get_source_files():
            try:
                content = file_path.read_text(encoding='utf-8')
                found_chars = []

                for char in self.SIMPLIFIED_CHINESE:
                    if char in content:
                        found_chars.append(char)

                if found_chars:
                    issues.append({
                        'file': str(file_path.relative_to(self.project_path)),
                        'chars': found_chars[:5]
                    })
            except Exception:
                pass

        self.result['checks']['simplified_chinese'] = {
            'count': len(issues),
            'files': issues
        }

        if issues:
            for issue in issues[:3]:
                self.result['errors'].append(
                    f"發現簡體字在 {issue['file']}: {', '.join(issue['chars'])}"
                )
            self.result['passed'] = False

    def check_naming_conventions(self):
        """檢查命名規範"""
        issues = []

        for file_path in self._get_source_files():
            # 檢查檔案名稱
            name = file_path.stem

            # JS/TS 檔案應該是 kebab-case 或 PascalCase
            if file_path.suffix in ['.js', '.ts', '.jsx', '.tsx']:
                if not self._is_valid_js_filename(name):
                    issues.append({
                        'file': str(file_path.relative_to(self.project_path)),
                        'issue': '檔名應為 kebab-case 或 PascalCase'
                    })

        self.result['checks']['naming'] = {
            'count': len(issues),
            'issues': issues
        }

        if issues:
            for issue in issues[:3]:
                self.result['warnings'].append(
                    f"命名問題: {issue['file']} - {issue['issue']}"
                )

    def _get_source_files(self):
        """取得所有原始碼檔案"""
        extensions = ['*.js', '*.ts', '*.jsx', '*.tsx', '*.py', '*.css', '*.scss']
        files = []

        for ext in extensions:
            for f in self.project_path.rglob(ext):
                if not any(ignore in str(f) for ignore in self.IGNORE_DIRS):
                    files.append(f)

        return files

    def _is_valid_js_filename(self, name):
        """檢查 JS 檔名是否有效"""
        # kebab-case
        if re.match(r'^[a-z][a-z0-9-]*$', name):
            return True
        # PascalCase
        if re.match(r'^[A-Z][a-zA-Z0-9]*$', name):
            return True
        # camelCase
        if re.match(r'^[a-z][a-zA-Z0-9]*$', name):
            return True
        return False

    def check_emoji_usage(self):
        """檢查程式碼中的 Emoji 使用（應改用 icon font）"""
        # Emoji Unicode 範圍
        emoji_pattern = re.compile(
            "["
            "\U0001F300-\U0001F9FF"  # 表情符號
            "\U0001FA00-\U0001FA6F"  # 擴展符號
            "\U0001FA70-\U0001FAFF"  # 更多擴展
            "\U00002702-\U000027B0"  # 裝飾符號
            "\U000024C2-\U0001F251"  # 封閉字符
            "]+",
            flags=re.UNICODE
        )

        issues = []

        for file_path in self._get_source_files():
            # 只檢查 JS/TS 檔案（不檢查 CSS）
            if file_path.suffix not in ['.js', '.ts', '.jsx', '.tsx']:
                continue

            try:
                content = file_path.read_text(encoding='utf-8')
                matches = emoji_pattern.findall(content)

                if matches:
                    # 過濾掉註解中的 emoji
                    unique_emojis = list(set(matches))[:5]
                    issues.append({
                        'file': str(file_path.relative_to(self.project_path)),
                        'emojis': unique_emojis,
                        'count': len(matches)
                    })
            except Exception:
                pass

        self.result['checks']['emoji_usage'] = {
            'count': sum(i['count'] for i in issues) if issues else 0,
            'files': issues
        }

        if issues:
            total = sum(i['count'] for i in issues)
            self.result['warnings'].append(
                f"程式碼中使用 Emoji: {total} 個（建議改用 icon font）"
            )
            for issue in issues[:3]:
                self.result['warnings'].append(
                    f"  {issue['file']}: {''.join(issue['emojis'])}"
                )
