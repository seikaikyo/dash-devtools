"""
整合報告產生器

產生完整的專案報告，包含：
- 健康評分
- 程式碼統計
- UI 截圖
- 測試結果
- HTML 報告輸出
"""

import base64
from pathlib import Path
from datetime import datetime
from typing import Dict, List

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from .reporters.report_data import (
    TestResult,
    ScreenshotResult,
    ReportData,
    collect_health,
    collect_stats,
    run_tests,
)
from .reporters.screenshot import take_screenshots

console = Console()


class ReportGenerator:
    """報告產生器"""

    def __init__(self, project_path: str):
        self.project_path = Path(project_path)
        self.project_name = self.project_path.name
        self.report_dir = self.project_path / 'reports'
        self.report_data = ReportData(
            project_name=self.project_name,
            generated_at=datetime.now().isoformat()
        )

    def collect_health(self) -> Dict:
        """收集健康評分"""
        health_data = collect_health(self.project_path)
        self.report_data.health_scores = health_data
        return health_data

    def collect_stats(self) -> Dict:
        """收集程式碼統計"""
        stats_data = collect_stats(self.project_path)
        self.report_data.stats = stats_data
        return stats_data

    def run_tests(self) -> TestResult:
        """執行測試"""
        result = run_tests(self.project_path)
        self.report_data.test_result = result
        return result

    def take_screenshots(self, urls: List[str] = None) -> List[ScreenshotResult]:
        """使用 agent-browser 截圖"""
        results = take_screenshots(self.project_path, self.report_dir, urls)
        self.report_data.screenshots = results
        return results

    def generate_html_report(self) -> str:
        """產生 HTML 報告"""
        self.report_dir.mkdir(parents=True, exist_ok=True)
        report_path = self.report_dir / f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"

        html = _build_html(self.report_data, self.project_name)

        report_path.write_text(html, encoding='utf-8')
        return str(report_path)


def _get_color(score):
    """取得評分顏色"""
    if score >= 90:
        return '#22c55e'  # green
    elif score >= 70:
        return '#eab308'  # yellow
    elif score >= 50:
        return '#f97316'  # orange
    else:
        return '#ef4444'  # red


def _build_lang_bars(stats: Dict) -> str:
    """產生語言分佈 HTML"""
    languages_data = stats.get('languages', {})
    total_lines = stats.get('total_lines', 1)

    lang_bars = ""
    colors = ['#3b82f6', '#22c55e', '#eab308', '#ef4444', '#8b5cf6', '#06b6d4', '#f97316', '#ec4899']
    for i, (name, data) in enumerate(sorted(languages_data.items(), key=lambda x: x[1]['lines'], reverse=True)[:6]):
        pct = (data['lines'] / total_lines) * 100
        color = colors[i % len(colors)]
        lang_bars += f'''
            <div class="lang-bar">
                <span class="lang-name">{name}</span>
                <div class="bar-container">
                    <div class="bar-fill" style="width: {pct}%; background: {color};"></div>
                </div>
                <span class="lang-pct">{pct:.1f}%</span>
            </div>
            '''

    return lang_bars


def _build_score_cards(health: Dict) -> str:
    """產生健康評分卡片 HTML"""
    score_cards = ""
    for key, data in health.get('scores', {}).items():
        score = data['score']
        category = data['category']
        score_cards += f'''
            <div class="score-card">
                <div class="score-value" style="color: {_get_color(score)}">{score}</div>
                <div class="score-label">{category}</div>
            </div>
            '''
    return score_cards


def _build_test_html(test_result) -> str:
    """產生測試結果 HTML"""
    if not test_result:
        return ""

    tr = test_result
    test_status = "PASS" if tr.success else "FAIL"
    test_color = "#22c55e" if tr.success else "#ef4444"
    return f'''
            <div class="section">
                <h2>測試結果</h2>
                <div class="test-result">
                    <div class="test-status" style="background: {test_color}">{test_status}</div>
                    <div class="test-stats">
                        <span class="passed">{tr.passed} passed</span>
                        <span class="failed">{tr.failed} failed</span>
                    </div>
                    <div class="test-framework">Framework: {tr.framework}</div>
                </div>
            </div>
            '''


