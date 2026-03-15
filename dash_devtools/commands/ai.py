"""ai group + 子指令 + _handle_ai_error"""

import click
from dash_devtools.cli import console


def _handle_ai_error(e: Exception) -> None:
    """處理 AI 相關錯誤，提供精確的修復建議"""
    error_msg = str(e).lower()

    if 'google.genai' in error_msg or 'google-genai' in error_msg:
        console.print("[red]缺少 Google GenAI SDK[/red]")
        console.print("[yellow]請執行: pip install google-genai[/yellow]")
    elif 'dotenv' in error_msg:
        console.print("[red]缺少 python-dotenv[/red]")
        console.print("[yellow]請執行: pip install python-dotenv[/yellow]")
    elif 'gemini_api_key' in error_msg:
        # 顯示完整的錯誤訊息（包含診斷資訊）
        console.print(f"[red]{e}[/red]")
    elif isinstance(e, ImportError):
        console.print(f"[red]模組載入失敗: {e}[/red]")
        console.print("[yellow]請執行: pip install google-genai python-dotenv[/yellow]")
    elif isinstance(e, ValueError):
        console.print(f"[red]設定錯誤: {e}[/red]")
    else:
        console.print(f"[red]錯誤: {e}[/red]")


@click.group()
def ai():
    """AI 程式碼助手 (Gemini 2.5)

    使用 Google GenAI SDK (新版)。
    需設定環境變數 GEMINI_API_KEY。

    子指令：
      analyze   分析程式碼
      fix       建議修復方案
      test      生成測試
      explain   解釋程式碼
      review    審查 commit
    """
    pass


@ai.command()
@click.argument('file', type=click.Path())
@click.option('--focus', '-f', type=click.Choice(['general', 'security', 'performance', 'quality']),
              default='general', help='分析重點')
def analyze(file, focus):
    """分析程式碼

    使用範例：
      dash ai analyze src/main.py
      dash ai analyze src/api.ts --focus security
    """
    try:
        from ..ai_engine import get_ai
        ai_engine = get_ai()

        with open(file, 'r', encoding='utf-8') as f:
            code = f.read()

        console.print(f"[cyan]分析中: {file}[/cyan]")
        console.print(f"[dim]重點: {focus}[/dim]\n")

        response = ai_engine.analyze_code(code, focus=focus)
        if response.success:
            console.print(response.content)
        else:
            console.print(f"[red]錯誤: {response.error}[/red]")
    except Exception as e:
        _handle_ai_error(e)


@ai.command()
@click.argument('file', type=click.Path())
@click.option('--error', '-e', required=True, help='錯誤訊息')
def fix(file, error):
    """建議修復方案

    使用範例：
      dash ai fix src/main.py -e "TypeError: Cannot read property"
    """
    try:
        from ..ai_engine import get_ai
        ai_engine = get_ai()

        with open(file, 'r', encoding='utf-8') as f:
            code = f.read()

        console.print(f"[cyan]分析錯誤: {file}[/cyan]\n")

        response = ai_engine.suggest_fix(code, error)
        if response.success:
            console.print(response.content)
        else:
            console.print(f"[red]錯誤: {response.error}[/red]")
    except Exception as e:
        _handle_ai_error(e)


@ai.command('test')
@click.argument('file', type=click.Path())
@click.option('--framework', '-f', default='auto', help='測試框架 (auto/pytest/jest/vitest)')
@click.option('--coverage', '-c', type=click.Choice(['basic', 'comprehensive', 'edge-cases']),
              default='comprehensive', help='覆蓋範圍')
def generate_test(file, framework, coverage):
    """生成測試程式碼

    使用範例：
      dash ai test src/utils.py
      dash ai test src/api.ts --framework jest
    """
    try:
        from ..ai_engine import get_ai
        ai_engine = get_ai()

        with open(file, 'r', encoding='utf-8') as f:
            code = f.read()

        console.print(f"[cyan]產生測試: {file}[/cyan]\n")

        response = ai_engine.generate_tests(code, framework=framework, coverage=coverage)
        if response.success:
            console.print(response.content)
        else:
            console.print(f"[red]錯誤: {response.error}[/red]")
    except Exception as e:
        _handle_ai_error(e)


@ai.command()
@click.argument('file', type=click.Path())
@click.option('--detail', '-d', type=click.Choice(['brief', 'medium', 'detailed']),
              default='medium', help='詳細程度')
def explain(file, detail):
    """解釋程式碼

    使用範例：
      dash ai explain src/complex-algo.py
      dash ai explain src/auth.ts --detail detailed
    """
    try:
        from ..ai_engine import get_ai
        ai_engine = get_ai()

        with open(file, 'r', encoding='utf-8') as f:
            code = f.read()

        console.print(f"[cyan]解釋: {file}[/cyan]\n")

        response = ai_engine.explain_code(code, detail_level=detail)
        if response.success:
            console.print(response.content)
        else:
            console.print(f"[red]錯誤: {response.error}[/red]")
    except Exception as e:
        _handle_ai_error(e)


@ai.command()
@click.argument('project', type=click.Path(), default='.')
def review(project):
    """審查最新 commit

    使用範例：
      dash ai review .
    """
    import subprocess
    try:
        from ..ai_engine import get_ai
        ai_engine = get_ai()

        # 取得最新 commit 的 diff
        result = subprocess.run(
            ['git', 'diff', 'HEAD~1', 'HEAD'],
            cwd=project,
            capture_output=True,
            text=True
        )
        diff = result.stdout

        # 取得 commit message
        msg_result = subprocess.run(
            ['git', 'log', '-1', '--pretty=%B'],
            cwd=project,
            capture_output=True,
            text=True
        )
        commit_msg = msg_result.stdout.strip()

        console.print(f"[cyan]審查 commit: {commit_msg[:50]}...[/cyan]\n")

        response = ai_engine.review_commit(diff, commit_msg)
        if response.success:
            console.print(response.content)
        else:
            console.print(f"[red]錯誤: {response.error}[/red]")
    except Exception as e:
        _handle_ai_error(e)


def register(main):
    main.add_command(ai)
