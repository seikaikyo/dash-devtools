"""
效能測試模組
使用 Lighthouse 進行網站效能分析
"""

import subprocess
import json
import tempfile
from pathlib import Path
from typing import Dict, List, Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()

# Lighthouse Node.js 腳本
LIGHTHOUSE_SCRIPT = '''
const { execSync } = require("child_process");

const url = process.argv[2];
const categories = process.argv[3] || "performance,accessibility,best-practices,seo";

try {
  // 使用 lighthouse CLI
  const result = execSync(
    `npx lighthouse "${url}" --output=json --quiet --chrome-flags="--headless --no-sandbox" --only-categories=${categories}`,
    {
      encoding: "utf-8",
      timeout: 120000,
      maxBuffer: 10 * 1024 * 1024
    }
  );

  const report = JSON.parse(result);

  // 擷取關鍵數據
  const output = {
    url: url,
    success: true,
    scores: {
      performance: Math.round((report.categories.performance?.score || 0) * 100),
      accessibility: Math.round((report.categories.accessibility?.score || 0) * 100),
      bestPractices: Math.round((report.categories["best-practices"]?.score || 0) * 100),
      seo: Math.round((report.categories.seo?.score || 0) * 100)
    },
    metrics: {
      fcp: report.audits["first-contentful-paint"]?.numericValue || 0,
      lcp: report.audits["largest-contentful-paint"]?.numericValue || 0,
      tbt: report.audits["total-blocking-time"]?.numericValue || 0,
      cls: report.audits["cumulative-layout-shift"]?.numericValue || 0,
      si: report.audits["speed-index"]?.numericValue || 0,
      tti: report.audits["interactive"]?.numericValue || 0
    },
    opportunities: [],
    diagnostics: []
  };

  // 擷取改善建議 (有節省時間的項目)
  for (const [id, audit] of Object.entries(report.audits)) {
    if (audit.details?.overallSavingsMs > 100) {
      output.opportunities.push({
        id: id,
        title: audit.title,
        savings: Math.round(audit.details.overallSavingsMs),
        description: audit.description?.substring(0, 150)
      });
    }
  }

  // 排序: 節省時間最多的優先
  output.opportunities.sort((a, b) => b.savings - a.savings);
  output.opportunities = output.opportunities.slice(0, 5);

  // 擷取診斷資訊
  const diagnosticIds = [
    "dom-size",
    "bootup-time",
    "mainthread-work-breakdown",
    "font-display",
    "uses-responsive-images"
  ];

  for (const id of diagnosticIds) {
    const audit = report.audits[id];
    if (audit && audit.score !== null && audit.score < 1) {
      output.diagnostics.push({
        id: id,
        title: audit.title,
        score: Math.round(audit.score * 100),
        displayValue: audit.displayValue || ""
      });
    }
  }

  console.log(JSON.stringify(output));

} catch (err) {
  console.log(JSON.stringify({
    url: url,
    success: false,
    error: err.message,
    scores: { performance: 0, accessibility: 0, bestPractices: 0, seo: 0 },
    metrics: {},
    opportunities: [],
    diagnostics: []
  }));
}
'''


def run_perf_test(
    url: str,
    categories: str = "performance,accessibility,best-practices,seo",
    timeout: int = 120000
) -> Dict:
    """
    執行 Lighthouse 效能測試

    Args:
        url: 要測試的網址
        categories: 要測試的類別
        timeout: 超時時間 (毫秒)

    Returns:
        測試結果字典
    """
    # 建立臨時腳本檔案
    with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
        f.write(LIGHTHOUSE_SCRIPT)
        script_path = f.name

    try:
        # 執行 Node.js 腳本
        result = subprocess.run(
            ['node', script_path, url, categories],
            capture_output=True,
            text=True,
            timeout=timeout / 1000 + 30,
            cwd=get_node_cwd()
        )

        if result.returncode != 0 and not result.stdout:
            return {
                'url': url,
                'success': False,
                'error': f"Script error: {result.stderr}",
                'scores': {'performance': 0, 'accessibility': 0, 'bestPractices': 0, 'seo': 0},
                'metrics': {},
                'opportunities': [],
                'diagnostics': []
            }

        # 解析 JSON 輸出
        try:
            return json.loads(result.stdout.strip())
        except json.JSONDecodeError:
            return {
                'url': url,
                'success': False,
                'error': f"Invalid JSON: {result.stdout[:200]}",
                'scores': {'performance': 0, 'accessibility': 0, 'bestPractices': 0, 'seo': 0},
                'metrics': {},
                'opportunities': [],
                'diagnostics': []
            }

    except subprocess.TimeoutExpired:
        return {
            'url': url,
            'success': False,
            'error': 'Timeout exceeded',
            'scores': {'performance': 0, 'accessibility': 0, 'bestPractices': 0, 'seo': 0},
            'metrics': {},
            'opportunities': [],
            'diagnostics': []
        }
    except FileNotFoundError:
        return {
            'url': url,
            'success': False,
            'error': 'Node.js not found',
            'scores': {'performance': 0, 'accessibility': 0, 'bestPractices': 0, 'seo': 0},
            'metrics': {},
            'opportunities': [],
            'diagnostics': []
        }
    finally:
        Path(script_path).unlink(missing_ok=True)


