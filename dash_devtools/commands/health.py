"""health, stats 指令"""

import click
from dash_devtools.cli import console, DEFAULT_PROJECTS


@click.command()
@click.argument('project', type=click.Path(), default='.')
@click.option('--all', 'check_all', is_flag=True, help='檢查所有專案')
@click.option('--json', 'output_json', is_flag=True, help='輸出 JSON 格式')
def health(project, check_all, output_json):
    """專案健康評分

    類似 Lighthouse 的評分機制，量化專案品質：
    - 安全性: 機敏資料、依賴漏洞
    - 品質: 程式碼規範、檔案結構
    - 維護性: 技術債務、文件完整度
    - 效能: Bundle 大小、依賴數量

    使用範例：
      dash health .
      dash health /path/to/project
      dash health --all
    """
    from ..health import run_health_check, HealthChecker
    import json as json_module

    if check_all:
        projects = DEFAULT_PROJECTS
    else:
        projects = [project]

    results = []
    for p in projects:
        try:
            if output_json:
                checker = HealthChecker(p)
                scores = checker.check_all()
                total = sum(s.score for s in scores.values()) // len(scores)
                results.append({
                    'project': checker.project_name,
                    'total_score': total,
                    'scores': {k: v.score for k, v in scores.items()}
                })
            else:
                result = run_health_check(p)
                results.append(result)
        except Exception as e:
            console.print(f"[red]錯誤: {p} - {e}[/red]")

    if output_json:
        console.print(json_module.dumps(results, indent=2, ensure_ascii=False))


@click.command()
@click.argument('project', type=click.Path(), default='.')
@click.option('--all', 'stats_all', is_flag=True, help='統計所有專案並比較')
def stats(project, stats_all):
    """程式碼統計

    視覺化專案統計資訊：
    - 語言分佈
    - 檔案數量與行數
    - 最大檔案排行
    - 複雜度警告

    使用範例：
      dash stats .
      dash stats /path/to/project
      dash stats --all
    """
    from ..stats import run_stats, run_stats_all

    if stats_all:
        run_stats_all(DEFAULT_PROJECTS)
    else:
        run_stats(project)


def register(main):
    main.add_command(health)
    main.add_command(stats)
