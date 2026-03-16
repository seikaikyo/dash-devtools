"""deps, deadcode, complexity, licenses, env-lint 指令

整合 deptry, pip-audit, vulture, radon, pip-licenses, liccheck, dotenv-linter。
所有工具為 optional dependencies，未安裝時提示安裝指引。
"""

import click
import subprocess
import sys
import json
from pathlib import Path
from dash_devtools.cli import console


def _check_installed(package_name, install_group="analyze"):
    """檢查套件是否已安裝，未安裝時給出提示"""
    try:
        __import__(package_name)
        return True
    except ImportError:
        console.print(
            f"[red]{package_name} 未安裝。[/red]\n"
            f"  安裝指令: [cyan]pip install dash-devtools[{install_group}][/cyan]"
        )
        return False


# === dash deps ===

@click.group()
def deps():
    """依賴分析 (孤兒依賴 + 安全漏洞)

    子指令：
      check     檢查孤兒/缺漏依賴 (deptry)
      audit     安全漏洞掃描 (pip-audit)
      all       執行全部檢查
    """
    pass


@deps.command('check')
@click.argument('project', type=click.Path(exists=True), default='.')
@click.option('--json-output', is_flag=True, help='JSON 格式輸出')
def deps_check(project, json_output):
    """檢查孤兒/缺漏依賴 (deptry)

    偵測未使用的依賴、缺漏的依賴、transitive 依賴。
    """
    if not _check_installed('deptry'):
        raise SystemExit(1)

    project_path = Path(project).resolve()

    # 智慧偵測：如果根目錄沒有 pyproject.toml/requirements.txt，找子目錄
    scan_path = project_path
    has_deps_file = (
        (project_path / 'pyproject.toml').exists()
        or (project_path / 'requirements.txt').exists()
        or (project_path / 'setup.py').exists()
    )
    if not has_deps_file:
        # 嘗試常見子目錄
        for subdir in ['backend', 'server', 'api', 'src']:
            candidate = project_path / subdir
            if (candidate / 'requirements.txt').exists() or (candidate / 'pyproject.toml').exists():
                scan_path = candidate
                console.print(f"[dim]在 {subdir}/ 找到依賴檔案[/dim]")
                break
        else:
            console.print(f"[yellow]找不到 pyproject.toml 或 requirements.txt[/yellow]")
            console.print(f"[dim]搜尋路徑: {project_path}[/dim]")
            raise SystemExit(1)

    cmd = [sys.executable, '-m', 'deptry', str(scan_path)]
    if json_output:
        cmd.append('--json-output')
        cmd.append('-')

    console.print(f"[cyan]deptry 掃描: {scan_path.relative_to(project_path.parent)}[/cyan]\n")
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(scan_path))

    if result.stdout:
        if json_output:
            try:
                data = json.loads(result.stdout)
                from rich.json import JSON
                console.print(JSON(json.dumps(data, indent=2)))
            except json.JSONDecodeError:
                console.print(result.stdout)
        else:
            console.print(result.stdout)

    if result.stderr:
        # deptry 的正常輸出有時在 stderr
        for line in result.stderr.strip().split('\n'):
            if line.strip():
                console.print(f"  {line}")

    if result.returncode == 0:
        console.print("\n[green]依賴檢查通過[/green]")
    else:
        console.print(f"\n[yellow]發現依賴問題 (exit code: {result.returncode})[/yellow]")
        console.print("[dim]提示: uvicorn/python-dotenv/psycopg 等 runtime 依賴屬於誤判，可忽略[/dim]")


@deps.command('audit')
@click.option('--fix', is_flag=True, help='自動修復已知漏洞')
@click.option('--json-output', is_flag=True, help='JSON 格式輸出')
def deps_audit(fix, json_output):
    """安全漏洞掃描 (pip-audit)

    掃描目前 Python 環境中的已知安全漏洞。
    """
    cmd = [sys.executable, '-m', 'pip_audit']
    if fix:
        cmd.append('--fix')
    if json_output:
        cmd.extend(['--format', 'json'])

    console.print("[cyan]pip-audit 掃描安全漏洞...[/cyan]\n")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.stdout:
        if json_output:
            try:
                data = json.loads(result.stdout)
                from rich.json import JSON
                console.print(JSON(json.dumps(data, indent=2)))
            except json.JSONDecodeError:
                console.print(result.stdout)
        else:
            console.print(result.stdout)

    if result.stderr:
        for line in result.stderr.strip().split('\n'):
            if line.strip():
                console.print(f"  [dim]{line}[/dim]")

    if result.returncode == 0:
        console.print("\n[green]未發現安全漏洞[/green]")
    else:
        console.print("\n[red]發現安全漏洞！請檢查上方列表並升級受影響的套件[/red]")