def get_node_cwd() -> str:
    """取得有 Node.js 的工作目錄"""
    return '/Users/dash/Documents/github/smai-process-vision'


def get_score_color(score: int) -> str:
    """根據分數取得顏色"""
    if score >= 90:
        return "green"
    elif score >= 50:
        return "yellow"
    else:
        return "red"


def get_score_emoji(score: int) -> str:
    """根據分數取得狀態符號"""
    if score >= 90:
        return "[green]OK[/green]"
    elif score >= 50:
        return "[yellow]!![/yellow]"
    else:
        return "[red]XX[/red]"


def format_time(ms: float) -> str:
    """格式化時間"""
    if ms >= 1000:
        return f"{ms/1000:.1f}s"
    return f"{ms:.0f}ms"


def print_perf_report(result: Dict, verbose: bool = False):
    """印出效能報告"""

    if not result.get('success', False):
        console.print(f"[red]測試失敗: {result.get('error', 'Unknown error')}[/red]")
        return

    scores = result.get('scores', {})
    metrics = result.get('metrics', {})

    # 分數表格
    score_table = Table(title="Lighthouse 效能評分", show_header=True)
    score_table.add_column("類別", style="cyan")
    score_table.add_column("分數", justify="right")
    score_table.add_column("狀態", justify="center")

    categories = [
        ("Performance", scores.get('performance', 0)),
        ("Accessibility", scores.get('accessibility', 0)),
        ("Best Practices", scores.get('bestPractices', 0)),
        ("SEO", scores.get('seo', 0))
    ]

    for name, score in categories:
        color = get_score_color(score)
        status = get_score_emoji(score)
        score_table.add_row(name, f"[{color}]{score}[/{color}]", status)

    console.print(score_table)
    console.print()

    # Core Web Vitals
    if metrics:
        vitals_table = Table(title="Core Web Vitals", show_header=True)
        vitals_table.add_column("指標", style="cyan")
        vitals_table.add_column("數值", justify="right")
        vitals_table.add_column("說明")

        vitals = [
            ("FCP", metrics.get('fcp', 0), "First Contentful Paint"),
            ("LCP", metrics.get('lcp', 0), "Largest Contentful Paint"),
            ("TBT", metrics.get('tbt', 0), "Total Blocking Time"),
            ("CLS", metrics.get('cls', 0), "Cumulative Layout Shift"),
            ("SI", metrics.get('si', 0), "Speed Index"),
            ("TTI", metrics.get('tti', 0), "Time to Interactive")
        ]

        for abbr, value, desc in vitals:
            if abbr == "CLS":
                formatted = f"{value:.3f}"
            else:
                formatted = format_time(value)
            vitals_table.add_row(abbr, formatted, desc)

        console.print(vitals_table)
        console.print()

    # 改善建議
    opportunities = result.get('opportunities', [])
    if opportunities:
        console.print("[bold yellow]改善建議 (可節省時間):[/bold yellow]")
        for i, opp in enumerate(opportunities, 1):
            savings = format_time(opp.get('savings', 0))
            console.print(f"  {i}. {opp.get('title')} [dim](-{savings})[/dim]")
        console.print()

    # 診斷資訊
    diagnostics = result.get('diagnostics', [])
    if diagnostics and verbose:
        console.print("[bold cyan]診斷資訊:[/bold cyan]")
        for diag in diagnostics:
            display = diag.get('displayValue', '')
            console.print(f"  - {diag.get('title')}: {display}")
        console.print()

    # 總結
    perf_score = scores.get('performance', 0)
    if perf_score >= 90:
        console.print("[green]效能優秀! 繼續保持[/green]")
    elif perf_score >= 50:
        console.print("[yellow]效能尚可，建議參考上述改善建議[/yellow]")
    else:
        console.print("[red]效能需要改善，請優先處理上述建議[/red]")


def check_lighthouse_installed() -> bool:
    """檢查 Lighthouse 是否可用"""
    try:
        result = subprocess.run(
            ['npx', 'lighthouse', '--version'],
            capture_output=True,
            timeout=30,
            cwd=get_node_cwd()
        )
        return result.returncode == 0
    except:
        return False
