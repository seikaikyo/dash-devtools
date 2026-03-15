"""
四大類型測試套件整合模組

支援測試類型：
- UIT (Unit Integration Testing): 單元測試 + 覆蓋率
- Smoke: 煙霧測試 (關鍵路徑快速驗證)
- E2E (End-to-End): 端對端測試
- UAT (User Acceptance Testing): 使用者驗收測試

支援測試框架：
- Vitest (推薦)
- Jest
- Playwright (E2E/Smoke/UAT)
- Pytest
"""

import json
import subprocess
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()


@dataclass
class TestCase:
    """單一測試案例"""
    name: str
    status: str  # passed, failed, skipped
    duration: float = 0.0
    error: str = ""
    screenshot: str = ""  # 截圖路徑
    api_response: str = ""  # API 測試回應 (JSON)
    terminal_output: str = ""  # 終端輸出 (UIT)


@dataclass
class TestTypeResult:
    """單一測試類型結果"""
    test_type: str  # UIT, Smoke, E2E, UAT
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    duration: float = 0.0
    coverage: float = 0.0
    success: bool = True
    error: str = ""
    details: List[str] = field(default_factory=list)
    test_cases: List[TestCase] = field(default_factory=list)  # 測試案例列表
    not_configured: bool = False  # 該測試類型未設定 (優雅跳過)


@dataclass
class TestSuiteResult:
    """完整測試套件結果"""
    project_name: str
    results: Dict[str, TestTypeResult] = field(default_factory=dict)
    total_passed: int = 0
    total_failed: int = 0
    total_duration: float = 0.0
    overall_success: bool = True
    coverage: float = 0.0
    timestamp: str = ""


