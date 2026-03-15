"""
Vitest 測試執行器

解析 Vitest JSON reporter 輸出，提取測試案例、統計與覆蓋率。
"""

import json
import re
import subprocess
from pathlib import Path
from typing import Dict

from ..test_suite import TestCase, TestTypeResult


def run_vitest(
    project_path: Path,
    with_coverage: bool = True,
) -> TestTypeResult:
    """
    執行 Vitest 單元測試

    Args:
        project_path: 專案路徑
        with_coverage: 是否包含覆蓋率

    Returns:
        TestTypeResult 測試結果
    """
    result = TestTypeResult(test_type='UIT')

    try:
        # 使用 JSON reporter 取得詳細結果
        cmd = ['npx', 'vitest', 'run', '--reporter=json']
        if with_coverage:
            cmd.append('--coverage')

        proc = subprocess.run(
            cmd,
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=300
        )

        result.success = proc.returncode == 0
        output = proc.stdout + proc.stderr

        # 移除 ANSI 顏色碼
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        clean_output = ansi_escape.sub('', output)

        # 嘗試解析 JSON 並建立摘要
        try:
            # 找到 JSON 部分 (Vitest JSON 輸出)
            json_match = re.search(r'(\{[\s\S]*"testResults"[\s\S]*\})', proc.stdout)
            if json_match:
                json_data = json.loads(json_match.group(1))

                # 從 JSON 提取統計資料
                result.passed = json_data.get('numPassedTests', 0)
                result.failed = json_data.get('numFailedTests', 0)
                num_total = json_data.get('numTotalTests', 0)
                num_suites = json_data.get('numTotalTestSuites', 0)

                # 解析覆蓋率 (從 stderr)
                coverage_match = re.search(r'All files\s+\|\s+([\d.]+)', clean_output)
                if coverage_match:
                    result.coverage = float(coverage_match.group(1))

                for test_file in json_data.get('testResults', []):
                    file_name = Path(test_file.get('name', '')).name
                    for assertion in test_file.get('assertionResults', []):
                        test_name = ' > '.join(
                            assertion.get('ancestorTitles', []) + [assertion.get('title', '')]
                        )
                        status = assertion.get('status', 'passed')
                        # Vitest duration 是毫秒，轉為秒 (與 Playwright 統一)
                        duration = assertion.get('duration', 0) / 1000  # ms -> s
                        result.test_cases.append(TestCase(
                            name=f"{file_name} > {test_name}",
                            status=status,
                            duration=duration
                            # UIT 不顯示 terminal_output (統計已在報告摘要中)
                        ))
        except (json.JSONDecodeError, KeyError):
            # 備援：從輸出解析測試名稱
            for match in re.finditer(
                r'[✓✗]\s+(\S+\.spec\.ts)\s+\((\d+)\s+tests?\)', clean_output
            ):
                file_name = Path(match.group(1)).name
                test_count = int(match.group(2))
                result.test_cases.append(TestCase(
                    name=f"{file_name} ({test_count} tests)",
                    status='passed' if '\u2713' in match.group(0) else 'failed'
                ))

        # 解析統計
        match = re.search(r'Tests\s+(\d+)\s+passed', clean_output)
        if match:
            result.passed = int(match.group(1))
        else:
            match = re.search(r'(\d+)\s+passed', clean_output)
            if match:
                result.passed = int(match.group(1))

        match = re.search(r'(\d+)\s+failed', clean_output)
        if match:
            result.failed = int(match.group(1))

        # 解析覆蓋率
        match = re.search(r'All files\s+\|\s+([\d.]+)', clean_output)
        if match:
            result.coverage = float(match.group(1))

        # 解析時間
        match = re.search(r'Duration\s+([\d.]+)ms', clean_output)
        if match:
            result.duration = float(match.group(1)) / 1000
        else:
            match = re.search(r'Duration\s+([\d.]+)s', clean_output)
            if match:
                result.duration = float(match.group(1))

    except subprocess.TimeoutExpired:
        result.success = False
        result.error = "測試超時 (5分鐘)"
    except Exception as e:
        result.success = False
        result.error = str(e)

    return result
