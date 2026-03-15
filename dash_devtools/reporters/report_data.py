"""
報告資料收集模組

負責收集測試結果、健康評分、程式碼統計等報告所需資料。
"""

import json
import re
import subprocess
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class TestResult:
    """測試結果"""
    framework: str  # pytest, jest, vitest, etc.
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    duration: float = 0.0
    output: str = ""
    success: bool = True


@dataclass
class ScreenshotResult:
    """截圖結果"""
    url: str
    path: str
    success: bool = True
    error: str = ""


@dataclass
class ReportData:
    """報告資料"""
    project_name: str
    generated_at: str
    health_scores: Dict = field(default_factory=dict)
    stats: Dict = field(default_factory=dict)
    test_result: Optional[TestResult] = None
    screenshots: List[ScreenshotResult] = field(default_factory=list)


def collect_health(project_path: Path) -> Dict:
    """收集健康評分

    Args:
        project_path: 專案根目錄路徑

    Returns:
        健康評分資料字典
    """
    from ..health import HealthChecker

    checker = HealthChecker(str(project_path))
    scores = checker.check_all()

    health_data = {
        'total_score': sum(s.score for s in scores.values()) // len(scores),
        'scores': {}
    }

    for key, score in scores.items():
        health_data['scores'][key] = {
            'score': score.score,
            'category': score.category,
            'issues': score.issues,
            'recommendations': score.recommendations
        }

    return health_data


def collect_stats(project_path: Path) -> Dict:
    """收集程式碼統計

    Args:
        project_path: 專案根目錄路徑

    Returns:
        程式碼統計資料字典
    """
    from ..stats import StatsCollector

    collector = StatsCollector(str(project_path))
    stats = collector.collect()

    stats_data = {
        'total_files': stats.total_files,
        'total_lines': stats.total_lines,
        'total_code_lines': stats.total_code_lines,
        'size_bytes': stats.total_size_bytes,
        'languages': {},
        'largest_files': stats.largest_files[:5],
        'complexity_issues': stats.complexity_issues
    }

    for name, lang in stats.languages.items():
        stats_data['languages'][name] = {
            'files': lang.files,
            'lines': lang.lines
        }

    return stats_data


def run_tests(project_path: Path) -> TestResult:
    """執行測試

    偵測專案使用的測試框架（vitest, jest, karma, pytest）並執行測試。

    Args:
        project_path: 專案根目錄路徑

    Returns:
        TestResult 測試結果
    """
    result = TestResult(framework='unknown')

    # 偵測測試框架
    package_json = project_path / 'package.json'
    if package_json.exists():
        try:
            pkg = json.loads(package_json.read_text())
            deps = {**pkg.get('dependencies', {}), **pkg.get('devDependencies', {})}
            scripts = pkg.get('scripts', {})

            # 判斷測試框架
            if 'vitest' in deps:
                result.framework = 'vitest'
            elif 'jest' in deps:
                result.framework = 'jest'
            elif '@angular-devkit/build-angular' in deps:
                result.framework = 'karma'

            # 執行測試
            if 'test' in scripts:
                try:
                    proc = subprocess.run(
                        ['npm', 'test', '--', '--passWithNoTests', '--run'],
                        cwd=project_path,
                        capture_output=True,
                        text=True,
                        timeout=120
                    )
                    result.output = proc.stdout + proc.stderr
                    result.success = proc.returncode == 0

                    # 簡單解析結果
                    if 'passed' in result.output.lower():
                        result.passed = result.output.lower().count('passed')
                    if 'failed' in result.output.lower():
                        result.failed = result.output.lower().count('failed')

                except subprocess.TimeoutExpired:
                    result.success = False
                    result.output = "測試超時 (120秒)"
                except Exception as e:
                    result.success = False
                    result.output = str(e)

        except Exception:
            pass

    # Python 專案
    requirements = project_path / 'requirements.txt'
    pytest_ini = project_path / 'pytest.ini'
    if requirements.exists() or pytest_ini.exists():
        result.framework = 'pytest'
        try:
            proc = subprocess.run(
                ['python', '-m', 'pytest', '--tb=short', '-q'],
                cwd=project_path,
                capture_output=True,
                text=True,
                timeout=120
            )
            result.output = proc.stdout + proc.stderr
            result.success = proc.returncode == 0

            # 解析 pytest 結果
            match = re.search(r'(\d+) passed', result.output)
            if match:
                result.passed = int(match.group(1))
            match = re.search(r'(\d+) failed', result.output)
            if match:
                result.failed = int(match.group(1))

        except Exception as e:
            result.output = str(e)
            result.success = False

    return result
