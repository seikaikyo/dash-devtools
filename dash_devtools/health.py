"""
專案健康評分系統

類似 Lighthouse 的評分機制，量化專案品質：
- 安全性 (Security): 機敏資料、依賴漏洞
- 品質 (Quality): 程式碼規範、檔案結構
- 維護性 (Maintainability): 技術債務、文件完整度
- 效能 (Performance): Bundle 大小、載入時間
"""

import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, BarColumn, TextColumn
from rich.table import Table
from rich.text import Text

console = Console()


@dataclass
class HealthScore:
    """健康評分結果"""
    category: str
    score: int  # 0-100
    max_score: int = 100
    issues: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)

    @property
    def percentage(self) -> float:
        return (self.score / self.max_score) * 100

    @property
    def grade(self) -> str:
        """轉換為等級"""
        if self.score >= 90:
            return 'A'
        elif self.score >= 80:
            return 'B'
        elif self.score >= 70:
            return 'C'
        elif self.score >= 60:
            return 'D'
        else:
            return 'F'

    @property
    def color(self) -> str:
        """根據分數決定顏色"""
        if self.score >= 90:
            return 'green'
        elif self.score >= 70:
            return 'yellow'
        elif self.score >= 50:
            return 'orange1'
        else:
            return 'red'


class HealthChecker:
    """專案健康檢查器"""

    def __init__(self, project_path: str):
        self.project_path = Path(project_path)
        self.project_name = self.project_path.name

    def check_all(self) -> Dict[str, HealthScore]:
        """執行完整健康檢查"""
        return {
            'security': self._check_security(),
            'quality': self._check_quality(),
            'maintainability': self._check_maintainability(),
            'performance': self._check_performance(),
        }

    def _check_security(self) -> HealthScore:
        """安全性檢查"""
        score = 100
        issues = []
        recommendations = []

        # 檢查 .env 是否在 .gitignore
        gitignore = self.project_path / '.gitignore'
        if gitignore.exists():
            content = gitignore.read_text()
            if '.env' not in content:
                score -= 20
                issues.append('.env 未加入 .gitignore')
                recommendations.append('將 .env 加入 .gitignore')
        else:
            score -= 10
            issues.append('缺少 .gitignore 檔案')

        # 檢查是否有 .env 檔案被追蹤
        env_file = self.project_path / '.env'
        if env_file.exists():
            # 檢查是否在 git 中
            git_dir = self.project_path / '.git'
            if git_dir.exists():
                import subprocess
                result = subprocess.run(
                    ['git', 'ls-files', '.env'],
                    cwd=self.project_path,
                    capture_output=True,
                    text=True
                )
                if result.stdout.strip():
                    score -= 30
                    issues.append('.env 檔案被 git 追蹤')

        # 檢查硬編碼的機敏資料
        sensitive_patterns = [
            ('password', -15, '發現硬編碼密碼'),
            ('api_key', -15, '發現硬編碼 API Key'),
            ('secret', -10, '發現硬編碼 Secret'),
        ]

        for ext in ['*.js', '*.ts', '*.py']:
            for file_path in self.project_path.rglob(ext):
                if 'node_modules' in str(file_path) or '.git' in str(file_path):
                    continue
                try:
                    content = file_path.read_text().lower()
                    for pattern, penalty, message in sensitive_patterns:
                        if f'{pattern} = "' in content or f"{pattern} = '" in content:
                            score += penalty
                            if message not in issues:
                                issues.append(message)
                except Exception:
                    pass

        # 檢查依賴漏洞（簡化版）
        package_lock = self.project_path / 'package-lock.json'
        if package_lock.exists():
            recommendations.append('建議定期執行 npm audit')

        return HealthScore(
            category='安全性',
            score=max(0, score),
            issues=issues,
            recommendations=recommendations
        )

    def _check_quality(self) -> HealthScore:
        """程式碼品質檢查"""
        score = 100
        issues = []
        recommendations = []

        # 檢查 ESLint/Prettier 設定
        has_linter = any([
            (self.project_path / '.eslintrc.js').exists(),
            (self.project_path / '.eslintrc.json').exists(),
            (self.project_path / 'eslint.config.js').exists(),
        ])
        if not has_linter:
            score -= 10
            recommendations.append('建議加入 ESLint 設定')

        has_prettier = any([
            (self.project_path / '.prettierrc').exists(),
            (self.project_path / '.prettierrc.json').exists(),
        ])
        if not has_prettier:
            score -= 5
            recommendations.append('建議加入 Prettier 設定')

        # 檢查 TypeScript
        package_json = self.project_path / 'package.json'
        if package_json.exists():
            try:
                pkg = json.loads(package_json.read_text())
                deps = {**pkg.get('dependencies', {}), **pkg.get('devDependencies', {})}
                if 'typescript' not in deps:
                    score -= 5
                    recommendations.append('建議使用 TypeScript')
            except Exception:
                pass

        # 檢查檔案行數
        large_files = []
        for ext in ['*.js', '*.ts', '*.py']:
            for file_path in self.project_path.rglob(ext):
                if 'node_modules' in str(file_path) or '.git' in str(file_path):
                    continue
                try:
                    lines = len(file_path.read_text().splitlines())
                    if lines > 500:
                        large_files.append(f'{file_path.name} ({lines} 行)')
                except Exception:
                    pass

        if large_files:
            score -= min(len(large_files) * 5, 20)
            issues.append(f'{len(large_files)} 個檔案超過 500 行')

        return HealthScore(
            category='品質',
            score=max(0, score),
            issues=issues,
            recommendations=recommendations
        )

    def _check_maintainability(self) -> HealthScore:
        """維護性檢查"""
        score = 100
        issues = []
        recommendations = []

        # 檢查 README
        readme = self.project_path / 'README.md'
        if not readme.exists():
            score -= 15
            issues.append('缺少 README.md')
        else:
            content = readme.read_text()
            if len(content) < 200:
                score -= 5
                recommendations.append('README 內容過短，建議補充')

        # 檢查 CLAUDE.md
        claude_md = self.project_path / 'CLAUDE.md'
        if not claude_md.exists():
            score -= 10
            recommendations.append('建議加入 CLAUDE.md (dash docs claude)')

        # 檢查 package.json 完整度
        package_json = self.project_path / 'package.json'
        if package_json.exists():
            try:
                pkg = json.loads(package_json.read_text())
                if not pkg.get('description'):
                    score -= 5
                    recommendations.append('package.json 缺少 description')
                if not pkg.get('scripts'):
                    score -= 5
                    issues.append('package.json 缺少 scripts')
            except Exception:
                pass

        # 檢查測試設定
        has_tests = any([
            (self.project_path / 'tests').exists(),
            (self.project_path / '__tests__').exists(),
            (self.project_path / 'spec').exists(),
            any(self.project_path.rglob('*.test.ts')),
            any(self.project_path.rglob('*.spec.ts')),
        ])
        if not has_tests:
            score -= 15
            recommendations.append('建議加入測試')

        # 檢查 Git hooks
        husky = self.project_path / '.husky'
        if not husky.exists():
            score -= 5
            recommendations.append('建議使用 Git hooks (dash hooks install)')

        return HealthScore(
            category='維護性',
            score=max(0, score),
            issues=issues,
            recommendations=recommendations
        )

    def _check_performance(self) -> HealthScore:
        """效能檢查"""
        score = 100
        issues = []
        recommendations = []

        # 檢查 node_modules 大小（簡化版）
        node_modules = self.project_path / 'node_modules'
        if node_modules.exists():
            # 計算依賴數量
            package_json = self.project_path / 'package.json'
            if package_json.exists():
                try:
                    pkg = json.loads(package_json.read_text())
                    deps_count = len(pkg.get('dependencies', {}))
                    if deps_count > 50:
                        score -= 10
                        issues.append(f'依賴數量過多 ({deps_count} 個)')
                        recommendations.append('審視並移除不必要的依賴')
                except Exception:
                    pass

        # 檢查是否有未使用的依賴（簡化版）
        package_json = self.project_path / 'package.json'
        if package_json.exists():
            recommendations.append('建議定期執行 depcheck 檢查未使用依賴')

        # 檢查圖片優化
        large_images = []
        for ext in ['*.png', '*.jpg', '*.jpeg']:
            for file_path in self.project_path.rglob(ext):
                if 'node_modules' in str(file_path):
                    continue
                try:
                    size_kb = file_path.stat().st_size / 1024
                    if size_kb > 500:
                        large_images.append(f'{file_path.name} ({size_kb:.0f}KB)')
                except Exception:
                    pass

        if large_images:
            score -= min(len(large_images) * 5, 15)
            issues.append(f'{len(large_images)} 個圖片超過 500KB')
            recommendations.append('建議壓縮大型圖片')

        return HealthScore(
            category='效能',
            score=max(0, score),
            issues=issues,
            recommendations=recommendations
        )


