"""
安全性驗證器（通用）

檢查內容：
1. API Key / Token 外洩
2. 密碼硬編碼
3. .env 檔案提交
4. 敏感資料暴露
"""

import re
from fnmatch import fnmatch
from pathlib import Path

from ...path_filters import is_gitignored, is_in_ignored_dir, is_under, parse_gitignore


class SecurityValidator:
    """安全性驗證器"""

    name = 'security'

    # 敏感資料正則表達式
    # 要求 value 必須在 quote 內，避免把 `token = func_call()` 這類函式呼叫誤判
    SENSITIVE_PATTERNS = [
        (r'(?i)(api[_-]?key|apikey)\s*[=:]\s*["\'][a-zA-Z0-9_=/+\-]{20,}["\']', 'API Key'),
        (r'(?i)(secret|token)\s*[=:]\s*["\'][a-zA-Z0-9_=/+\-]{20,}["\']', 'Secret/Token'),
        (r'(?i)password\s*[=:]\s*["\'][^"\']+["\']', '密碼'),
        (r'sk-[a-zA-Z0-9]{48}', 'OpenAI API Key'),
        (r'sk_live_[a-zA-Z0-9]{24,}', 'Stripe Live Key'),
        (r'ghp_[a-zA-Z0-9]{36}', 'GitHub Token'),
        # Clerk 只檢查 secret key (sk_)，publishable key (pk_) 是公開的
        (r'CLERK_SECRET_KEY\s*=\s*["\']sk_[a-zA-Z0-9_-]{20,}["\']', 'Clerk Secret Key'),
        # Neon Database API Key (napi_開頭，64字元)
        (r'napi_[a-zA-Z0-9]{60,}', 'Neon API Key'),
        # PostgreSQL 連線字串 (含密碼)
        (r'postgres(?:ql)?://[^:<]+:[^@<]+@[^\s"\']+', 'PostgreSQL 連線字串'),
        # Neon PostgreSQL 專用格式
        (r'npg_[a-zA-Z0-9]{10,}', 'Neon PostgreSQL 密碼'),
    ]

    # 敏感檔案
    SENSITIVE_FILES = [
        '.env',
        '.env.local',
        '.env.production',
        'credentials.json',
        'service-account.json',
        'private.key',
        '*.pem',
    ]

    # 忽略目錄（含 tests / __tests__ — 測試 fixture 常用 fake secret，會誤判）
    IGNORE_DIRS = [
        'node_modules', '.git', 'dist', 'build', '.next', '__pycache__',
        '.angular', 'venv', '.venv', '.cache', 'coverage',
        'tests', '__tests__', 'test', 'spec', '__specs__',
    ]

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

        self.check_sensitive_files()
        self.check_hardcoded_secrets()
        self.check_gitignore()

        return self.result

    def check_sensitive_files(self):
        """檢查敏感檔案是否被追蹤"""
        issues = []

        # 找出所有巢狀的 git repo (要跳過)
        nested_repos = self._get_nested_repos()

        for pattern in self.SENSITIVE_FILES:
            if '*' in pattern:
                files = list(self.project_path.rglob(pattern))
            else:
                files = [self.project_path / pattern]

            for f in files:
                if f.exists() and f.is_file():
                    if self._should_skip(f, nested_repos):
                        continue
                    if not self._is_gitignored(f):
                        issues.append(str(f.relative_to(self.project_path)))

        self.result['checks']['sensitive_files'] = {
            'count': len(issues),
            'files': issues
        }

        if issues:
            self.result['passed'] = False
            for f in issues:
                self.result['errors'].append(f'敏感檔案未忽略: {f}')

    def check_hardcoded_secrets(self):
        """檢查硬編碼的敏感資料"""
        issues = []

        for file_path in self._get_source_files():
            try:
                content = file_path.read_text(encoding='utf-8')
                rel_path = str(file_path.relative_to(self.project_path))

                # 全排除檢查
                if self._is_scanignored(rel_path, None):
                    continue

                for pattern, desc in self.SENSITIVE_PATTERNS:
                    # 特定 pattern 排除檢查
                    if self._is_scanignored(rel_path, desc):
                        continue
                    matches = re.findall(pattern, content)
                    if matches:
                        issues.append({
                            'file': rel_path,
                            'type': desc,
                            'count': len(matches)
                        })
            except Exception:
                pass

        self.result['checks']['hardcoded_secrets'] = {
            'count': len(issues),
            'issues': issues
        }

        if issues:
            self.result['passed'] = False
            for issue in issues:
                self.result['errors'].append(
                    f"發現 {issue['type']} 在 {issue['file']}"
                )

    def check_gitignore(self):
        """檢查 .gitignore 設定"""
        gitignore = self.project_path / '.gitignore'
        required_patterns = ['.env', 'node_modules', '*.log']
        missing = []

        if gitignore.exists():
            content = gitignore.read_text(encoding='utf-8')
            for pattern in required_patterns:
                if pattern not in content:
                    missing.append(pattern)
        else:
            missing = required_patterns

        self.result['checks']['gitignore'] = {
            'exists': gitignore.exists(),
            'missing_patterns': missing
        }

        if missing:
            for pattern in missing:
                self.result['warnings'].append(f'.gitignore 缺少: {pattern}')

    def _get_nested_repos(self):
        """取得巢狀 git repo 路徑"""
        nested_repos = []
        for git_dir in self.project_path.rglob('.git'):
            if git_dir.parent != self.project_path:
                nested_repos.append(str(git_dir.parent))
        return nested_repos

    def _should_skip(self, file_path, nested_repos):
        """檢查是否應該跳過該檔案"""
        file_str = str(file_path)
        # 跳過巢狀 git repo
        if any(is_under(file_str, repo) for repo in nested_repos):
            return True
        # 跳過忽略目錄（比對路徑元件，不是子字串）
        if is_in_ignored_dir(file_path, self.project_path, self.IGNORE_DIRS):
            return True
        return False

    def _get_source_files(self):
        """取得所有原始碼檔案"""
        extensions = ['*.js', '*.ts', '*.jsx', '*.tsx', '*.py', '*.json', '*.yaml', '*.yml']
        files = []
        nested_repos = self._get_nested_repos()

        for ext in extensions:
            for f in self.project_path.rglob(ext):
                if not self._should_skip(f, nested_repos):
                    files.append(f)

        return files

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

    def _is_scanignored(self, rel_path, pattern_name):
        """檢查檔案是否在 .scanignore 中"""
        # 全排除路徑
        for glob_pattern in self.scanignore['paths']:
            if glob_pattern.endswith('/'):
                if rel_path.startswith(glob_pattern) or rel_path.startswith(glob_pattern.rstrip('/')):
                    return True
            if fnmatch(rel_path, glob_pattern):
                return True
            if rel_path.startswith(glob_pattern.rstrip('/') + '/'):
                return True

        # 特定 pattern 排除
        if pattern_name:
            for p_name, p_glob in self.scanignore['pattern_paths']:
                if p_name == pattern_name:
                    if fnmatch(rel_path, p_glob):
                        return True
                    if rel_path == p_glob:
                        return True

        return False

    def _is_gitignored(self, file_path):
        """檢查檔案是否在 .gitignore 中（gitignore 語意，不是子字串）"""
        rel_path = str(file_path.relative_to(self.project_path))
        return is_gitignored(rel_path, parse_gitignore(self.project_path))
