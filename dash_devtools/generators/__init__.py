"""
文件產生工具
"""

from pathlib import Path
import json

__all__ = ['generate_claude_md', 'get_release_status', 'publish_release']


def generate_claude_md(project_path):
    """產生 CLAUDE.md"""
    project = Path(project_path)
    claude_dir = project / '.claude'
    claude_md = claude_dir / 'CLAUDE.md'

    if not project.exists():
        return {'success': False, 'error': '專案不存在'}

    # 基本模板
    template = f"""# {project.name}

## 專案概述

[待補充]

## 技術堆疊

| 類別 | 技術 |
|------|------|
| 前端 | [待補充] |
| 後端 | [待補充] |
| 資料庫 | [待補充] |

## 開發規範

遵循 DashAI 開發規範，詳見全域 CLAUDE.md
"""

    try:
        claude_dir.mkdir(exist_ok=True)
        claude_md.write_text(template, encoding='utf-8')
        return {'success': True}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def get_release_status():
    """取得版本狀態"""
    projects_dir = Path('/Users/dash/Documents/github')
    status = {}

    for project in projects_dir.iterdir():
        if not project.is_dir():
            continue
        pkg_path = project / 'package.json'
        if pkg_path.exists():
            try:
                pkg = json.loads(pkg_path.read_text())
                status[project.name] = {
                    'version': pkg.get('version', 'N/A'),
                    'last_update': 'N/A'
                }
            except Exception:
                pass

    return status


def publish_release(project_path, version):
    """發布版本"""
    project = Path(project_path)
    pkg_path = project / 'package.json'

    if not pkg_path.exists():
        return {'success': False, 'error': 'package.json 不存在'}

    try:
        pkg = json.loads(pkg_path.read_text())
        pkg['version'] = version
        pkg_path.write_text(json.dumps(pkg, indent=2, ensure_ascii=False))
        return {'success': True}
    except Exception as e:
        return {'success': False, 'error': str(e)}
