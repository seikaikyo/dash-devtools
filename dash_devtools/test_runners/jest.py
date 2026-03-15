"""
Jest 測試執行器

執行 Jest 單元測試並解析輸出。
"""

import re
import subprocess
from pathlib import Path

from ..test_suite import TestTypeResult


def run_jest(
    project_path: Path,
    with_coverage: bool = True,
) -> TestTypeResult:
    """
    執行 Jest 單元測試

    Args:
        project_path: 專案路徑
        with_coverage: 是否包含覆蓋率

    Returns:
        TestTypeResult 測試結果
    """
    result = TestTypeResult(test_type='UIT')

    try:
        cmd = ['npx', 'jest', '--coverage'] if with_coverage else ['npx', 'jest']
        proc = subprocess.run(
            cmd,
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=300
        )

        result.success = proc.returncode == 0
        output = proc.stdout + proc.stderr

        match = re.search(r'Tests:\s+(\d+) passed', output)
        if match:
            result.passed = int(match.group(1))

        match = re.search(r'(\d+) failed', output)
        if match:
            result.failed = int(match.group(1))

    except subprocess.TimeoutExpired:
        result.success = False
        result.error = "測試超時 (5分鐘)"
    except Exception as e:
        result.success = False
        result.error = str(e)

    return result
