"""
測試執行與分析

專注於測試的核心功能：
- 自動偵測測試框架
- 執行測試並收集結果
- 覆蓋率分析
- 測試健康指標
"""

import json
import subprocess
import re
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
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


@dataclass
class TestSuite:
    """測試套件"""
    name: str
    tests: List[TestCase] = field(default_factory=list)

    @property
    def passed(self) -> int:
        return sum(1 for t in self.tests if t.status == 'passed')

    @property
    def failed(self) -> int:
        return sum(1 for t in self.tests if t.status == 'failed')

    @property
    def skipped(self) -> int:
        return sum(1 for t in self.tests if t.status == 'skipped')


@dataclass
class TestResult:
    """測試執行結果"""
    framework: str
    success: bool = True
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    duration: float = 0.0
    coverage: float = 0.0
    suites: List[TestSuite] = field(default_factory=list)
    failed_tests: List[str] = field(default_factory=list)
    output: str = ""


class TestRunner:
    """測試執行器"""

    FRAMEWORKS = {
        'vitest': {
            'detect': ['vitest'],
            'cmd': ['npx', 'vitest', 'run', '--reporter=json'],
            'coverage_cmd': ['npx', 'vitest', 'run', '--coverage']
        },
        'jest': {
            'detect': ['jest'],
            'cmd': ['npx', 'jest', '--json', '--passWithNoTests'],
            'coverage_cmd': ['npx', 'jest', '--coverage', '--passWithNoTests']
        },
        'pytest': {
            'detect': ['pytest'],
            'cmd': ['python', '-m', 'pytest', '-v', '--tb=short'],
            'coverage_cmd': ['python', '-m', 'pytest', '--cov', '--cov-report=term-missing']
        },
        'karma': {
            'detect': ['@angular-devkit/build-angular', 'karma'],
            'cmd': ['npx', 'ng', 'test', '--no-watch', '--browsers=ChromeHeadless'],
            'coverage_cmd': ['npx', 'ng', 'test', '--no-watch', '--code-coverage', '--browsers=ChromeHeadless']
        }
    }

    def __init__(self, project_path: str):
        self.project_path = Path(project_path)
        self.project_name = self.project_path.name

    def detect_framework(self) -> Tuple[str, Dict]:
        """偵測測試框架"""
        # 檢查 package.json
        package_json = self.project_path / 'package.json'
        if package_json.exists():
            try:
                pkg = json.loads(package_json.read_text())
                deps = {**pkg.get('dependencies', {}), **pkg.get('devDependencies', {})}

                for framework, config in self.FRAMEWORKS.items():
                    if framework == 'pytest':
                        continue
                    for detect_pkg in config['detect']:
                        if detect_pkg in deps:
                            return framework, config
            except Exception:
                pass

        # 檢查 Python 專案
        if (self.project_path / 'pytest.ini').exists() or \
           (self.project_path / 'pyproject.toml').exists() or \
           (self.project_path / 'setup.py').exists():
            # 確認有 tests 目錄或 test_*.py 檔案
            if (self.project_path / 'tests').exists() or \
               list(self.project_path.rglob('test_*.py')):
                return 'pytest', self.FRAMEWORKS['pytest']

        return None, None

    def run(self, with_coverage: bool = False, verbose: bool = False) -> TestResult:
        """執行測試"""
        framework, config = self.detect_framework()

        if not framework:
            return TestResult(
                framework='unknown',
                success=False,
                output='未偵測到測試框架'
            )

        result = TestResult(framework=framework)
        cmd = config['coverage_cmd'] if with_coverage else config['cmd']

        try:
            proc = subprocess.run(
                cmd,
                cwd=self.project_path,
                capture_output=True,
                text=True,
                timeout=300  # 5 分鐘超時
            )

            result.output = proc.stdout + proc.stderr
            result.success = proc.returncode == 0

            # 解析結果
            self._parse_result(result, framework, proc.stdout + proc.stderr)

        except subprocess.TimeoutExpired:
            result.success = False
            result.output = "測試超時 (5分鐘)"
        except FileNotFoundError as e:
            result.success = False
            result.output = f"找不到測試命令: {e}"
        except Exception as e:
            result.success = False
            result.output = str(e)

        return result

    def _parse_result(self, result: TestResult, framework: str, output: str):
        """解析測試結果"""
        if framework == 'pytest':
            self._parse_pytest(result, output)
        elif framework in ['jest', 'vitest']:
            self._parse_jest(result, output)
        elif framework == 'karma':
            self._parse_karma(result, output)

    def _parse_pytest(self, result: TestResult, output: str):
        """解析 pytest 輸出"""
        # 解析通過/失敗數量
        match = re.search(r'(\d+) passed', output)
        if match:
            result.passed = int(match.group(1))

        match = re.search(r'(\d+) failed', output)
        if match:
            result.failed = int(match.group(1))

        match = re.search(r'(\d+) skipped', output)
        if match:
            result.skipped = int(match.group(1))

        # 解析執行時間
        match = re.search(r'in ([\d.]+)s', output)
        if match:
            result.duration = float(match.group(1))

        # 解析覆蓋率
        match = re.search(r'TOTAL\s+\d+\s+\d+\s+(\d+)%', output)
        if match:
            result.coverage = float(match.group(1))

        # 收集失敗的測試
        for match in re.finditer(r'FAILED ([\w/.:]+)', output):
            result.failed_tests.append(match.group(1))

    def _parse_jest(self, result: TestResult, output: str):
        """解析 Jest/Vitest 輸出"""
        # 嘗試解析 JSON 輸出
        try:
            # 找到 JSON 部分
            json_match = re.search(r'\{.*"numTotalTests".*\}', output, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                result.passed = data.get('numPassedTests', 0)
                result.failed = data.get('numFailedTests', 0)
                result.skipped = data.get('numPendingTests', 0)
                return
        except Exception:
            pass

        # 備援：用正則解析
        match = re.search(r'Tests:\s+(\d+) passed', output)
        if match:
            result.passed = int(match.group(1))

        match = re.search(r'(\d+) failed', output)
        if match:
            result.failed = int(match.group(1))

    def _parse_karma(self, result: TestResult, output: str):
        """解析 Karma 輸出"""
        match = re.search(r'Executed (\d+) of (\d+)', output)
        if match:
            executed = int(match.group(1))
            total = int(match.group(2))

            if 'SUCCESS' in output:
                result.passed = executed
            else:
                match = re.search(r'(\d+) FAILED', output)
                if match:
                    result.failed = int(match.group(1))
                    result.passed = executed - result.failed


def render_test_result(result: TestResult, project_name: str):
    """渲染測試結果"""

    # 標題
    status_color = "green" if result.success else "red"
    status_icon = "✓" if result.success else "✗"

    title = Text()
    title.append(f"\n  {project_name} ", style="bold white")
    title.append("測試報告\n", style="dim")
    console.print(Panel(title, border_style="cyan"))

    # 狀態
    console.print(f"  [{status_color}]{status_icon}[/{status_color}] ", end="")
    console.print(f"[bold {status_color}]{'PASSED' if result.success else 'FAILED'}[/bold {status_color}]")
    console.print(f"  [dim]Framework:[/dim] {result.framework}")
    if result.duration:
        console.print(f"  [dim]Duration:[/dim] {result.duration:.2f}s")
    console.print()

    # 統計
    total = result.passed + result.failed + result.skipped
    if total > 0:
        pass_rate = (result.passed / total) * 100

        # 進度條
        bar_width = 40
        passed_width = int((result.passed / total) * bar_width)
        failed_width = int((result.failed / total) * bar_width)
        skipped_width = bar_width - passed_width - failed_width

        bar = Text()
        bar.append("  ")
        bar.append("█" * passed_width, style="green")
        bar.append("█" * failed_width, style="red")
        bar.append("█" * skipped_width, style="yellow")
        bar.append(f" {pass_rate:.1f}%", style="green" if pass_rate >= 80 else "yellow")
        console.print(bar)
        console.print()

        # 數字統計
        stats = Text()
        stats.append("  ")
        stats.append(f"{result.passed} passed", style="green")
        stats.append("  |  ")
        stats.append(f"{result.failed} failed", style="red" if result.failed else "dim")
        stats.append("  |  ")
        stats.append(f"{result.skipped} skipped", style="yellow" if result.skipped else "dim")
        console.print(stats)

    # 覆蓋率
    if result.coverage > 0:
        console.print()
        cov_color = "green" if result.coverage >= 80 else "yellow" if result.coverage >= 60 else "red"
        console.print(f"  [dim]Coverage:[/dim] [{cov_color}]{result.coverage:.1f}%[/{cov_color}]")

    # 失敗的測試
    if result.failed_tests:
        console.print()
        console.print("  [bold red]Failed Tests:[/bold red]")
        for test in result.failed_tests[:10]:
            console.print(f"    [red]•[/red] {test}")
        if len(result.failed_tests) > 10:
            console.print(f"    [dim]... and {len(result.failed_tests) - 10} more[/dim]")

    console.print()

    return {
        'success': result.success,
        'passed': result.passed,
        'failed': result.failed,
        'skipped': result.skipped,
        'coverage': result.coverage
    }


def run_test(project_path: str, coverage: bool = False, verbose: bool = False) -> dict:
    """執行測試"""
    runner = TestRunner(project_path)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("執行測試中...", total=None)
        result = runner.run(with_coverage=coverage, verbose=verbose)
        progress.update(task, description="[green]測試完成 ✓")

    return render_test_result(result, runner.project_name)


def run_test_all(projects: List[str], coverage: bool = False) -> dict:
    """多專案測試"""
    results = []

    console.print(Panel(
        Text("\n  專案測試總覽\n", style="bold white"),
        border_style="cyan"
    ))

    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("專案", style="white")
    table.add_column("狀態", justify="center")
    table.add_column("通過", justify="right", style="green")
    table.add_column("失敗", justify="right", style="red")
    table.add_column("覆蓋率", justify="right")
    table.add_column("Framework", style="dim")

    for project in projects:
        try:
            runner = TestRunner(project)
            framework, _ = runner.detect_framework()

            if not framework:
                table.add_row(
                    Path(project).name,
                    "[dim]-[/dim]",
                    "-",
                    "-",
                    "-",
                    "[dim]無測試[/dim]"
                )
                continue

            result = runner.run(with_coverage=coverage)

            status = "[green]PASS[/green]" if result.success else "[red]FAIL[/red]"
            cov_display = f"{result.coverage:.0f}%" if result.coverage > 0 else "-"

            table.add_row(
                Path(project).name,
                status,
                str(result.passed),
                str(result.failed),
                cov_display,
                result.framework
            )

            results.append({
                'project': Path(project).name,
                'success': result.success,
                'passed': result.passed,
                'failed': result.failed
            })

        except Exception as e:
            table.add_row(
                Path(project).name,
                "[red]ERROR[/red]",
                "-",
                "-",
                "-",
                f"[red]{str(e)[:20]}[/red]"
            )

    console.print(table)

    # 總結
    total_passed = sum(r['passed'] for r in results)
    total_failed = sum(r['failed'] for r in results)
    all_success = all(r['success'] for r in results)

    console.print()
    if all_success:
        console.print(f"  [green]所有專案測試通過[/green] ({total_passed} tests)")
    else:
        console.print(f"  [red]部分專案測試失敗[/red] ({total_failed} failures)")

    return {'projects': results, 'all_success': all_success}
