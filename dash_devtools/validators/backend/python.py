"""
Python 後端驗證器

檢查項目：
1. 程式碼風格 (PEP 8)
2. 依賴管理 (requirements.txt / pyproject.toml)
3. 模型權重檔案 (.pt, .pth, .onnx)
4. 虛擬環境設定
5. AI/ML 套件相容性
"""

import re
from pathlib import Path


class PythonValidator:
    """Python 後端驗證器"""

    name = 'python'

    # 忽略目錄
    IGNORE_DIRS = [
        '__pycache__', '.git', 'venv', '.venv', 'env', '.env',
        'dist', 'build', '.eggs', '*.egg-info', '.pytest_cache'
    ]

    # 模型權重副檔名（應加入 .gitignore）
    MODEL_EXTENSIONS = ['.pt', '.pth', '.onnx', '.h5', '.pkl', '.joblib', '.safetensors']

    # 常見 AI/ML 套件
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

    def run(self):
        """執行所有驗證"""
        if not self.project_path.exists():
            self.result['passed'] = False
            self.result['errors'].append(f'專案路徑不存在: {self.project_path}')
            return self.result

        self.check_dependencies()
        self.check_model_files()
        self.check_virtual_env()
        self.check_code_style()
        self.check_ai_packages()

        return self.result

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

        # 檢查 requirements.txt 是否有版本鎖定
        if requirements.exists():
            content = requirements.read_text(encoding='utf-8')
            lines = [l.strip() for l in content.splitlines() if l.strip() and not l.startswith('#')]
            unpinned = []

            for line in lines:
                # 排除 -e, git+, http:// 等特殊格式
                if line.startswith('-') or line.startswith('git+') or '://' in line:
                    continue
                # 檢查是否有版本指定
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
                # 檢查是否在 .gitignore 中
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
            for issue in issues[:3]:
                self.result['warnings'].append(f"  • {issue['file']}")

    def check_virtual_env(self):
        """檢查虛擬環境設定"""
        venv_dirs = ['venv', '.venv', 'env', '.env']
        has_venv = any((self.project_path / d).exists() for d in venv_dirs)

        # 檢查 .gitignore 是否忽略虛擬環境
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

    def check_code_style(self):
        """檢查程式碼風格"""
        issues = []

        for file_path in self.project_path.rglob('*.py'):
            if self._should_skip(file_path):
                continue
            try:
                content = file_path.read_text(encoding='utf-8')
                rel_path = str(file_path.relative_to(self.project_path))
                lines = content.splitlines()

                # 檢查行長度
                long_lines = [i+1 for i, line in enumerate(lines) if len(line) > 120]
                if long_lines:
                    issues.append({
                        'file': rel_path,
                        'issue': f'行過長 (> 120 字元): 第 {long_lines[0]} 行等 {len(long_lines)} 處'
                    })

                # 檢查 import *
                if 'from ' in content and ' import *' in content:
                    issues.append({
                        'file': rel_path,
                        'issue': '使用 import * (建議明確匯入)'
                    })

                # 檢查 TODO/FIXME
                todo_count = len(re.findall(r'#\s*(TODO|FIXME|XXX)', content, re.IGNORECASE))
                if todo_count > 5:
                    issues.append({
                        'file': rel_path,
                        'issue': f'過多 TODO/FIXME 註解 ({todo_count} 個)'
                    })

            except Exception:
                pass

        self.result['checks']['code_style'] = {
            'count': len(issues),
            'issues': issues
        }

        for issue in issues[:5]:
            self.result['warnings'].append(f"{issue['file']}: {issue['issue']}")

    def check_ai_packages(self):
        """檢查 AI/ML 套件"""
        requirements = self.project_path / 'requirements.txt'
        pyproject = self.project_path / 'pyproject.toml'

        detected_packages = []
        content = ''

        if requirements.exists():
            content = requirements.read_text(encoding='utf-8').lower()
        elif pyproject.exists():
            content = pyproject.read_text(encoding='utf-8').lower()

        for pkg, name in self.AI_PACKAGES.items():
            if pkg.lower() in content:
                detected_packages.append(name)

        self.result['checks']['ai_packages'] = {
            'detected': detected_packages
        }

        # 檢查 CUDA 相容性提示
        if 'torch' in content.lower() or 'tensorflow' in content.lower():
            cuda_warning = None
            if 'cu11' in content or 'cu12' in content:
                cuda_warning = 'CUDA 版本已指定'
            else:
                cuda_warning = '未指定 CUDA 版本（可能造成 GPU 不可用）'

            self.result['checks']['ai_packages']['cuda_note'] = cuda_warning

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

        # 檢查副檔名是否被忽略
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
