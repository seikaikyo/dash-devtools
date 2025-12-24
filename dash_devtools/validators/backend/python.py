"""
Python 後端驗證器 v2.0

支援：
- FastAPI 專案結構驗證
- Ruff 整合 (lint + format)
- 程式碼風格檢查

檢查項目：
1. FastAPI 結構 (main.py, routers/, etc.)
2. Ruff lint/format 檢查
3. 依賴管理 (requirements.txt / pyproject.toml)
4. 模型權重檔案
5. 虛擬環境設定
"""

import re
import subprocess
from pathlib import Path


class PythonValidator:
    """Python 後端驗證器 (支援 FastAPI + Ruff)"""

    name = 'python'

    IGNORE_DIRS = [
        '__pycache__', '.git', 'venv', '.venv', 'env', '.env',
        'dist', 'build', '.eggs', '*.egg-info', '.pytest_cache'
    ]

    MODEL_EXTENSIONS = ['.pt', '.pth', '.onnx', '.h5', '.pkl', '.joblib', '.safetensors']

    AI_PACKAGES = {
        'torch': 'PyTorch',
        'tensorflow': 'TensorFlow',
        'ultralytics': 'YOLO',
        'transformers': 'Hugging Face Transformers',
        'opencv-python': 'OpenCV',
        'scikit-learn': 'Scikit-learn',
    }

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
        # 偵測框架
        self.framework = self._detect_framework()

    def _detect_framework(self) -> str | None:
        """偵測 Python 框架"""
        requirements = self.project_path / 'requirements.txt'
        pyproject = self.project_path / 'pyproject.toml'

        content = ''
        if requirements.exists():
            content = requirements.read_text(encoding='utf-8').lower()
        elif pyproject.exists():
            content = pyproject.read_text(encoding='utf-8').lower()

        if 'fastapi' in content:
            return 'fastapi'
        if 'flask' in content:
            return 'flask'
        if 'django' in content:
            return 'django'
        if 'streamlit' in content:
            return 'streamlit'
        return None

    def run(self):
        """執行所有驗證"""
        if not self.project_path.exists():
            self.result['passed'] = False
            self.result['errors'].append(f'專案路徑不存在: {self.project_path}')
            return self.result

        # 框架特定檢查
        if self.framework == 'fastapi':
            self.check_fastapi_structure()

        # 通用檢查
        self.check_ruff()
        self.check_dependencies()
        self.check_model_files()
        self.check_virtual_env()

        return self.result

    def check_fastapi_structure(self):
        """檢查 FastAPI 專案結構"""
        issues = []

        # 檢查入口點
        main_py = self.project_path / 'main.py'
        app_main_py = self.project_path / 'app' / 'main.py'

        has_main = main_py.exists() or app_main_py.exists()
        main_file = main_py if main_py.exists() else app_main_py

        if not has_main:
            issues.append('缺少 main.py 入口點')

        # 檢查 main.py 內容
        if has_main:
            try:
                content = main_file.read_text(encoding='utf-8')

                # 檢查 FastAPI 實例
                if 'FastAPI()' not in content and 'FastAPI(' not in content:
                    issues.append('main.py 中未找到 FastAPI 實例')

                # 檢查 CORS 設定
                if 'CORSMiddleware' not in content:
                    issues.append('建議加入 CORS 設定')

                # 檢查全域錯誤處理
                if '@app.exception_handler' not in content and 'exception_handler' not in content:
                    issues.append('建議加入全域錯誤處理')

            except Exception:
                pass

        # 檢查 requirements.txt
        requirements = self.project_path / 'requirements.txt'
        if not requirements.exists():
            issues.append('缺少 requirements.txt')

        # 檢查目錄結構
        app_dir = self.project_path / 'app'
        routers_dir = app_dir / 'routers' if app_dir.exists() else self.project_path / 'routers'

        self.result['checks']['fastapi_structure'] = {
            'has_main': has_main,
            'has_requirements': requirements.exists(),
            'has_app_dir': app_dir.exists(),
            'has_routers': routers_dir.exists(),
            'issues': issues
        }

        for issue in issues:
            if '缺少' in issue:
                self.result['errors'].append(f'FastAPI: {issue}')
            else:
                self.result['warnings'].append(f'FastAPI: {issue}')

    def check_ruff(self):
        """執行 Ruff lint 和 format 檢查"""
        # 檢查 ruff 是否安裝
        try:
            result = subprocess.run(
                ['ruff', '--version'],
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                self.result['checks']['ruff'] = {'skipped': 'Ruff 未安裝'}
                return
        except FileNotFoundError:
            self.result['checks']['ruff'] = {'skipped': 'Ruff 未安裝'}
            return

        lint_issues = []
        format_issues = []

        # 執行 ruff check
        try:
            result = subprocess.run(
                ['ruff', 'check', str(self.project_path), '--output-format=json'],
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.stdout:
                import json
                try:
                    issues = json.loads(result.stdout)
                    for issue in issues[:10]:  # 只取前 10 個
                        lint_issues.append({
                            'file': issue.get('filename', ''),
                            'line': issue.get('location', {}).get('row', 0),
                            'code': issue.get('code', ''),
                            'message': issue.get('message', '')
                        })
                except json.JSONDecodeError:
                    pass

        except subprocess.TimeoutExpired:
            self.result['checks']['ruff'] = {'error': 'Ruff check 執行逾時'}
            return
        except Exception as e:
            self.result['checks']['ruff'] = {'error': str(e)}
            return

        # 執行 ruff format --check
        try:
            result = subprocess.run(
                ['ruff', 'format', '--check', str(self.project_path)],
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode != 0:
                # 解析需要格式化的檔案
                for line in result.stdout.splitlines():
                    if line.strip().startswith('Would reformat'):
                        file_name = line.replace('Would reformat', '').strip()
                        format_issues.append(file_name)
                    elif line.strip() and not line.startswith('Oh no!') and not line.startswith('1 file'):
                        # 其他格式的輸出
                        format_issues.append(line.strip())

        except subprocess.TimeoutExpired:
            pass
        except Exception:
            pass

        self.result['checks']['ruff'] = {
            'lint_issues': len(lint_issues),
            'format_issues': len(format_issues),
            'lint_details': lint_issues[:5],
            'format_details': format_issues[:5]
        }

        if lint_issues:
            self.result['warnings'].append(f'Ruff lint: {len(lint_issues)} 個問題')
            for issue in lint_issues[:3]:
                self.result['warnings'].append(
                    f"  {issue['file']}:{issue['line']} [{issue['code']}] {issue['message'][:50]}"
                )

        if format_issues:
            self.result['warnings'].append(f'Ruff format: {len(format_issues)} 個檔案需要格式化')

    def check_dependencies(self):
        """檢查依賴管理"""
        requirements = self.project_path / 'requirements.txt'
        pyproject = self.project_path / 'pyproject.toml'
        setup_py = self.project_path / 'setup.py'

        has_deps = requirements.exists() or pyproject.exists() or setup_py.exists()

        self.result['checks']['dependencies'] = {
            'has_requirements': requirements.exists(),
            'has_pyproject': pyproject.exists(),
            'has_setup_py': setup_py.exists()
        }

        if not has_deps:
            self.result['warnings'].append('缺少依賴管理檔案 (requirements.txt 或 pyproject.toml)')

        # 檢查 requirements.txt 版本鎖定
        if requirements.exists():
            content = requirements.read_text(encoding='utf-8')
            lines = [l.strip() for l in content.splitlines() if l.strip() and not l.startswith('#')]
            unpinned = []

            for line in lines:
                if line.startswith('-') or line.startswith('git+') or '://' in line:
                    continue
                if '==' not in line and '>=' not in line and '<=' not in line:
                    pkg_name = re.split(r'[<>=\[]', line)[0]
                    unpinned.append(pkg_name)

            if unpinned:
                self.result['checks']['dependencies']['unpinned'] = unpinned[:5]
                self.result['warnings'].append(
                    f'部分依賴未鎖定版本: {", ".join(unpinned[:3])}...'
                )

    def check_model_files(self):
        """檢查模型權重檔案"""
        issues = []

        for ext in self.MODEL_EXTENSIONS:
            for f in self.project_path.rglob(f'*{ext}'):
                if self._should_skip(f):
                    continue
                if not self._is_gitignored(f):
                    issues.append({
                        'file': str(f.relative_to(self.project_path)),
                        'type': ext
                    })

        self.result['checks']['model_files'] = {
            'count': len(issues),
            'files': issues
        }

        if issues:
            self.result['warnings'].append(
                f'模型權重檔案未忽略: {len(issues)} 個 (建議加入 .gitignore)'
            )

    def check_virtual_env(self):
        """檢查虛擬環境設定"""
        venv_dirs = ['venv', '.venv', 'env', '.env']
        has_venv = any((self.project_path / d).exists() for d in venv_dirs)

        gitignore = self.project_path / '.gitignore'
        venv_ignored = False

        if gitignore.exists():
            content = gitignore.read_text(encoding='utf-8')
            venv_ignored = any(d in content for d in venv_dirs)

        self.result['checks']['virtual_env'] = {
            'has_venv': has_venv,
            'venv_ignored': venv_ignored
        }

        if has_venv and not venv_ignored:
            self.result['warnings'].append('虛擬環境目錄未加入 .gitignore')

    def _should_skip(self, file_path):
        """檢查是否應該跳過該檔案"""
        file_str = str(file_path)
        return any(ignore in file_str for ignore in self.IGNORE_DIRS)

    def _is_gitignored(self, file_path):
        """檢查檔案是否在 .gitignore 中"""
        gitignore = self.project_path / '.gitignore'
        if not gitignore.exists():
            return False

        content = gitignore.read_text(encoding='utf-8')
        rel_path = str(file_path.relative_to(self.project_path))

        ext = file_path.suffix
        if f'*{ext}' in content:
            return True

        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if line in rel_path or rel_path.startswith(line):
                return True

        return False


def run_ruff_check(project_path) -> dict:
    """獨立函數：執行 Ruff 檢查（供 Hook 使用）"""
    try:
        # Lint 檢查
        lint_result = subprocess.run(
            ['ruff', 'check', str(project_path)],
            capture_output=True,
            text=True,
            timeout=60
        )

        # Format 檢查
        format_result = subprocess.run(
            ['ruff', 'format', '--check', str(project_path)],
            capture_output=True,
            text=True,
            timeout=60
        )

        lint_passed = lint_result.returncode == 0
        format_passed = format_result.returncode == 0

        return {
            'passed': lint_passed and format_passed,
            'lint_passed': lint_passed,
            'format_passed': format_passed,
            'lint_output': lint_result.stdout[:500] if lint_result.stdout else '',
            'format_output': format_result.stdout[:500] if format_result.stdout else ''
        }

    except FileNotFoundError:
        return {'passed': True, 'skipped': 'Ruff 未安裝'}
    except subprocess.TimeoutExpired:
        return {'passed': False, 'error': '執行逾時'}
    except Exception as e:
        return {'passed': False, 'error': str(e)}