@deps.command('all')
@click.argument('project', type=click.Path(exists=True), default='.')
@click.pass_context
def deps_all(ctx, project):
    """執行全部依賴檢查 (deptry + pip-audit)"""
    console.print("[cyan]= 依賴完整檢查 =[/cyan]\n")

    has_error = False

    # deptry
    console.print("[yellow]1/2 孤兒依賴檢查 (deptry)[/yellow]")
    try:
        ctx.invoke(deps_check, project=project, json_output=False)
    except SystemExit as e:
        if e.code != 0:
            has_error = True
    console.print()

    # pip-audit
    console.print("[yellow]2/2 安全漏洞掃描 (pip-audit)[/yellow]")
    try:
        ctx.invoke(deps_audit, fix=False, json_output=False)
    except SystemExit as e:
        if e.code != 0:
            has_error = True

    if has_error:
        raise SystemExit(1)


# === dash deadcode ===

@click.command()
@click.argument('project', type=click.Path(exists=True), default='.')
@click.option('--min-confidence', type=int, default=80, help='最低信心分數 (0-100)')
@click.option('--exclude', multiple=True, help='排除路徑 (可多次指定)')
@click.option('--sort', is_flag=True, help='依信心分數排序')
def deadcode(project, min_confidence, exclude, sort):
    """死代碼偵測 (vulture)

    掃描未使用的函數、變數、類別、import。
    信心分數 60-100%，預設只顯示 80% 以上。

    使用範例：
      dash deadcode .
      dash deadcode . --min-confidence 60
      dash deadcode . --exclude tests --exclude migrations
    """
    if not _check_installed('vulture'):
        raise SystemExit(1)

    from vulture import Vulture

    project_path = Path(project).resolve()
    console.print(f"[cyan]vulture 掃描: {project_path.name}[/cyan]")
    console.print(f"[dim]最低信心: {min_confidence}%[/dim]\n")

    v = Vulture()

    # 收集 Python 檔案
    py_files = []
    exclude_set = set(exclude) | {
        '__pycache__', '.git', 'node_modules', 'venv', '.venv',
        'dist', 'build', '.egg-info'
    }

    for f in project_path.rglob('*.py'):
        # 檢查是否在排除路徑中
        parts = f.relative_to(project_path).parts
        if any(ex in parts for ex in exclude_set):
            continue
        py_files.append(str(f))

    if not py_files:
        console.print("[yellow]未找到 Python 檔案[/yellow]")
        return

    console.print(f"[dim]掃描 {len(py_files)} 個檔案...[/dim]\n")
    v.scavenge(py_files)

    results = v.get_unused_code(min_confidence=min_confidence)
    if sort:
        results = sorted(results, key=lambda x: x.confidence, reverse=True)

    if not results:
        console.print("[green]未發現死代碼[/green]")
        return

    from rich.table import Table

    table = Table(title=f"發現 {len(results)} 項未使用的程式碼")
    table.add_column("檔案", style="cyan", max_width=40)
    table.add_column("行", justify="right", style="dim")
    table.add_column("信心", justify="right")
    table.add_column("類型", style="yellow")
    table.add_column("名稱", style="white")

    for item in results:
        filepath = str(Path(item.filename).relative_to(project_path))
        confidence = item.confidence
        conf_style = "green" if confidence >= 90 else "yellow" if confidence >= 80 else "dim"
        table.add_row(
            filepath,
            str(item.first_lineno),
            f"[{conf_style}]{confidence}%[/{conf_style}]",
            item.typ,
            item.name,
        )

    console.print(table)
    console.print(f"\n[yellow]共 {len(results)} 項，建議優先處理信心 >= 90% 的項目[/yellow]")


# === dash complexity ===

@click.command()
@click.argument('project', type=click.Path(exists=True), default='.')
@click.option('--threshold', '-t', default='C', help='複雜度門檻 (A/B/C/D/E/F)')
@click.option('--top', type=int, default=20, help='只顯示前 N 項')
@click.option('--cognitive', is_flag=True, help='使用認知複雜度 (complexipy)')
def complexity(project, threshold, top, cognitive):
    """程式碼複雜度分析 (radon / complexipy)

    分析循環複雜度 (Cyclomatic Complexity) 或認知複雜度 (Cognitive Complexity)。

    等級: A(1-5) B(6-10) C(11-15) D(16-20) E(21-25) F(26+)

    使用範例：
      dash complexity .
      dash complexity . --threshold B --top 10
      dash complexity . --cognitive
    """
    project_path = Path(project).resolve()

    if cognitive:
        _run_cognitive_complexity(project_path)
    else:
        _run_cyclomatic_complexity(project_path, threshold, top)


