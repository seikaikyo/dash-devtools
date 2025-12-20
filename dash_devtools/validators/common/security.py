"""
安全性驗證器（通用）

檢查項目：
1. API Key / Token 外洩
2. 密碼硬編碼
3. .env 檔案提交
4. 敏感資料暴露
"""

import re
from pathlib import Path


class SecurityValidator:
    """安全性驗證器"""

    name = 'security'

    # 敏感資料正則表達式
    SENSITIVE_PATTERNS = [
        (r'(?i)(api[_-]?key|apikey)\s*[=:]\s*["\']?[a-zA-Z0-9_-]{20,}', 'API Key'),
        (r'(?i)(secret|token)\s*[=:]\s*["\']?[a-zA-Z0-9_-]{20,}', 'Secret/Token'),
        (r'(?i)password\s*[=:]\s*["\'][^"\']+["\']', '密碼'),
        (r'sk-[a-zA-Z0-9]{48}', 'OpenAI API Key'),
        (r'sk_live_[a-zA-Z0-9]{24,}', 'Stripe Live Key'),
        (r'ghp_[a-zA-Z0-9]{36}', 'GitHub Token'),
        # Clerk 只檢查 secret key (sk_)，publishable key (pk_) 是公開的
        (r'CLERK_SECRET_KEY\s*=\s*["\']?sk_[a-zA-Z0-9_-]{20,}', 'Clerk Secret Key'),
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

    # 忽略目錄
    IGNORE_DIRS = [
        'node_modules', '.git', 'dist', 'build', '.next', '__pycache__',
        '.angular', 'venv', '.venv', '.cache', 'coverage'
    ]

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

                for pattern, desc in self.SENSITIVE_PATTERNS:
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
        if any(file_str.startswith(repo) for repo in nested_repos):
            return True
        # 跳過忽略目錄
        if any(ignore in file_str for ignore in self.IGNORE_DIRS):
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

    def _is_gitignored(self, file_path):
        """檢查檔案是否在 .gitignore 中"""
        gitignore = self.project_path / '.gitignore'
        if not gitignore.exists():
            return False

        content = gitignore.read_text(encoding='utf-8')
        rel_path = str(file_path.relative_to(self.project_path))

        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if line in rel_path or rel_path.startswith(line):
                return True

        return False
