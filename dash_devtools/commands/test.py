"""init-test, test, test-suite, gas-test 指令"""

import click
from pathlib import Path
from dash_devtools.cli import console, DEFAULT_PROJECTS


@click.command('init-test')
@click.argument('project', type=click.Path(), default='.')
@click.option('--e2e', is_flag=True, help='同時設定 Playwright E2E 測試')
def init_test(project, e2e):
    """初始化測試框架

    自動偵測專案類型並設定適合的測試框架：
    - Vite 專案 → Vitest
    - Angular 專案 → Jest
    - 可選 Playwright E2E

    使用範例：
      dash init-test .
      dash init-test . --e2e
    """
    from ..init_test import run_init_test

    run_init_test(project, include_e2e=e2e)


@click.command()
@click.argument('project', type=click.Path(), default='.')
@click.option('--all', 'test_all', is_flag=True, help='測試所有專案')
@click.option('--coverage', '-c', is_flag=True, help='產生覆蓋率報告')
@click.option('--verbose', '-v', is_flag=True, help='詳細輸出')
def test(project, test_all, coverage, verbose):
    """執行專案測試

    自動偵測測試框架並執行：
    - pytest (Python)
    - vitest/jest (JavaScript/TypeScript)
    - karma (Angular)

    使用範例：
      dash test .
      dash test . --coverage
      dash test --all
    """
    from ..testing import run_test, run_test_all

    if test_all:
        run_test_all(DEFAULT_PROJECTS, coverage=coverage)
    else:
        run_test(project, coverage=coverage, verbose=verbose)


@click.command('test-suite')
@click.argument('project', type=click.Path(), default='.')
@click.option('--types', '-t', type=str, default='UIT,Smoke,E2E,UAT',
              help='測試類型 (逗號分隔): UIT,Smoke,E2E,UAT')
@click.option('--coverage', '-c', is_flag=True, default=True, help='包含覆蓋率報告')
@click.option('--report', '-r', type=click.Path(), help='輸出 JSON 報告路徑')
@click.option('--word', '-w', type=click.Path(), help='輸出 Word 報告路徑')
@click.option('--md', '-m', type=click.Path(), help='輸出 Markdown 報告路徑')
@click.option('--no-screenshots', is_flag=True, help='不擷取系統截圖')
def test_suite(project, types, coverage, report, word, md, no_screenshots):
    """四大類型測試套件

    執行完整測試套件，包含：
    - UIT: 單元測試 (Vitest/Jest/Pytest) + 覆蓋率
    - Smoke: 煙霧測試 (Playwright smoke.spec.ts)
    - E2E: 端對端測試 (Playwright mes-system.spec.ts)
    - UAT: 使用者驗收測試 (Playwright uat.spec.ts)

    報告格式：
    - --word: Word 文件 (含圖表、截圖)
    - --md: Markdown 文件 (適合 GitHub)
    - --report: JSON 原始資料

    使用範例：
      dash test-suite .
      dash test-suite . --types UIT,Smoke
      dash test-suite . --report ./test-report.json
      dash test-suite . --word ./test-report.docx
      dash test-suite . --md ./test-report.md
      dash test-suite . --word report.docx --no-screenshots
    """
    from ..test_suite import run_test_suite, run_test_suite_report

    test_types = [t.strip() for t in types.split(',')]

    # 如果指定 Word 報告，使用 word_report 模組
    if word:
        from ..word_report import run_and_generate_report
        result = run_and_generate_report(
            project,
            output_path=word,
            test_types=test_types,
            include_screenshots=not no_screenshots
        )
    elif md:
        from ..markdown_report import run_and_generate_markdown_report
        result = run_and_generate_markdown_report(
            project,
            output_path=md,
            test_types=test_types,
        )
    elif report:
        result = run_test_suite_report(project, output_path=report)
    else:
        result = run_test_suite(project, test_types=test_types, coverage=coverage)

    if not result.get('success', True):
        raise SystemExit(1)


@click.command('gas-test')
@click.argument('project', type=click.Path(), default=str(Path.home() / 'Documents' / 'github' / 'GAS' / 'mes'))
@click.option('--types', '-t', type=str, default='UIT,Smoke,E2E,UAT',
              help='測試類型 (逗號分隔): UIT,Smoke,E2E,UAT')
@click.option('--word', '-w', type=click.Path(), help='輸出 Word 報告路徑')
@click.option('--url', '-u', type=str, help='GAS 部署 URL (預設使用 MES 正式環境)')
def gas_test(project, types, word, url):
    """GAS MES 四大測試套件

    針對 Google Apps Script MES 系統的專用測試：
    - UIT: 程式碼靜態分析 (Code.js, Database.js, HTML)
    - Smoke: 頁面載入測試 (各頁籤)
    - E2E: 完整流程測試 (登入→操作→驗證)
    - UAT: 角色權限驗證

    使用範例：
      dash gas-test
      dash gas-test /path/to/gas/mes
      dash gas-test --types UIT,Smoke
      dash gas-test --word report.docx
      dash gas-test --url https://script.google.com/macros/s/xxx/exec
    """
    from ..gas_mes_test import run_gas_test, run_gas_test_with_report

    test_types = [t.strip() for t in types.split(',')]

    if word:
        result = run_gas_test_with_report(
            project,
            output_path=word,
            test_types=test_types,
            url=url
        )
    else:
        result = run_gas_test(project, test_types=test_types, url=url)

    if not result.get('success', True):
        raise SystemExit(1)


def register(main):
    main.add_command(init_test)
    main.add_command(test)
    main.add_command(test_suite)
    main.add_command(gas_test)
