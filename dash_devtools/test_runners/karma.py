"""
Playwright 測試執行器 (Karma)

用於 Smoke / E2E / UAT 測試，基於 Playwright JSON reporter。
命名為 karma 是因為它負責執行 Playwright-based 的整合測試類別。
"""

import json
import re
import subprocess
from pathlib import Path
from typing import Dict

from ..test_suite import TestCase, TestTypeResult


def parse_playwright_suite(
    suite: Dict,
    result: TestTypeResult,
    prefix: str = "",
) -> None:
    """
    遞迴解析 Playwright 測試套件

    Args:
        suite: Playwright JSON 套件資料
        result: 寫入結果的 TestTypeResult
        prefix: 測試名稱前綴 (遞迴用)
    """
    suite_title = suite.get('title', '')
    current_prefix = f"{prefix} > {suite_title}" if prefix else suite_title

    # 解析 specs (測試案例)
    for spec in suite.get('specs', []):
        test_title = spec.get('title', '')
        full_name = f"{current_prefix} > {test_title}" if current_prefix else test_title

        # 取得測試結果
        tests = spec.get('tests', [])
        for test in tests:
            results_list = test.get('results', [])
            status = 'passed'
            duration = 0.0
            error = ''
            screenshot = ''
            api_response = ''

            for res in results_list:
                status = res.get('status', 'passed')
                duration = res.get('duration', 0) / 1000  # 毫秒轉秒
                if res.get('error'):
                    error = res['error'].get('message', '')[:200]

                # 取得附件 (截圖或 API 回應)
                attachments = res.get('attachments', [])
                for att in attachments:
                    att_name = att.get('name', '')
                    if att_name == 'screenshot' and att.get('path'):
                        screenshot = att.get('path', '')
                    elif att_name == 'api-response' and att.get('body'):
                        # API 回應是 base64 編碼的 body
                        import base64
                        try:
                            body = att.get('body', '')
                            if body:
                                api_response = base64.b64decode(body).decode('utf-8')
                        except Exception:
                            api_response = att.get('body', '')

            result.test_cases.append(TestCase(
                name=full_name,
                status=status,
                duration=duration,
                error=error,
                screenshot=screenshot,
                api_response=api_response
            ))

    # 遞迴處理子套件
    for sub_suite in suite.get('suites', []):
        parse_playwright_suite(sub_suite, result, current_prefix)


def run_playwright_tests(
    project_path: Path,
    spec_pattern: str,
    test_type: str,
    setup: Dict,
    capture_screenshots: bool = True,
) -> TestTypeResult:
    """
    執行 Playwright 測試

    Args:
        project_path: 專案路徑
        spec_pattern: 測試檔案 glob 模式
        test_type: 測試類型 (Smoke / E2E / UAT)
        setup: detect_test_setup() 回傳的設定字典
        capture_screenshots: 是否擷取截圖

    Returns:
        TestTypeResult 測試結果
    """
    result = TestTypeResult(test_type=test_type)

    try:
        # 檢查是否有 Playwright
        if not setup['has_playwright']:
            result.success = True
            result.not_configured = True
            result.error = "未安裝 Playwright"
            return result

        # 檢查是否有對應的測試檔案
        spec_files = list(project_path.glob(f'e2e/{spec_pattern}'))
        if not spec_files:
            result.success = True
            result.not_configured = True
            result.error = f"未找到 {spec_pattern}"
            return result

        # 為每個測試類型建立獨立的輸出目錄
        output_dir = project_path / 'test-results' / test_type.lower()
        output_dir.mkdir(parents=True, exist_ok=True)

        # 使用 JSON reporter 取得詳細結果
        cmd = [
            'npx', 'playwright', 'test', f'e2e/{spec_pattern}',
            '--reporter=json',
            f'--output={output_dir}'
        ]

        # 設定環境變數啟用截圖
        env = dict(subprocess.os.environ)
        if capture_screenshots:
            env['SCREENSHOT_ALL'] = '1'

        proc = subprocess.run(
            cmd,
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=300,
            env=env
        )

        output = proc.stdout + proc.stderr
        result.success = proc.returncode == 0

        # 嘗試解析 JSON 輸出
        try:
            # Playwright JSON 輸出在 stdout
            json_data = json.loads(proc.stdout)

            # 解析測試案例
            for suite in json_data.get('suites', []):
                parse_playwright_suite(suite, result)

            # 計算統計
            result.passed = sum(1 for tc in result.test_cases if tc.status == 'passed')
            result.failed = sum(1 for tc in result.test_cases if tc.status == 'failed')
            result.skipped = sum(1 for tc in result.test_cases if tc.status == 'skipped')

        except json.JSONDecodeError:
            # 備援：用正則解析
            ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
            clean_output = ansi_escape.sub('', output)

            match = re.search(r'(\d+) passed', clean_output)
            if match:
                result.passed = int(match.group(1))

            match = re.search(r'(\d+) failed', clean_output)
            if match:
                result.failed = int(match.group(1))

            # 解析測試名稱 (從輸出中提取)
            for match in re.finditer(r'> ([^>]+\.spec\.ts:\d+:\d+) > (.+)', clean_output):
                test_name = match.group(2).strip()
                status = 'passed'
                if '\u2713' in clean_output or 'passed' in clean_output:
                    status = 'passed'
                result.test_cases.append(TestCase(name=test_name, status=status))

        match = re.search(r'\(([\d.]+)s\)', output)
        if match:
            result.duration = float(match.group(1))

    except subprocess.TimeoutExpired:
        result.success = False
        result.error = "測試超時"
    except Exception as e:
        result.success = False
        result.error = str(e)

    return result
