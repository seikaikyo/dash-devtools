#!/usr/bin/env python3
"""
DashAI DevTools CLI - 統一入口

使用方式：
  dash validate /path/to/project
  dash migrate /path/to/project
  dash docs claude /path/to/project
  dash release status
"""

import click
from pathlib import Path
from rich.console import Console

console = Console()

# 基礎路徑 (動態取得使用者 home 目錄)
GITHUB_BASE = Path.home() / 'Documents' / 'github'

# 預設專案清單 (使用動態基礎路徑)
DEFAULT_PROJECT_NAMES = [
    'DashAstro',
    'DashTrade',
    'sinoauto',
    'jlpt-n1-learner',
    'sukuyodo',
    'jinkochino',
    'job-crawler',
    'dashai-portfolio',
    'ai-english-tutor',
    'ai-red-team',
    'toeic-practice',
    'dash-devtools',
    'dash-doc-generator',
    'dash-skills',
    'git-security-hooks',
]

DEFAULT_PROJECTS = [str(GITHUB_BASE / name) for name in DEFAULT_PROJECT_NAMES]


@click.group()
@click.version_option(version="2.0.1")
def main():
    """DashAI DevTools v2 - 大許開發工具集

    新功能：
      health  專案健康評分
      stats   程式碼統計
      watch   即時監控
    """
    pass


# 註冊所有子指令
from .commands import register_all
register_all(main)


if __name__ == '__main__':
    main()
