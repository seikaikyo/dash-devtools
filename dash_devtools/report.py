"""
整合報告產生器

產生完整的專案報告，包含：
- 健康評分
- 程式碼統計
- UI 截圖
- 測試結果
- HTML 報告輸出
"""

import json
import subprocess
import base64
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()


@dataclass
class TestResult:
    """測試結果"""
    framework: str  # pytest, jest, vitest, etc.
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    duration: float = 0.0
    output: str = ""
    success: bool = True


@dataclass
class ScreenshotResult:
    """截圖結果"""
    url: str
    path: str
    success: bool = True
    error: str = ""


@dataclass
class ReportData:
    """報告資料"""
    project_name: str
    generated_at: str
    health_scores: Dict = field(default_factory=dict)
    stats: Dict = field(default_factory=dict)
    test_result: Optional[TestResult] = None
    screenshots: List[ScreenshotResult] = field(default_factory=list)


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
        from .health import HealthChecker

        checker = HealthChecker(str(self.project_path))
        scores = checker.check_all()

        health_data = {
            'total_score': sum(s.score for s in scores.values()) // len(scores),
            'scores': {}
        }

        for key, score in scores.items():
            health_data['scores'][key] = {
                'score': score.score,
                'category': score.category,
                'issues': score.issues,
                'recommendations': score.recommendations
            }

        self.report_data.health_scores = health_data
        return health_data

    def collect_stats(self) -> Dict:
        """收集程式碼統計"""
        from .stats import StatsCollector

        collector = StatsCollector(str(self.project_path))
        stats = collector.collect()

        stats_data = {
            'total_files': stats.total_files,
            'total_lines': stats.total_lines,
            'total_code_lines': stats.total_code_lines,
            'size_bytes': stats.total_size_bytes,
            'languages': {},
            'largest_files': stats.largest_files[:5],
            'complexity_issues': stats.complexity_issues
        }

        for name, lang in stats.languages.items():
            stats_data['languages'][name] = {
                'files': lang.files,
                'lines': lang.lines
            }

        self.report_data.stats = stats_data
        return stats_data

    def run_tests(self) -> TestResult:
        """執行測試"""
        result = TestResult(framework='unknown')

        # 偵測測試框架
        package_json = self.project_path / 'package.json'
        if package_json.exists():
            try:
                pkg = json.loads(package_json.read_text())
                deps = {**pkg.get('dependencies', {}), **pkg.get('devDependencies', {})}
                scripts = pkg.get('scripts', {})

                # 判斷測試框架
                if 'vitest' in deps:
                    result.framework = 'vitest'
                elif 'jest' in deps:
                    result.framework = 'jest'
                elif '@angular-devkit/build-angular' in deps:
                    result.framework = 'karma'

                # 執行測試
                if 'test' in scripts:
                    try:
                        proc = subprocess.run(
                            ['npm', 'test', '--', '--passWithNoTests', '--run'],
                            cwd=self.project_path,
                            capture_output=True,
                            text=True,
                            timeout=120
                        )
                        result.output = proc.stdout + proc.stderr
                        result.success = proc.returncode == 0

                        # 簡單解析結果
                        if 'passed' in result.output.lower():
                            result.passed = result.output.lower().count('passed')
                        if 'failed' in result.output.lower():
                            result.failed = result.output.lower().count('failed')

                    except subprocess.TimeoutExpired:
                        result.success = False
                        result.output = "測試超時 (120秒)"
                    except Exception as e:
                        result.success = False
                        result.output = str(e)

            except Exception:
                pass

        # Python 專案
        requirements = self.project_path / 'requirements.txt'
        pytest_ini = self.project_path / 'pytest.ini'
        if requirements.exists() or pytest_ini.exists():
            result.framework = 'pytest'
            try:
                proc = subprocess.run(
                    ['python', '-m', 'pytest', '--tb=short', '-q'],
                    cwd=self.project_path,
                    capture_output=True,
                    text=True,
                    timeout=120
                )
                result.output = proc.stdout + proc.stderr
                result.success = proc.returncode == 0

                # 解析 pytest 結果
                import re
                match = re.search(r'(\d+) passed', result.output)
                if match:
                    result.passed = int(match.group(1))
                match = re.search(r'(\d+) failed', result.output)
                if match:
                    result.failed = int(match.group(1))

            except Exception as e:
                result.output = str(e)
                result.success = False

        self.report_data.test_result = result
        return result

    def take_screenshots(self, urls: List[str] = None) -> List[ScreenshotResult]:
        """使用 Puppeteer 截圖"""
        results = []

        # 如果沒指定 URL，嘗試偵測本地開發伺服器
        if not urls:
            # 檢查常見的開發伺服器設定
            package_json = self.project_path / 'package.json'
            if package_json.exists():
                try:
                    pkg = json.loads(package_json.read_text())
                    scripts = pkg.get('scripts', {})
                    # 常見的開發伺服器埠號
                    if 'dev' in scripts or 'start' in scripts:
                        urls = ['http://localhost:5173', 'http://localhost:3000', 'http://localhost:4200']
                except Exception:
                    pass

        if not urls:
            return results

        # 確保報告目錄存在
        screenshots_dir = self.report_dir / 'screenshots'
        screenshots_dir.mkdir(parents=True, exist_ok=True)

        # 使用 Puppeteer 截圖
        for url in urls:
            screenshot_path = screenshots_dir / f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"

            try:
                # 嘗試使用 puppeteer
                script = f'''
                const puppeteer = require('puppeteer');
                (async () => {{
                    const browser = await puppeteer.launch({{ headless: 'new' }});
                    const page = await browser.newPage();
                    await page.setViewport({{ width: 1920, height: 1080 }});
                    try {{
                        await page.goto('{url}', {{ waitUntil: 'networkidle2', timeout: 10000 }});
                        await page.screenshot({{ path: '{screenshot_path}', fullPage: true }});
                        console.log('success');
                    }} catch (e) {{
                        console.log('error: ' + e.message);
                    }}
                    await browser.close();
                }})();
                '''

                proc = subprocess.run(
                    ['node', '-e', script],
                    cwd=self.project_path,
                    capture_output=True,
                    text=True,
                    timeout=30
                )

                if 'success' in proc.stdout:
                    results.append(ScreenshotResult(
                        url=url,
                        path=str(screenshot_path),
                        success=True
                    ))
                else:
                    results.append(ScreenshotResult(
                        url=url,
                        path="",
                        success=False,
                        error=proc.stdout + proc.stderr
                    ))

            except Exception as e:
                results.append(ScreenshotResult(
                    url=url,
                    path="",
                    success=False,
                    error=str(e)
                ))

        self.report_data.screenshots = results
        return results

    def generate_html_report(self) -> str:
        """產生 HTML 報告"""
        self.report_dir.mkdir(parents=True, exist_ok=True)
        report_path = self.report_dir / f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"

        # 取得評分顏色
        def get_color(score):
            if score >= 90:
                return '#22c55e'  # green
            elif score >= 70:
                return '#eab308'  # yellow
            elif score >= 50:
                return '#f97316'  # orange
            else:
                return '#ef4444'  # red

        # 語言分佈圖資料
        languages_data = self.report_data.stats.get('languages', {})
        total_lines = self.report_data.stats.get('total_lines', 1)

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

        # 健康評分卡片
        health = self.report_data.health_scores
        total_score = health.get('total_score', 0)
        score_cards = ""
        for key, data in health.get('scores', {}).items():
            score = data['score']
            category = data['category']
            score_cards += f'''
            <div class="score-card">
                <div class="score-value" style="color: {get_color(score)}">{score}</div>
                <div class="score-label">{category}</div>
            </div>
            '''

        # 測試結果
        test_html = ""
        if self.report_data.test_result:
            tr = self.report_data.test_result
            test_status = "PASS" if tr.success else "FAIL"
            test_color = "#22c55e" if tr.success else "#ef4444"
            test_html = f'''
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

        # 截圖
        screenshots_html = ""
        for ss in self.report_data.screenshots:
            if ss.success and Path(ss.path).exists():
                # 轉換為 base64
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

        # 問題與建議
        issues_html = ""
        recommendations_html = ""
        for data in health.get('scores', {}).values():
            for issue in data.get('issues', []):
                issues_html += f'<li class="issue">{issue}</li>'
            for rec in data.get('recommendations', []):
                recommendations_html += f'<li class="recommendation">{rec}</li>'

        html = f'''<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{self.project_name} - 專案報告</title>
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
            color: {get_color(total_score)};
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
            <h1>{self.project_name}</h1>
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
                    <div class="stat-value">{self.report_data.stats.get('total_files', 0):,}</div>
                    <div class="stat-label">檔案數</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">{self.report_data.stats.get('total_lines', 0):,}</div>
                    <div class="stat-label">總行數</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">{self.report_data.stats.get('total_code_lines', 0):,}</div>
                    <div class="stat-label">程式碼行數</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">{self.report_data.stats.get('size_bytes', 0) / 1024:.0f} KB</div>
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

        report_path.write_text(html, encoding='utf-8')
        return str(report_path)


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