class TestSuiteRunner:
    """四大類型測試套件執行器"""

    def __init__(self, project_path: str):
        self.project_path = Path(project_path)
        self.project_name = self.project_path.name

    def detect_test_setup(self) -> Dict:
        """偵測專案測試設定"""
        setup = {
            'has_vitest': False,
            'has_jest': False,
            'has_playwright': False,
            'has_pytest': False,
            'package_scripts': {},
            'test_dirs': []
        }

        # 檢查 package.json
        package_json = self.project_path / 'package.json'
        if package_json.exists():
            try:
                pkg = json.loads(package_json.read_text())
                deps = {**pkg.get('dependencies', {}), **pkg.get('devDependencies', {})}
                setup['package_scripts'] = pkg.get('scripts', {})

                setup['has_vitest'] = 'vitest' in deps
                setup['has_jest'] = 'jest' in deps
                setup['has_playwright'] = '@playwright/test' in deps
            except Exception:
                pass

        # 檢查測試目錄
        for test_dir in ['e2e', 'tests', 'test', '__tests__', 'spec']:
            if (self.project_path / test_dir).exists():
                setup['test_dirs'].append(test_dir)

        # 檢查 Playwright 設定
        if (self.project_path / 'playwright.config.ts').exists():
            setup['has_playwright'] = True

        # 檢查 Python
        if (self.project_path / 'pytest.ini').exists() or \
           (self.project_path / 'pyproject.toml').exists():
            setup['has_pytest'] = True

        return setup

    def run_uit(self, with_coverage: bool = True) -> TestTypeResult:
        """執行 UIT 單元測試"""
        setup = self.detect_test_setup()

        if setup['has_vitest']:
            from .test_runners.vitest import run_vitest
            return run_vitest(self.project_path, with_coverage)
        elif setup['has_jest']:
            from .test_runners.jest import run_jest
            return run_jest(self.project_path, with_coverage)
        elif setup['has_pytest']:
            from .test_runners.pytest_runner import run_pytest
            return run_pytest(self.project_path, with_coverage)
        else:
            # 無測試框架，優雅跳過 (不視為失敗)
            result = TestTypeResult(test_type='UIT')
            result.success = True
            result.not_configured = True
            result.error = "未設定單元測試框架"
            return result

    def run_playwright_tests(self, spec_pattern: str, test_type: str, capture_screenshots: bool = True) -> TestTypeResult:
        """執行 Playwright 測試"""
        from .test_runners.karma import run_playwright_tests
        setup = self.detect_test_setup()
        return run_playwright_tests(self.project_path, spec_pattern, test_type, setup, capture_screenshots)

    def _parse_playwright_suite(self, suite: Dict, result: TestTypeResult, prefix: str = ""):
        """遞迴解析 Playwright 測試套件"""
        from .test_runners.karma import parse_playwright_suite
        parse_playwright_suite(suite, result, prefix)

    def run_smoke(self) -> TestTypeResult:
        """執行 Smoke 煙霧測試"""
        return self.run_playwright_tests('smoke.spec.ts', 'Smoke')

    def run_e2e(self) -> TestTypeResult:
        """執行 E2E 端對端測試"""
        result = self.run_playwright_tests('mes-system.spec.ts', 'E2E')
        if result.passed == 0 and not result.error:
            result = self.run_playwright_tests('*.e2e.spec.ts', 'E2E')
        return result

    def run_uat(self) -> TestTypeResult:
        """執行 UAT 使用者驗收測試"""
        return self.run_playwright_tests('uat.spec.ts', 'UAT')

    def run_all(self, test_types: List[str] = None) -> TestSuiteResult:
        """執行所有測試類型"""
        if test_types is None:
            test_types = ['UIT', 'Smoke', 'E2E', 'UAT']

        suite_result = TestSuiteResult(
            project_name=self.project_name,
            timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        )

        for test_type in test_types:
            if test_type.upper() == 'UIT':
                result = self.run_uit(with_coverage=True)
            elif test_type.upper() == 'SMOKE':
                result = self.run_smoke()
            elif test_type.upper() == 'E2E':
                result = self.run_e2e()
            elif test_type.upper() == 'UAT':
                result = self.run_uat()
            else:
                continue

            suite_result.results[test_type.upper()] = result
            suite_result.total_passed += result.passed
            suite_result.total_failed += result.failed
            suite_result.total_duration += result.duration

            if not result.success:
                suite_result.overall_success = False

        # 取得 UIT 覆蓋率
        if 'UIT' in suite_result.results:
            suite_result.coverage = suite_result.results['UIT'].coverage

        return suite_result


