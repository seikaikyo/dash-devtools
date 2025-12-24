"""
資料庫遷移管理模組

支援 Alembic + SQLModel 的自動遷移管理
"""

import os
import re
import subprocess
from pathlib import Path
from typing import Optional


def _run_alembic(project: str, args: list[str], capture: bool = True) -> dict:
    """執行 Alembic 指令

    Args:
        project: 專案路徑
        args: Alembic 參數
        capture: 是否擷取輸出

    Returns:
        dict 包含 success, stdout, stderr
    """
    project_path = Path(project).resolve()

    # 檢查是否有 alembic.ini
    alembic_ini = project_path / 'alembic.ini'
    if not alembic_ini.exists():
        return {
            'success': False,
            'error': '找不到 alembic.ini，請先執行 dash db init'
        }

    try:
        result = subprocess.run(
            ['alembic'] + args,
            cwd=str(project_path),
            capture_output=capture,
            text=True,
            timeout=60
        )

        return {
            'success': result.returncode == 0,
            'stdout': result.stdout if capture else '',
            'stderr': result.stderr if capture else '',
            'returncode': result.returncode
        }
    except FileNotFoundError:
        return {
            'success': False,
            'error': '找不到 alembic 指令，請安裝: pip install alembic'
        }
    except subprocess.TimeoutExpired:
        return {
            'success': False,
            'error': '指令執行逾時'
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


def init_alembic(project: str) -> dict:
    """初始化 Alembic 環境

    Args:
        project: 專案路徑

    Returns:
        dict 包含 success, alembic_dir 或 error
    """
    project_path = Path(project).resolve()
    alembic_dir = project_path / 'alembic'
    alembic_ini = project_path / 'alembic.ini'

    # 檢查是否已初始化
    if alembic_ini.exists():
        return {
            'success': False,
            'error': 'Alembic 已初始化 (alembic.ini 已存在)'
        }

    # 執行 alembic init
    try:
        result = subprocess.run(
            ['alembic', 'init', 'alembic'],
            cwd=str(project_path),
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode != 0:
            return {
                'success': False,
                'error': result.stderr or '初始化失敗'
            }

        return {
            'success': True,
            'alembic_dir': str(alembic_dir)
        }
    except FileNotFoundError:
        return {
            'success': False,
            'error': '找不到 alembic 指令，請安裝: pip install alembic'
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


def get_migration_status(project: str) -> dict:
    """取得遷移狀態

    Args:
        project: 專案路徑

    Returns:
        dict 包含 success, current, head, pending 或 error
    """
    project_path = Path(project).resolve()

    # 取得目前版本
    current_result = _run_alembic(project, ['current'])
    if not current_result['success']:
        # 如果沒有 DATABASE_URL，嘗試讀取本地狀態
        if 'DATABASE_URL' in current_result.get('stderr', ''):
            return {
                'success': False,
                'error': 'DATABASE_URL 環境變數未設定'
            }
        return current_result

    current = current_result['stdout'].strip()
    if not current:
        current = '(尚未套用任何遷移)'

    # 取得最新版本
    head_result = _run_alembic(project, ['heads'])
    head = head_result['stdout'].strip() if head_result['success'] else 'N/A'

    # 取得待套用的遷移
    history_result = _run_alembic(project, ['history', '--indicate-current'])
    pending = []
    if history_result['success']:
        lines = history_result['stdout'].strip().split('\n')
        in_pending = True
        for line in lines:
            if '(current)' in line or '(head)' in line:
                in_pending = False
            elif in_pending and line.strip() and '->' in line:
                pending.append(line.strip())

    return {
        'success': True,
        'current': current,
        'head': head,
        'pending': pending
    }


def generate_migration(project: str, message: str, autogenerate: bool = True) -> dict:
    """產生新的遷移檔

    Args:
        project: 專案路徑
        message: 遷移訊息
        autogenerate: 是否自動偵測變更

    Returns:
        dict 包含 success, migration_file, warnings 或 error
    """
    args = ['revision', '-m', message]
    if autogenerate:
        args.append('--autogenerate')

    result = _run_alembic(project, args)

    if not result['success']:
        return {
            'success': False,
            'error': result.get('stderr') or result.get('error', '產生失敗')
        }

    # 解析輸出取得檔案路徑
    output = result['stdout']
    migration_file = None

    # 尋找產生的檔案路徑
    match = re.search(r'Generating (.+\.py)', output)
    if match:
        migration_file = match.group(1)

    # 檢查危險操作
    warnings = []
    if migration_file and Path(migration_file).exists():
        content = Path(migration_file).read_text()
        dangerous_patterns = [
            (r'\bop\.drop_table\b', 'DROP TABLE 操作'),
            (r'\bop\.drop_column\b', 'DROP COLUMN 操作'),
            (r'\bop\.drop_index\b', 'DROP INDEX 操作'),
        ]
        for pattern, desc in dangerous_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                warnings.append(desc)

    return {
        'success': True,
        'migration_file': migration_file,
        'warnings': warnings
    }


def run_upgrade(project: str, revision: str = 'head', dry_run: bool = False) -> dict:
    """升級資料庫

    Args:
        project: 專案路徑
        revision: 目標版本
        dry_run: 預覽模式

    Returns:
        dict 包含 success, current, sql 或 error
    """
    if dry_run:
        # SQL 預覽模式
        result = _run_alembic(project, ['upgrade', revision, '--sql'])
        if result['success']:
            return {
                'success': True,
                'sql': result['stdout']
            }
        return {
            'success': False,
            'error': result.get('stderr') or result.get('error', '預覽失敗')
        }

    # 實際執行升級
    result = _run_alembic(project, ['upgrade', revision])

    if not result['success']:
        return {
            'success': False,
            'error': result.get('stderr') or result.get('error', '升級失敗')
        }

    # 取得目前版本
    status = get_migration_status(project)

    return {
        'success': True,
        'current': status.get('current', 'N/A')
    }


def run_downgrade(project: str, revision: str) -> dict:
    """降級資料庫

    Args:
        project: 專案路徑
        revision: 目標版本 (可用 -1 表示降一個版本)

    Returns:
        dict 包含 success, current 或 error
    """
    result = _run_alembic(project, ['downgrade', revision])

    if not result['success']:
        return {
            'success': False,
            'error': result.get('stderr') or result.get('error', '降級失敗')
        }

    # 取得目前版本
    status = get_migration_status(project)

    return {
        'success': True,
        'current': status.get('current', 'N/A')
    }


def check_migration_sync(project: str) -> dict:
    """檢查 Model 與遷移是否同步

    用於驗證器，檢查是否有未產生遷移的 Model 變更

    Args:
        project: 專案路徑

    Returns:
        dict 包含 success, synced, details
    """
    project_path = Path(project).resolve()

    # 檢查是否有 alembic
    if not (project_path / 'alembic.ini').exists():
        return {
            'success': True,
            'synced': None,
            'details': 'Alembic 未初始化'
        }

    # 嘗試產生遷移預覽
    result = _run_alembic(project, [
        'check'  # Alembic 1.9+ 的新功能
    ])

    # alembic check 不存在時，改用其他方式
    if 'No such command' in result.get('stderr', ''):
        # 舊版 Alembic，使用 revision --autogenerate 加 --dry-run
        # 這會比較複雜，先簡單回傳
        return {
            'success': True,
            'synced': None,
            'details': 'Alembic 版本過舊，無法自動檢查'
        }

    if result['success']:
        return {
            'success': True,
            'synced': True,
            'details': 'Model 與遷移已同步'
        }
    else:
        # 有差異
        return {
            'success': True,
            'synced': False,
            'details': result.get('stderr', 'Model 與遷移不同步')
        }
