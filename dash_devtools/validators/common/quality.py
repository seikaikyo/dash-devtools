"""
程式碼品質驗證器（通用）

檢查項目：
1. 檔案行數限制 (500 行)
2. 命名規範
3. 中文註解
4. 禁止簡體字
5. 禁止 Emoji（應使用 icon font）
"""

import re
from fnmatch import fnmatch
from pathlib import Path


class QualityValidator:
    """程式碼品質驗證器"""

    name = 'quality'

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

    # 中國用語禁用詞（應替換為台灣用語）
    # 來源: pjchender/cn2tw4programmer + 自訂補充
    BANNED_CN_TERMS = {
        # -- 高頻日常用語 --
        '崗位': '職位',
        '人才市場': '人力銀行',
        '博客': '部落格',
        '視頻': '影片',
        '信息': '訊息',
        '搜索': '搜尋',
        '用戶': '使用者',
        '設置': '設定',
        '配置': '設定',
        '項目': '專案',
        '默認': '預設',
        '響應': '回應',
        # -- 技術術語 --
        '軟件': '軟體',
        '硬件': '硬體',
        '網絡': '網路',
        '服務器': '伺服器',
        '數據': '資料',
        '數據庫': '資料庫',
        '數組': '陣列',
        '代碼': '程式碼',
        '源代碼': '原始碼',
        '算法': '演算法',
        '緩存': '快取',
        '內存': '記憶體',
        '線程': '執行緒',
        '進程': '程序',
        '端口': '連接埠',
        '接口': '介面',
        '字段': '欄位',
        '文件夾': '資料夾',
        '操作系統': '作業系統',
        '調試': '除錯',
        '編程': '程式設計',
        '程序員': '工程師',
        '變量': '變數',
        '常量': '常數',
        '加載': '載入',
        '創建': '建立',
        '刷新': '重新整理',
        '導入': '匯入',
        '導出': '匯出',
        '運行': '執行',
        '調用': '呼叫',
        '返回': '回傳',
        '遠程': '遠端',
        '集群': '叢集',
        '隊列': '佇列',
        '窗口': '視窗',
        '菜單': '選單',
        '屏幕': '螢幕',
        '鏈接': '連結',
        '登陸': '登入',
    }

    # 忽略目錄
    IGNORE_DIRS = [
        'node_modules', '.git', 'dist', 'build', '.next', '__pycache__',
        '.angular', 'venv', '.venv', '.cache', 'coverage',
        'playwright-report'
    ]

    # 日文專案（允許使用日文漢字）
    JAPANESE_PROJECTS = ['jinkochino']

    def __init__(self, project_path):
        self.project_path = Path(project_path)
        self.project_name = self.project_path.name
        self.scanignore = self._parse_scanignore()
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
        self.check_banned_cn_terms()
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
                rel_path = str(file_path.relative_to(self.project_path))

                # 檢查 [pattern:簡體字] 排除
                if self._is_pattern_ignored(rel_path, '簡體字'):
                    continue

                content = file_path.read_text(encoding='utf-8')
                found_chars = []

                for char in self.SIMPLIFIED_CHINESE:
                    if char in content:
                        found_chars.append(char)

                if found_chars:
                    issues.append({
                        'file': rel_path,
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

    def check_banned_cn_terms(self):
        """檢查中國用語禁用詞"""
        if self.project_name in self.JAPANESE_PROJECTS:
            return

        issues = []

        for file_path in self._get_source_files():
            try:
                rel_path = str(file_path.relative_to(self.project_path))

                if self._is_pattern_ignored(rel_path, '中國用語'):
                    continue

                content = file_path.read_text(encoding='utf-8')
                found_terms = []

                for cn_term, tw_term in self.BANNED_CN_TERMS.items():
                    if cn_term in content:
                        found_terms.append(f"{cn_term}→{tw_term}")

                if found_terms:
                    issues.append({
                        'file': rel_path,
                        'terms': found_terms
                    })
            except Exception:
                pass

        self.result['checks']['banned_cn_terms'] = {
            'count': len(issues),
            'files': issues
        }

        if issues:
            for issue in issues[:3]:
                self.result['warnings'].append(
                    f"發現中國用語在 {issue['file']}: {', '.join(issue['terms'])}"
                )

    def check_naming_conventions(self):
        """檢查命名規範"""
        issues = []

        for file_path in self._get_source_files():
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

    def check_emoji_usage(self):
        """檢查程式碼中的 Emoji 使用（應改用 icon font）"""
        # 精確的 emoji Unicode 範圍（避免誤判中文字）
        emoji_pattern = re.compile(
            "["
            "\U0001F300-\U0001F5FF"  # 雜項符號和象形文字
            "\U0001F600-\U0001F64F"  # 表情符號
            "\U0001F680-\U0001F6FF"  # 交通和地圖符號
            "\U0001F900-\U0001F9FF"  # 補充符號和象形文字
            "\U0001FA00-\U0001FA6F"  # 棋類符號
            "\U0001FA70-\U0001FAFF"  # 符號和象形文字擴展-A
            "\U00002600-\U000026FF"  # 雜項符號
            "\U00002700-\U000027BF"  # 裝飾符號
            "]+",
            flags=re.UNICODE
        )

        issues = []

        for file_path in self._get_source_files():
            # 檢查 JS/TS/HTML 檔案（不檢查 CSS）
            if file_path.suffix not in ['.js', '.ts', '.jsx', '.tsx', '.html']:
                continue

            try:
                content = file_path.read_text(encoding='utf-8')
                matches = emoji_pattern.findall(content)

                if matches:
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

    def _is_scanignored(self, file_path):
        """檢查檔案是否被 .scanignore 全排除"""
        rel_path = str(file_path.relative_to(self.project_path))
        for pattern in self.scanignore['paths']:
            # 目錄排除（以 / 結尾）
            if pattern.endswith('/'):
                if rel_path.startswith(pattern) or f'/{pattern}' in f'/{rel_path}':
                    return True
            # 精確檔名比對
            elif '/' in pattern:
                if rel_path == pattern:
                    return True
            else:
                # 只比對檔名部分
                if file_path.name == pattern:
                    return True
        return False

    def _is_pattern_ignored(self, rel_path, pattern_name):
        """檢查檔案是否被 .scanignore 的特定 pattern 排除"""
        for p_name, p_glob in self.scanignore['pattern_paths']:
            if p_name == pattern_name:
                if fnmatch(rel_path, p_glob):
                    return True
                if rel_path == p_glob:
                    return True
        return False

    def _get_source_files(self):
        """取得所有原始碼檔案"""
        extensions = ['*.js', '*.ts', '*.jsx', '*.tsx', '*.py', '*.css', '*.scss', '*.html']
        files = []

        for ext in extensions:
            for f in self.project_path.rglob(ext):
                if any(ignore in str(f) for ignore in self.IGNORE_DIRS):
                    continue
                if self._is_scanignored(f):
                    continue
                files.append(f)

        return files

    def _is_valid_js_filename(self, name):
        """檢查 JS 檔名是否有效"""
        # 允許設定檔名（含點號）
        config_patterns = [
            'vite.config', 'tailwind.config', 'postcss.config',
            'eslint.config', 'prettier.config', 'jest.config',
            'webpack.config', 'rollup.config', 'tsconfig',
            'karma.conf', 'playwright.config', 'vitest.config',
            'babel.config', 'nuxt.config', 'next.config',
            'cypress.config', 'angular.json'
        ]
        if any(name.startswith(p) for p in config_patterns):
            return True

        # kebab-case 含 dot-separated 後綴
        # 如 xxx.component, xxx.service.spec, xxx.e2e 等
        if re.match(r'^[a-z][a-z0-9-]*(\.[a-z][a-z0-9-]*)*$', name):
            return True
        # PascalCase
        if re.match(r'^[A-Z][a-zA-Z0-9]*$', name):
            return True
        # camelCase
        if re.match(r'^[a-z][a-zA-Z0-9]*$', name):
            return True
        return False
