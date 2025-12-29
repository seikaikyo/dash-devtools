"""
Markdown 測試報告生成模組

生成專業的 Markdown 格式測試報告
- 測試摘要
- 測試結果表格
- 測試案例明細
- ASCII 圖表
"""

from pathlib import Path
from datetime import datetime
from typing import Dict, List

from rich.console import Console

console = Console()


def create_ascii_progress_bar(passed: int, failed: int, width: int = 30) -> str:
    """建立 ASCII 進度條"""
    total = passed + failed
    if total == 0:
        return "[" + "-" * width + "] N/A"

    pass_rate = passed / total
    filled = int(width * pass_rate)

    bar = "[" + "=" * filled + "-" * (width - filled) + "]"
    return f"{bar} {pass_rate * 100:.1f}%"


def format_duration(duration: float) -> str:
    """格式化時間"""
    if duration <= 0:
        return "-"
    elif duration < 0.001:
        return f"{duration * 1000000:.0f}us"
    elif duration < 0.1:
        return f"{duration * 1000:.2f}ms"
    elif duration < 1:
        return f"{duration * 1000:.0f}ms"
    else:
        return f"{duration:.2f}s"


def generate_markdown_report(
    project_name: str,
    test_results: Dict,
    output_path: str,
) -> str:
    """
    生成 Markdown 測試報告

    Args:
        project_name: 專案名稱
        test_results: 測試結果字典 (來自 test_suite)
        output_path: 輸出檔案路徑

    Returns:
        輸出檔案路徑
    """
    lines = []

    # ========== 標題 ==========
    lines.append(f"# {project_name} 測試報告")
    lines.append("")

    timestamp = test_results.get('timestamp', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    lines.append(f"> 報告產生時間: {timestamp}")
    lines.append("")

    # 狀態標示
    overall_success = test_results.get('overall_success', True)
    if overall_success:
        lines.append("![Status](https://img.shields.io/badge/Status-PASSED-success)")
    else:
        lines.append("![Status](https://img.shields.io/badge/Status-FAILED-critical)")
    lines.append("")

    # ========== 測試摘要 ==========
    lines.append("## 測試摘要")
    lines.append("")

    summary = test_results.get('summary', {})
    total_passed = summary.get('total_passed', 0)
    total_failed = summary.get('total_failed', 0)
    total_duration = summary.get('total_duration', 0)
    coverage = summary.get('coverage', 0)

    # 從 test_cases 計算總時間
    if total_duration == 0:
        tests = test_results.get('tests', {})
        for result in tests.values():
            test_cases = result.get('test_cases', [])
            total_duration += sum(tc.get('duration', 0) for tc in test_cases)

    # 進度條
    lines.append("```")
    lines.append(create_ascii_progress_bar(total_passed, total_failed, 40))
    lines.append("```")
    lines.append("")

    # 摘要表格
    lines.append("| 項目 | 數值 |")
    lines.append("|------|------|")
    lines.append(f"| 總測試數 | {total_passed + total_failed} |")
    lines.append(f"| 通過 | {total_passed} |")
    lines.append(f"| 失敗 | {total_failed} |")
    lines.append(f"| 執行時間 | {format_duration(total_duration)} |")
    lines.append(f"| 程式碼覆蓋率 | {coverage:.1f}% |" if coverage > 0 else "| 程式碼覆蓋率 | N/A |")
    lines.append("")

    # ========== 各類型測試結果 ==========
    lines.append("## 各類型測試結果")
    lines.append("")

    tests = test_results.get('tests', {})
    configured_tests = {k: v for k, v in tests.items() if not v.get('not_configured', False)}

    if not configured_tests:
        lines.append("*此專案未設定任何測試框架*")
        lines.append("")
    else:
        type_labels = {
            'UIT': '單元測試 (UIT)',
            'SMOKE': '煙霧測試 (Smoke)',
            'E2E': '端對端測試 (E2E)',
            'UAT': '驗收測試 (UAT)'
        }

        lines.append("| 測試類型 | 狀態 | 通過 | 失敗 | 時間 |")
        lines.append("|----------|------|------|------|------|")

        for test_type, result in configured_tests.items():
            label = type_labels.get(test_type, test_type)
            success = result.get('success', True)
            status = "PASS" if success else "FAIL"
            passed = result.get('passed', 0)
            failed = result.get('failed', 0)

            duration = result.get('duration', 0)
            if duration == 0:
                test_cases = result.get('test_cases', [])
                duration = sum(tc.get('duration', 0) for tc in test_cases)

            lines.append(f"| {label} | {status} | {passed} | {failed} | {format_duration(duration)} |")

        lines.append("")

    # ========== 測試案例明細 ==========
    for test_type, result in configured_tests.items():
        test_cases = result.get('test_cases', [])
        if not test_cases:
            continue

        type_labels = {
            'UIT': '單元測試 (UIT)',
            'SMOKE': '煙霧測試 (Smoke)',
            'E2E': '端對端測試 (E2E)',
            'UAT': '驗收測試 (UAT)'
        }

        lines.append(f"### {type_labels.get(test_type, test_type)} 明細")
        lines.append("")

        # 分類顯示
        passed_cases = [tc for tc in test_cases if tc.get('status') == 'passed']
        failed_cases = [tc for tc in test_cases if tc.get('status') == 'failed']
        skipped_cases = [tc for tc in test_cases if tc.get('status') == 'skipped']

        if passed_cases:
            lines.append("<details>")
            lines.append(f"<summary>通過 ({len(passed_cases)})</summary>")
            lines.append("")
            for tc in passed_cases:
                name = tc.get('name', '')
                duration = tc.get('duration', 0)
                lines.append(f"- [x] {name} ({format_duration(duration)})")
            lines.append("")
            lines.append("</details>")
            lines.append("")

        if failed_cases:
            lines.append(f"**失敗 ({len(failed_cases)})**")
            lines.append("")
            for tc in failed_cases:
                name = tc.get('name', '')
                duration = tc.get('duration', 0)
                error = tc.get('error', '')
                lines.append(f"- [ ] {name} ({format_duration(duration)})")
                if error:
                    lines.append(f"  - Error: `{error[:100]}`")
            lines.append("")

        if skipped_cases:
            lines.append(f"**跳過 ({len(skipped_cases)})**")
            lines.append("")
            for tc in skipped_cases:
                name = tc.get('name', '')
                lines.append(f"- [ ] ~{name}~")
            lines.append("")

    # ========== 測試類型說明 ==========
    lines.append("---")
    lines.append("")
    lines.append("## 測試類型說明")
    lines.append("")

    descriptions = [
        ('UIT', 'Unit Integration Testing', '單元測試驗證各個模組、函數的正確性。使用 Vitest/Jest 框架執行，並產生程式碼覆蓋率報告。'),
        ('Smoke', '煙霧測試', '快速驗證系統關鍵路徑是否正常運作。包含應用程式啟動、頁面載入、API 健康檢查等基本功能。'),
        ('E2E', 'End-to-End Testing', '端對端測試模擬真實使用情境，驗證完整的使用者流程。使用 Playwright 自動化測試框架執行。'),
        ('UAT', 'User Acceptance Testing', '使用者驗收測試從業務角度驗證系統符合需求規格。測試案例依據使用者角色設計，確保系統滿足業務需求。'),
    ]

    for abbr, full, desc in descriptions:
        lines.append(f"- **{abbr}** ({full}): {desc}")

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("*Generated by DashAI DevTools*")

    # 儲存
    content = "\n".join(lines)
    output_file = Path(output_path)
    output_file.write_text(content, encoding='utf-8')

    return str(output_file)


def run_and_generate_markdown_report(
    project_path: str,
    output_path: str = None,
    test_types: List[str] = None,
) -> Dict:
    """
    執行測試並生成 Markdown 報告

    Args:
        project_path: 專案路徑
        output_path: 輸出路徑 (預設為專案目錄下的 test-report.md)
        test_types: 測試類型列表

    Returns:
        結果字典
    """
    from .test_suite import TestSuiteRunner

    project = Path(project_path).resolve()  # 使用 resolve() 取得完整路徑
    project_name = project.name

    if not output_path:
        output_path = str(project / f'{project_name}-test-report.md')

    # 執行測試
    console.print(f"[cyan]執行 {project_name} 測試套件...[/cyan]")
    runner = TestSuiteRunner(project_path)
    suite_result = runner.run_all(test_types)

    # 準備測試結果
    test_results = {
        'project': project_name,
        'timestamp': suite_result.timestamp,
        'overall_success': suite_result.overall_success,
        'summary': {
            'total_passed': suite_result.total_passed,
            'total_failed': suite_result.total_failed,
            'total_duration': suite_result.total_duration,
            'coverage': suite_result.coverage
        },
        'tests': {
            k: {
                'success': v.success,
                'passed': v.passed,
                'failed': v.failed,
                'duration': v.duration,
                'coverage': v.coverage,
                'not_configured': v.not_configured,
                'test_cases': [
                    {
                        'name': tc.name,
                        'status': tc.status,
                        'duration': tc.duration,
                        'error': tc.error,
                    }
                    for tc in v.test_cases
                ]
            }
            for k, v in suite_result.results.items()
        }
    }

    # 生成報告
    console.print(f"[cyan]生成 Markdown 報告...[/cyan]")
    report_path = generate_markdown_report(
        project_name=project_name,
        test_results=test_results,
        output_path=output_path,
    )

    console.print(f"[green]報告已生成: {report_path}[/green]")

    return {
        'success': True,
        'report_path': report_path,
        'test_results': test_results
    }