def render_test_suite_result(suite: TestSuiteResult):
    """渲染測試套件結果"""

    # 標題
    status_color = "green" if suite.overall_success else "red"
    status_icon = "v" if suite.overall_success else "x"

    title = Text()
    title.append(f"\n  {suite.project_name} ", style="bold white")
    title.append("測試套件報告\n", style="dim")
    console.print(Panel(title, border_style="cyan"))

    # 測試類型結果表格
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("測試類型", style="white")
    table.add_column("狀態", justify="center")
    table.add_column("通過", justify="right", style="green")
    table.add_column("失敗", justify="right", style="red")
    table.add_column("時間", justify="right", style="dim")
    table.add_column("覆蓋率", justify="right")

    type_labels = {
        'UIT': '單元測試 (UIT)',
        'Smoke': '煙霧測試 (Smoke)',
        'E2E': '端對端測試 (E2E)',
        'UAT': '驗收測試 (UAT)'
    }

    configured_count = 0
    for test_type, result in suite.results.items():
        # 判斷狀態
        if result.not_configured:
            status = "[dim]N/A[/dim]"
        elif result.success:
            status = "[green]PASS[/green]"
            configured_count += 1
        else:
            status = "[red]FAIL[/red]"
            configured_count += 1

        coverage_str = f"{result.coverage:.0f}%" if result.coverage > 0 else "-"

        table.add_row(
            type_labels.get(test_type, test_type),
            status,
            str(result.passed) if not result.not_configured else "-",
            str(result.failed) if result.failed else "-",
            f"{result.duration:.1f}s" if result.duration else "-",
            coverage_str
        )

    console.print(table)

    # 總計
    console.print()
    total = suite.total_passed + suite.total_failed
    if total > 0:
        pass_rate = (suite.total_passed / total) * 100

        # 進度條
        bar_width = 40
        passed_width = int((suite.total_passed / total) * bar_width)
        failed_width = bar_width - passed_width

        bar = Text()
        bar.append("  ")
        bar.append("=" * passed_width, style="green")
        bar.append("=" * failed_width, style="red")
        bar.append(f" {pass_rate:.1f}%", style="green" if pass_rate >= 80 else "yellow")
        console.print(bar)
        console.print()

    # 總結
    summary = Text()
    summary.append("  總計: ")
    summary.append(f"{suite.total_passed} passed", style="green")
    summary.append(" / ")
    summary.append(f"{suite.total_failed} failed", style="red" if suite.total_failed else "dim")
    summary.append(f"  |  {suite.total_duration:.1f}s", style="dim")
    console.print(summary)

    # 覆蓋率
    if suite.coverage > 0:
        cov_color = "green" if suite.coverage >= 80 else "yellow" if suite.coverage >= 60 else "red"
        console.print(f"  覆蓋率: [{cov_color}]{suite.coverage:.1f}%[/{cov_color}]")

    # 最終狀態
    console.print()
    if configured_count == 0:
        console.print(f"  [yellow][-] 此專案未設定任何測試[/yellow]")
    elif suite.overall_success:
        console.print(f"  [green][v] 所有測試通過[/green]")
    else:
        console.print(f"  [red][x] 部分測試失敗[/red]")

    console.print()

    return {
        'success': suite.overall_success,
        'total_passed': suite.total_passed,
        'total_failed': suite.total_failed,
        'coverage': suite.coverage,
        'results': {k: {
            'passed': v.passed,
            'failed': v.failed,
            'success': v.success
        } for k, v in suite.results.items()}
    }


def run_test_suite(
    project_path: str,
    test_types: List[str] = None,
    coverage: bool = True
) -> dict:
    """
    執行測試套件

    Args:
        project_path: 專案路徑
        test_types: 要執行的測試類型列表 (預設全部)
        coverage: 是否包含覆蓋率 (預設 True)

    Returns:
        測試結果字典
    """
    runner = TestSuiteRunner(project_path)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        # 偵測設定
        task = progress.add_task("偵測測試設定...", total=None)
        setup = runner.detect_test_setup()
        progress.update(task, description="[green]設定偵測完成 v")

        # 執行測試
        task = progress.add_task("執行測試套件...", total=None)
        suite_result = runner.run_all(test_types)
        progress.update(task, description="[green]測試執行完成 v")

    return render_test_suite_result(suite_result)


def run_test_suite_report(project_path: str, output_path: str = None) -> dict:
    """
    產生測試套件報告

    Args:
        project_path: 專案路徑
        output_path: 報告輸出路徑 (可選)

    Returns:
        報告字典
    """
    runner = TestSuiteRunner(project_path)
    suite_result = runner.run_all()

    report = {
        'project': suite_result.project_name,
        'timestamp': suite_result.timestamp,
        'overall_success': suite_result.overall_success,
        'summary': {
            'total_passed': suite_result.total_passed,
            'total_failed': suite_result.total_failed,
            'total_duration': suite_result.total_duration,
            'coverage': suite_result.coverage
        },
        'tests': {}
    }

    for test_type, result in suite_result.results.items():
        report['tests'][test_type] = {
            'success': result.success,
            'passed': result.passed,
            'failed': result.failed,
            'duration': result.duration,
            'coverage': result.coverage,
            'error': result.error
        }

    if output_path:
        output_file = Path(output_path)
        output_file.write_text(json.dumps(report, indent=2, ensure_ascii=False))
        console.print(f"[green]報告已儲存: {output_path}[/green]")

    return report