def _build_screenshots_html(screenshots: list) -> str:
    """產生截圖 HTML"""
    screenshots_html = ""
    for ss in screenshots:
        if ss.success and Path(ss.path).exists():
            img_data = base64.b64encode(Path(ss.path).read_bytes()).decode()
            screenshots_html += f'''
                <div class="screenshot">
                    <div class="screenshot-url">{ss.url}</div>
                    <img src="data:image/png;base64,{img_data}" alt="Screenshot" />
                </div>
                '''

    if screenshots_html:
        screenshots_html = f'''
            <div class="section">
                <h2>UI 截圖</h2>
                <div class="screenshots-grid">
                    {screenshots_html}
                </div>
            </div>
            '''
    return screenshots_html


def _build_issues_html(health: Dict) -> tuple:
    """產生問題與建議 HTML"""
    issues_html = ""
    recommendations_html = ""
    for data in health.get('scores', {}).values():
        for issue in data.get('issues', []):
            issues_html += f'<li class="issue">{issue}</li>'
        for rec in data.get('recommendations', []):
            recommendations_html += f'<li class="recommendation">{rec}</li>'
    return issues_html, recommendations_html


def _build_html(report_data: ReportData, project_name: str) -> str:
    """組裝完整 HTML 報告"""
    health = report_data.health_scores
    total_score = health.get('total_score', 0)

    lang_bars = _build_lang_bars(report_data.stats)
    score_cards = _build_score_cards(health)
    test_html = _build_test_html(report_data.test_result)
    screenshots_html = _build_screenshots_html(report_data.screenshots)
    issues_html, recommendations_html = _build_issues_html(health)

    html = f'''<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{project_name} - 專案報告</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0f172a;
            color: #e2e8f0;
            line-height: 1.6;
            padding: 2rem;
        }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        .header {{
            text-align: center;
            padding: 2rem;
            background: linear-gradient(135deg, #1e293b, #334155);
            border-radius: 1rem;
            margin-bottom: 2rem;
        }}
        .header h1 {{ font-size: 2rem; margin-bottom: 0.5rem; }}
        .header .date {{ color: #94a3b8; font-size: 0.875rem; }}
        .total-score {{
            font-size: 4rem;
            font-weight: bold;
            color: {_get_color(total_score)};
            margin: 1rem 0;
        }}
        .section {{
            background: #1e293b;
            border-radius: 1rem;
            padding: 1.5rem;
            margin-bottom: 1.5rem;
        }}
        .section h2 {{
            font-size: 1.25rem;
            margin-bottom: 1rem;
            color: #38bdf8;
        }}
        .scores-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 1rem;
        }}
        .score-card {{
            background: #334155;
            padding: 1rem;
            border-radius: 0.5rem;
            text-align: center;
        }}
        .score-value {{ font-size: 2rem; font-weight: bold; }}
        .score-label {{ color: #94a3b8; font-size: 0.875rem; }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 1rem;
        }}
        .stat-item {{
            background: #334155;
            padding: 1rem;
            border-radius: 0.5rem;
            text-align: center;
        }}
        .stat-value {{ font-size: 1.5rem; font-weight: bold; color: #38bdf8; }}
        .stat-label {{ color: #94a3b8; font-size: 0.75rem; }}
        .lang-bar {{
            display: flex;
            align-items: center;
            margin-bottom: 0.5rem;
        }}
        .lang-name {{ width: 100px; font-size: 0.875rem; }}
        .bar-container {{
            flex: 1;
            height: 8px;
            background: #334155;
            border-radius: 4px;
            overflow: hidden;
            margin: 0 1rem;
        }}
        .bar-fill {{ height: 100%; border-radius: 4px; }}
        .lang-pct {{ width: 60px; text-align: right; font-size: 0.875rem; color: #94a3b8; }}
        .test-result {{
            display: flex;
            align-items: center;
            gap: 1rem;
        }}
        .test-status {{
            padding: 0.5rem 1rem;
            border-radius: 0.25rem;
            font-weight: bold;
        }}
        .test-stats .passed {{ color: #22c55e; }}
        .test-stats .failed {{ color: #ef4444; margin-left: 1rem; }}
        .test-framework {{ color: #94a3b8; margin-left: auto; }}
        .issues-list, .recommendations-list {{
            list-style: none;
            padding-left: 0;
        }}
        .issue, .recommendation {{
            padding: 0.5rem 1rem;
            margin-bottom: 0.5rem;
            border-radius: 0.25rem;
            font-size: 0.875rem;
        }}
        .issue {{ background: rgba(239, 68, 68, 0.1); border-left: 3px solid #ef4444; }}
        .recommendation {{ background: rgba(234, 179, 8, 0.1); border-left: 3px solid #eab308; }}
        .screenshots-grid {{ display: grid; gap: 1rem; }}
        .screenshot img {{
            max-width: 100%;
            border-radius: 0.5rem;
            border: 1px solid #334155;
        }}
        .screenshot-url {{
            font-size: 0.75rem;
            color: #94a3b8;
            margin-bottom: 0.5rem;
        }}
        .footer {{
            text-align: center;
            color: #64748b;
            font-size: 0.75rem;
            margin-top: 2rem;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{project_name}</h1>
            <div class="date">報告產生時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
            <div class="total-score">{total_score}/100</div>
        </div>

        <div class="section">
            <h2>健康評分</h2>
            <div class="scores-grid">
                {score_cards}
            </div>
        </div>

        <div class="section">
            <h2>程式碼統計</h2>
            <div class="stats-grid">
                <div class="stat-item">
                    <div class="stat-value">{report_data.stats.get('total_files', 0):,}</div>
                    <div class="stat-label">檔案數</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">{report_data.stats.get('total_lines', 0):,}</div>
                    <div class="stat-label">總行數</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">{report_data.stats.get('total_code_lines', 0):,}</div>
                    <div class="stat-label">程式碼行數</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">{report_data.stats.get('size_bytes', 0) / 1024:.0f} KB</div>
                    <div class="stat-label">大小</div>
                </div>
            </div>
        </div>

        <div class="section">
            <h2>語言分佈</h2>
            {lang_bars}
        </div>

        {test_html}

        {screenshots_html}

        <div class="section">
            <h2>問題與建議</h2>
            <h3 style="color: #ef4444; font-size: 0.875rem; margin-bottom: 0.5rem;">問題</h3>
            <ul class="issues-list">{issues_html if issues_html else '<li style="color: #94a3b8;">無問題</li>'}</ul>
            <h3 style="color: #eab308; font-size: 0.875rem; margin: 1rem 0 0.5rem;">建議</h3>
            <ul class="recommendations-list">{recommendations_html if recommendations_html else '<li style="color: #94a3b8;">無建議</li>'}</ul>
        </div>

        <div class="footer">
            Generated by DashAI DevTools v2.0
        </div>
    </div>
</body>
</html>'''

    return html