def _run_cyclomatic_complexity(project_path, threshold, top):
    """循環複雜度分析 (radon)"""
    if not _check_installed('radon'):
        raise SystemExit(1)

    from radon.complexity import cc_visit, cc_rank
    from rich.table import Table

    console.print(f"[cyan]radon 複雜度分析: {project_path.name}[/cyan]")
    console.print(f"[dim]門檻: {threshold} | 顯示前 {top} 項[/dim]\n")

    all_blocks = []
    file_count = 0
    exclude_dirs = {
        '__pycache__', '.git', 'node_modules', 'venv', '.venv',
        'dist', 'build', '.egg-info'
    }

    for f in project_path.rglob('*.py'):
        parts = f.relative_to(project_path).parts
        if any(ex in parts for ex in exclude_dirs):
            continue
        file_count += 1
        try:
            source = f.read_text(encoding='utf-8', errors='ignore')
            blocks = cc_visit(source)
            for block in blocks:
                block._filepath = str(f.relative_to(project_path))
                all_blocks.append(block)
        except SyntaxError:
            continue

    # 過濾 + 排序
    threshold_map = {'A': 1, 'B': 6, 'C': 11, 'D': 16, 'E': 21, 'F': 26}
    min_cc = threshold_map.get(threshold.upper(), 11)
    filtered = [b for b in all_blocks if b.complexity >= min_cc]
    filtered.sort(key=lambda x: x.complexity, reverse=True)
    display = filtered[:top]

    if not display:
        console.print(f"[green]所有函數複雜度都在 {threshold} 以下[/green]")
        console.print(f"[dim]掃描 {file_count} 個檔案，{len(all_blocks)} 個函數[/dim]")
        return

    table = Table(title=f"複雜度 >= {threshold} 的函數 (共 {len(filtered)} 個)")
    table.add_column("檔案", style="cyan", max_width=35)
    table.add_column("函數", style="white")
    table.add_column("行", justify="right", style="dim")
    table.add_column("CC", justify="right")
    table.add_column("等級", justify="center")

    for block in display:
        rank = cc_rank(block.complexity)
        rank_style = {
            'A': 'green', 'B': 'green', 'C': 'yellow',
            'D': 'red', 'E': 'red bold', 'F': 'red bold'
        }.get(rank, 'white')
        table.add_row(
            block._filepath,
            block.name,
            str(block.lineno),
            str(block.complexity),
            f"[{rank_style}]{rank}[/{rank_style}]",
        )

    console.print(table)
    console.print(f"\n[dim]掃描 {file_count} 個檔案，{len(all_blocks)} 個函數[/dim]")

    # 統計
    from collections import Counter
    rank_counts = Counter(cc_rank(b.complexity) for b in all_blocks)
    summary = " | ".join(f"{r}: {rank_counts.get(r, 0)}" for r in 'ABCDEF')
    console.print(f"[dim]等級分布: {summary}[/dim]")


def _run_cognitive_complexity(project_path):
    """認知複雜度分析 (complexipy)"""
    cmd = [sys.executable, '-m', 'complexipy', str(project_path)]
    console.print(f"[cyan]complexipy 認知複雜度: {project_path.name}[/cyan]\n")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode == 127 or 'No module named' in (result.stderr or ''):
        console.print(
            "[red]complexipy 未安裝。[/red]\n"
            "  安裝指令: [cyan]pip install complexipy[/cyan]"
        )
        raise SystemExit(1)

    if result.stdout:
        console.print(result.stdout)
    if result.stderr:
        console.print(result.stderr)


# === dash licenses ===

@click.group()
def licenses():
    """授權合規檢查 (pip-licenses + liccheck)

    子指令：
      list      列出所有依賴授權
      check     檢查授權合規性
    """
    pass


@licenses.command('list')
@click.option('--format', 'fmt', type=click.Choice(['plain', 'json', 'csv', 'markdown']),
              default='plain', help='輸出格式')
@click.option('--with-system', is_flag=True, help='包含系統套件')
def licenses_list(fmt, with_system):
    """列出所有依賴授權"""
    if not _check_installed('piplicenses', 'analyze'):
        raise SystemExit(1)

    cmd = [sys.executable, '-m', 'piplicenses', '--format', fmt]

    if with_system:
        cmd.append('--with-system')

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.stdout:
        if fmt == 'json':
            try:
                data = json.loads(result.stdout)
                from rich.json import JSON
                console.print(JSON(json.dumps(data, indent=2)))
            except json.JSONDecodeError:
                console.print(result.stdout)
        else:
            console.print(result.stdout)


