"""
Node.js 後端驗證器

檢查項目：
1. API 回應格式
2. 錯誤處理
3. 認證中介層
4. 稽核日誌
5. Vercel Serverless 設定
"""

import re
import json
from pathlib import Path


class NodejsValidator:
    """Node.js 後端驗證器"""

    name = 'nodejs'

    # 忽略目錄
    IGNORE_DIRS = [
        'node_modules', '.git', 'dist', 'build', '.next', '.vercel'
    ]

    def __init__(self, project_path):
        self.project_path = Path(project_path)
        self.project_name = self.project_path.name
        self.api_path = self.project_path / 'api'
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

        self.check_api_structure()
        self.check_response_format()
        self.check_error_handling()
        self.check_auth_middleware()
        self.check_vercel_config()

        return self.result

    def check_api_structure(self):
        """檢查 API 目錄結構"""
        has_api_dir = self.api_path.exists()

        if has_api_dir:
            api_files = list(self.api_path.rglob('*.js'))
            self.result['checks']['api_structure'] = {
                'has_api_dir': True,
                'api_count': len(api_files)
            }
        else:
            self.result['checks']['api_structure'] = {
                'has_api_dir': False,
                'skipped': '無 api 目錄'
            }

    def check_response_format(self):
        """檢查 API 回應格式是否符合規範"""
        if not self.api_path.exists():
            return

        issues = []
        good_patterns = 0

        # 標準回應格式: { success: boolean, data?: T, error?: { code, message } }
        success_pattern = r'success:\s*(true|false)'
        json_response = r'res\.json\s*\('

        for file_path in self.api_path.rglob('*.js'):
            if self._should_skip(file_path):
                continue
            try:
                content = file_path.read_text(encoding='utf-8')
                rel_path = str(file_path.relative_to(self.project_path))

                # 檢查是否有 res.json()
                json_calls = len(re.findall(json_response, content))
                success_calls = len(re.findall(success_pattern, content))

                if json_calls > 0:
                    if success_calls < json_calls:
                        issues.append({
                            'file': rel_path,
                            'issue': f'回應格式不一致 ({json_calls} 個回應，{success_calls} 個使用 success)'
                        })
                    else:
                        good_patterns += json_calls

            except Exception:
                pass

        self.result['checks']['response_format'] = {
            'issues_count': len(issues),
            'good_patterns': good_patterns,
            'issues': issues
        }

        if issues:
            for issue in issues[:3]:
                self.result['warnings'].append(f"{issue['file']}: {issue['issue']}")

    def check_error_handling(self):
        """檢查錯誤處理"""
        if not self.api_path.exists():
            return

        issues = []

        # 檢查是否有 try-catch
        try_catch_pattern = r'try\s*\{'
        catch_pattern = r'catch\s*\([^)]*\)\s*\{'

        for file_path in self.api_path.rglob('*.js'):
            if self._should_skip(file_path):
                continue
            try:
                content = file_path.read_text(encoding='utf-8')
                rel_path = str(file_path.relative_to(self.project_path))

                try_count = len(re.findall(try_catch_pattern, content))
                catch_count = len(re.findall(catch_pattern, content))

                # 如果有 async function 但沒有 try-catch
                has_async = 'async ' in content
                if has_async and try_count == 0:
                    issues.append({
                        'file': rel_path,
                        'issue': 'async 函數缺少 try-catch 錯誤處理'
                    })

                # 檢查 catch 是否有正確處理錯誤
                if catch_count > 0:
                    # 檢查是否有 console.error 或記錄錯誤
                    has_error_log = 'console.error' in content or 'logSystemAudit' in content
                    if not has_error_log:
                        issues.append({
                            'file': rel_path,
                            'issue': '錯誤處理缺少日誌記錄'
                        })

            except Exception:
                pass

        self.result['checks']['error_handling'] = {
            'count': len(issues),
            'issues': issues
        }

        for issue in issues[:5]:
            self.result['warnings'].append(f"{issue['file']}: {issue['issue']}")

    def check_auth_middleware(self):
        """檢查認證中介層"""
        if not self.api_path.exists():
            return

        issues = []
        protected_count = 0

        # 檢查是否使用 withApiAuth
        auth_pattern = r'withApiAuth'

        for file_path in self.api_path.rglob('*.js'):
            if self._should_skip(file_path):
                continue
            try:
                content = file_path.read_text(encoding='utf-8')
                rel_path = str(file_path.relative_to(self.project_path))

                has_auth = auth_pattern in content

                # 判斷是否為需要認證的 API
                is_public = any(pub in rel_path for pub in ['health', 'public', 'webhook'])

                if has_auth:
                    protected_count += 1
                elif not is_public:
                    # 非公開 API 但沒有認證
                    issues.append({
                        'file': rel_path,
                        'issue': '可能缺少認證保護 (withApiAuth)'
                    })

            except Exception:
                pass

        self.result['checks']['auth_middleware'] = {
            'protected_count': protected_count,
            'issues_count': len(issues),
            'issues': issues
        }

        if issues:
            self.result['warnings'].append(f'{len(issues)} 個 API 可能缺少認證保護')

    def check_vercel_config(self):
        """檢查 Vercel 設定"""
        vercel_json = self.project_path / 'vercel.json'

        if not vercel_json.exists():
            self.result['checks']['vercel_config'] = {'skipped': '無 vercel.json'}
            return

        try:
            config = json.loads(vercel_json.read_text(encoding='utf-8'))

            has_functions = 'functions' in config
            has_routes = 'routes' in config or 'rewrites' in config

            self.result['checks']['vercel_config'] = {
                'has_functions': has_functions,
                'has_routes': has_routes,
                'config': config
            }

            # 檢查函數設定
            if has_functions:
                for func_path, func_config in config.get('functions', {}).items():
                    if func_config.get('maxDuration', 10) > 60:
                        self.result['warnings'].append(
                            f"函數 {func_path} 設定 maxDuration > 60s (可能影響成本)"
                        )

        except Exception as e:
            self.result['checks']['vercel_config'] = {
                'error': str(e)
            }
            self.result['warnings'].append('vercel.json 格式錯誤')

    def _should_skip(self, file_path):
        """檢查是否應該跳過該檔案"""
        return any(ignore in str(file_path) for ignore in self.IGNORE_DIRS)