def run_report(project_path: str, include_tests: bool = True,
               include_screenshots: bool = False, urls: List[str] = None,
               open_browser: bool = True) -> dict:
    """產生完整報告"""

    generator = ReportGenerator(project_path)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:

        # 收集健康評分
        task = progress.add_task("收集健康評分...", total=None)
        generator.collect_health()
        progress.update(task, description="[green]健康評分 ✓")

        # 收集統計
        task = progress.add_task("收集程式碼統計...", total=None)
        generator.collect_stats()
        progress.update(task, description="[green]程式碼統計 ✓")

        # 執行測試
        if include_tests:
            task = progress.add_task("執行測試...", total=None)
            test_result = generator.run_tests()
            if test_result.framework != 'unknown':
                status = "[green]✓" if test_result.success else "[red]✗"
                progress.update(task, description=f"{status} 測試完成 ({test_result.framework})")
            else:
                progress.update(task, description="[yellow]跳過測試 (未偵測到測試框架)")

        # 截圖
        if include_screenshots:
            task = progress.add_task("擷取截圖...", total=None)
            screenshots = generator.take_screenshots(urls)
            success_count = sum(1 for s in screenshots if s.success)
            progress.update(task, description=f"[green]截圖完成 ({success_count}/{len(screenshots)})")

        # 產生報告
        task = progress.add_task("產生 HTML 報告...", total=None)
        report_path = generator.generate_html_report()
        progress.update(task, description="[green]報告已產生 ✓")

    console.print()
    console.print(f"[green]報告已產生:[/green] {report_path}")

    # 開啟瀏覽器
    if open_browser:
        try:
            import webbrowser
            webbrowser.open(f'file://{report_path}')
        except Exception:
            pass

    return {
        'success': True,
        'report_path': report_path,
        'health_score': generator.report_data.health_scores.get('total_score', 0)
    }