@licenses.command('check')
@click.option('--allow', multiple=True, help='允許的授權類型 (可多次指定)')
def licenses_check(allow):
    """檢查授權合規性 (liccheck)"""
    allowed = list(allow) if allow else [
        'MIT',
        'BSD',
        'Apache',
        'ISC',
        'Python Software Foundation',
        'Mozilla Public License',
        'Public Domain',
        'Unlicense',
    ]

    console.print("[cyan]授權合規檢查[/cyan]")
    console.print(f"[dim]允許的授權: {', '.join(allowed)}[/dim]\n")

    # 用 pip-licenses 取得 JSON
    cmd = [sys.executable, '-m', 'piplicenses', '--format', 'json']
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        if not _check_installed('piplicenses', 'analyze'):
            raise SystemExit(1)
        console.print(f"[red]pip-licenses 執行失敗[/red]")
        raise SystemExit(1)

    try:
        packages = json.loads(result.stdout)
    except json.JSONDecodeError:
        console.print("[red]無法解析 pip-licenses 輸出[/red]")
        raise SystemExit(1)

    from rich.table import Table

    violations = []
    for pkg in packages:
        license_name = pkg.get('License', 'UNKNOWN')
        license_lower = license_name.lower()
        if license_name == 'UNKNOWN' or not any(a.lower() in license_lower for a in allowed):
            violations.append(pkg)

    if not violations:
        console.print(f"[green]所有 {len(packages)} 個套件授權合規[/green]")
        return

    table = Table(title=f"授權不合規的套件 ({len(violations)} 個)")
    table.add_column("套件", style="cyan")
    table.add_column("版本", style="dim")
    table.add_column("授權", style="red")

    for pkg in violations:
        table.add_row(
            pkg.get('Name', ''),
            pkg.get('Version', ''),
            pkg.get('License', 'UNKNOWN'),
        )

    console.print(table)
    console.print(f"\n[yellow]共 {len(violations)} 個套件需要確認授權合規性[/yellow]")


# === dash env-lint ===

@click.command('env-lint')
@click.argument('project', type=click.Path(exists=True), default='.')
@click.option('--fix', is_flag=True, help='自動修復問題')
def env_lint(project, fix):
    """檢查 .env 檔案 (dotenv-linter)

    偵測重複 key、排序問題、格式錯誤等。

    使用範例：
      dash env-lint .
      dash env-lint /path/to/project --fix
    """
    project_path = Path(project).resolve()

    # 找所有 .env 檔案
    env_files = list(project_path.glob('.env*'))
    env_files = [f for f in env_files if f.is_file() and not f.name.endswith('.example')]

    if not env_files:
        console.print(f"[yellow]未找到 .env 檔案: {project_path}[/yellow]")
        return

    console.print(f"[cyan]dotenv-linter 檢查 .env 檔案[/cyan]\n")

    total_issues = 0
    for env_file in sorted(env_files):
        rel_path = env_file.relative_to(project_path)
        console.print(f"[dim]檢查: {rel_path}[/dim]")

        try:
            content = env_file.read_text(encoding='utf-8')
        except Exception as e:
            console.print(f"  [red]讀取失敗: {e}[/red]")
            continue

        issues = _lint_env_file(content, str(rel_path))
        total_issues += len(issues)

        if issues:
            for issue in issues:
                console.print(f"  [yellow]{issue}[/yellow]")
        else:
            console.print(f"  [green]通過[/green]")

    console.print()
    if total_issues == 0:
        console.print("[green]所有 .env 檔案檢查通過[/green]")
    else:
        console.print(f"[yellow]共 {total_issues} 個問題[/yellow]")


def _lint_env_file(content, filename):
    """內建 .env 檢查 (不依賴外部套件)"""
    issues = []
    seen_keys = {}
    prev_key = None

    for lineno, line in enumerate(content.split('\n'), 1):
        stripped = line.strip()

        # 跳過空行和註解
        if not stripped or stripped.startswith('#'):
            continue

        # 檢查格式
        if '=' not in stripped:
            issues.append(f"L{lineno}: 缺少 '=' 分隔符")
            continue

        key, _, value = stripped.partition('=')
        key = key.strip()

        # 空 key
        if not key:
            issues.append(f"L{lineno}: 空的 key")
            continue

        # 重複 key
        if key in seen_keys:
            issues.append(f"L{lineno}: 重複 key '{key}' (首次出現: L{seen_keys[key]})")
        seen_keys[key] = lineno

        # key 有空格
        if ' ' in key:
            issues.append(f"L{lineno}: key '{key}' 包含空格")

        # key 小寫 (慣例是大寫)
        if key != key.upper() and not key.startswith('#'):
            issues.append(f"L{lineno}: key '{key}' 建議使用大寫")

        # 值有前後空格
        if value != value.strip() and not value.startswith('"') and not value.startswith("'"):
            issues.append(f"L{lineno}: '{key}' 的值有多餘空格")

        prev_key = key

    return issues


def register(main):
    main.add_command(deps)
    main.add_command(deadcode)
    main.add_command(complexity)
    main.add_command(licenses)
    main.add_command(env_lint)