def render_health_report(project_name: str, scores: Dict[str, HealthScore]):
    """渲染健康報告"""

    # 計算總分
    total_score = sum(s.score for s in scores.values()) // len(scores)

    # 標題
    grade_colors = {'A': 'green', 'B': 'cyan', 'C': 'yellow', 'D': 'orange1', 'F': 'red'}
    grade = 'A' if total_score >= 90 else 'B' if total_score >= 80 else 'C' if total_score >= 70 else 'D' if total_score >= 60 else 'F'

    title = Text()
    title.append(f"\n  {project_name} ", style="bold white")
    title.append("健康報告\n", style="dim")

    console.print(Panel(title, border_style="cyan"))

    # 總分顯示
    score_display = Text()
    score_display.append("  總分: ", style="dim")
    score_display.append(f"{total_score}", style=f"bold {grade_colors[grade]}")
    score_display.append(f"/100 ", style="dim")
    score_display.append(f"[{grade}]", style=f"bold {grade_colors[grade]}")
    console.print(score_display)
    console.print()

    # 各項評分進度條
    for key, score in scores.items():
        bar_width = 30
        filled = int((score.score / 100) * bar_width)

        bar = Text()
        bar.append(f"  {score.category:　<6} ", style="white")
        bar.append("█" * filled, style=score.color)
        bar.append("░" * (bar_width - filled), style="dim")
        bar.append(f" {score.score:3d}%", style=score.color)

        console.print(bar)

    console.print()

    # 問題和建議
    all_issues = []
    all_recommendations = []

    for score in scores.values():
        all_issues.extend(score.issues)
        all_recommendations.extend(score.recommendations)

    if all_issues:
        console.print("  [red]問題[/red]")
        for issue in all_issues[:5]:
            console.print(f"    [red]•[/red] {issue}")
        console.print()

    if all_recommendations:
        console.print("  [yellow]建議[/yellow]")
        for rec in all_recommendations[:5]:
            console.print(f"    [yellow]•[/yellow] {rec}")

    console.print()

    return {
        'project': project_name,
        'total_score': total_score,
        'grade': grade,
        'scores': {k: {'score': v.score, 'issues': v.issues} for k, v in scores.items()}
    }


def run_health_check(project_path: str) -> dict:
    """執行健康檢查並輸出報告"""
    checker = HealthChecker(project_path)
    scores = checker.check_all()
    return render_health_report(checker.project_name, scores)
