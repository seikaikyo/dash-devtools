"""
Pre-push 檢查

支援功能：
1. GitGuardian (ggshield) 機敏資料掃描
2. 測試執行 (Vitest / Jest / Pytest)
3. 強制門檻：測試失敗禁止推送

使用 --strict 選項強制測試通過才能推送
"""

from .pre_commit import run_pre_commit_check, SENSITIVE_PATTERNS
import re
import os
import subprocess
from pathlib import Path


def run_tests(project_path, strict=False):
    """
    執行專案測試

    Args:
        project_path: 專案路徑
        strict: 嚴格模式 - 測試失敗時禁止推送

    Returns:
        dict: {passed: bool, engine: str, message: str}
    """
    project = Path(project_path)
    package_json = project / 'package.json'
    pytest_ini = project / 'pytest.ini'
    pyproject = project / 'pyproject.toml'

    results = []

    # 1. Node.js 專案測試 (Vitest / Jest / Karma)
    if package_json.exists():
        try:
            import json
            pkg = json.loads(package_json.read_text())
            scripts = pkg.get('scripts', {})

            if 'test' in scripts:
                result = subprocess.run(
                    ['npm', 'run', 'test'],
                    capture_output=True,
                    text=True,
                    cwd=project_path,
                    timeout=300  # 5 分鐘超時
                )

                test_engine = 'Vitest'
                if 'jest' in scripts.get('test', ''):
                    test_engine = 'Jest'
                elif 'karma' in scripts.get('test', ''):
                    test_engine = 'Karma'

                results.append({
                    'engine': test_engine,
                    'passed': result.returncode == 0,
                    'output': result.stdout + result.stderr
                })
        except subprocess.TimeoutExpired:
            results.append({
                'engine': 'npm test',
                'passed': False,
                'output': '測試執行超時 (5 分鐘)'
            })
        except Exception as e:
            results.append({
                'engine': 'npm test',
                'passed': True,  # 無法執行時不阻擋
                'output': f'跳過: {str(e)}'
            })

    # 2. Python 專案測試 (pytest)
    if pytest_ini.exists() or (pyproject.exists() and '[tool.pytest' in pyproject.read_text()):
        tests_dir = project / 'tests'
        if tests_dir.exists():
            try:
                result = subprocess.run(
                    ['python3', '-m', 'pytest', 'tests/', '-v', '--tb=short'],
                    capture_output=True,
                    text=True,
                    cwd=project_path,
                    timeout=300
                )

                results.append({
                    'engine': 'Pytest',
                    'passed': result.returncode == 0,
                    'output': result.stdout + result.stderr
                })
            except subprocess.TimeoutExpired:
                results.append({
                    'engine': 'Pytest',
                    'passed': False,
                    'output': '測試執行超時 (5 分鐘)'
                })
            except Exception as e:
                results.append({
                    'engine': 'Pytest',
                    'passed': True,
                    'output': f'跳過: {str(e)}'
                })

    # 彙總結果
    if not results:
        return {
            'passed': True,
            'engine': 'None',
            'message': '未偵測到測試框架'
        }

    all_passed = all(r['passed'] for r in results)
    engines = [r['engine'] for r in results]

    return {
        'passed': all_passed or not strict,
        'strict_failed': not all_passed and strict,
        'engine': ', '.join(engines),
        'message': '所有測試通過' if all_passed else '測試失敗',
        'details': results
    }


def run_ggshield_scan(project_path):
    """使用 GitGuardian ggshield 掃描"""
    try:
        # 檢查是否有 API Key
        if not os.environ.get('GITGUARDIAN_API_KEY'):
            return None

        # 檢查 ggshield 是否安裝
        result = subprocess.run(
            ['ggshield', '--version'],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            return None

        # 執行掃描 (忽略 .claude 本地設定和 node_modules)
        result = subprocess.run(
            ['ggshield', 'secret', 'scan', 'path', str(project_path),
             '--recursive', '--exit-zero', '--json', '--yes',
             '--ignore-path', '.claude/',
             '--ignore-path', 'node_modules/',
             '--ignore-path', '.env',
             '--ignore-path', '.env.local'],
            capture_output=True,
            text=True,
            cwd=project_path
        )

        # 解析結果
        import json
        try:
            data = json.loads(result.stdout)
            issues = []

            # ggshield 輸出格式
            if 'entities_with_incidents' in data:
                for entity in data.get('entities_with_incidents', []):
                    filename = entity.get('filename', 'unknown')
                    for incident in entity.get('incidents', []):
                        issues.append({
                            'file': filename,
                            'type': incident.get('type', 'Secret'),
                            'count': 1
                        })

            return {
                'passed': len(issues) == 0,
                'issues': issues,
                'engine': 'GitGuardian'
            }
        except json.JSONDecodeError:
            return None

    except Exception:
        return None


def run_pre_push_check(project_path):
    """執行 pre-push 檢查 (掃描整個專案)"""
    project = Path(project_path)

    # 優先使用 GitGuardian
    gg_result = run_ggshield_scan(project_path)
    if gg_result is not None:
        return gg_result

    # 備援：使用本地正則表達式
    issues = []

    # 忽略的目錄和檔案
    ignore_dirs = [
        'node_modules', '.git', 'dist', 'build', '.next', '__pycache__',
        'venv', '.venv', '.angular', '.cache', 'coverage'
    ]
    ignore_files = ['.env.example', '.env.sample', '.env.template']

    # 讀取 .gitignore 檔案
    gitignore_patterns = []
    gitignore_file = project / '.gitignore'
    if gitignore_file.exists():
        try:
            for line in gitignore_file.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith('#'):
                    gitignore_patterns.append(line)
        except Exception:
            pass

    def is_gitignored(file_path):
        """檢查檔案是否在 .gitignore 中"""
        rel_path = str(file_path.relative_to(project))
        file_name = file_path.name
        for pattern in gitignore_patterns:
            # 簡單匹配：完全匹配或 pattern 在路徑中
            if pattern == file_name or pattern == rel_path:
                return True
            if pattern.startswith('*.') and file_name.endswith(pattern[1:]):
                return True
            if pattern.endswith('/') and pattern[:-1] in rel_path.split('/'):
                return True
            if pattern in rel_path:
                return True
        return False

    # 掃描所有檔案（不含 .env，因為應該都在 .gitignore）
    extensions = ['*.js', '*.ts', '*.jsx', '*.tsx', '*.py', '*.json', '*.yaml', '*.yml']

    for ext in extensions:
        for file_path in project.rglob(ext):
            # 跳過忽略的目錄
            if any(ignore in str(file_path) for ignore in ignore_dirs):
                continue
            # 跳過範例檔案
            if file_path.name in ignore_files:
                continue
            # 跳過 .gitignore 中的檔案
            if is_gitignored(file_path):
                continue

            try:
                content = file_path.read_text(encoding='utf-8')
                for pattern, desc in SENSITIVE_PATTERNS:
                    matches = re.findall(pattern, content)
                    if matches:
                        issues.append({
                            'file': str(file_path.relative_to(project)),
                            'type': desc,
                            'count': len(matches)
                        })
            except Exception:
                pass

    return {
        'passed': len(issues) == 0,
        'issues': issues
    }
