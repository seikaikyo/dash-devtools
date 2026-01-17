"""
OpenSpec CLI 包裝模組

Spec-Driven Development (SDD) 工作流程整合。
使用 @fission-ai/openspec npm 套件。

安裝：npm install -g @fission-ai/openspec@latest
"""

import subprocess
import json
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field


@dataclass
class SpecResult:
    """OpenSpec 操作結果"""
    success: bool
    message: str = ""
    data: dict = field(default_factory=dict)
    error: str = ""


class OpenSpecWrapper:
    """OpenSpec CLI 包裝器"""

    @staticmethod
    def _check_installed() -> bool:
        """檢查 openspec 是否安裝"""
        try:
            result = subprocess.run(
                ['which', 'openspec'],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except Exception:
            return False

    @staticmethod
    def _run_command(args: list, cwd: Optional[str] = None) -> SpecResult:
        """執行 openspec 指令"""
        if not OpenSpecWrapper._check_installed():
            return SpecResult(
                success=False,
                error="openspec 未安裝。請執行: npm install -g @fission-ai/openspec@latest"
            )

        try:
            cmd = ['openspec'] + args
            result = subprocess.run(
                cmd,
                cwd=cwd,
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                return SpecResult(
                    success=True,
                    message=result.stdout.strip(),
                    data={}
                )
            else:
                return SpecResult(
                    success=False,
                    error=result.stderr.strip() or result.stdout.strip()
                )
        except Exception as e:
            return SpecResult(
                success=False,
                error=str(e)
            )

    @staticmethod
    def init(project_path: str) -> SpecResult:
        """初始化 OpenSpec

        Args:
            project_path: 專案路徑

        Returns:
            SpecResult: 操作結果
        """
        result = OpenSpecWrapper._run_command(['init'], cwd=project_path)
        if result.success:
            result.message = "OpenSpec 初始化完成"
            result.data = {
                'openspec_dir': str(Path(project_path) / 'openspec'),
                'specs_dir': str(Path(project_path) / 'openspec' / 'specs'),
                'changes_dir': str(Path(project_path) / 'openspec' / 'changes')
            }
        return result

    @staticmethod
    def list_changes(project_path: str) -> SpecResult:
        """列出活動變更

        Args:
            project_path: 專案路徑

        Returns:
            SpecResult: 包含變更清單
        """
        result = OpenSpecWrapper._run_command(['list'], cwd=project_path)
        if result.success:
            # 解析輸出為結構化資料
            changes = []
            for line in result.message.split('\n'):
                line = line.strip()
                if line and not line.startswith('─') and not line.startswith('Active'):
                    changes.append(line)
            result.data = {'changes': changes, 'count': len(changes)}
        return result

    @staticmethod
    def view(project_path: str) -> None:
        """開啟互動式儀表板 (需要 TTY)

        Args:
            project_path: 專案路徑
        """
        subprocess.run(['openspec', 'view'], cwd=project_path)

    @staticmethod
    def show(project_path: str, change_name: str) -> SpecResult:
        """顯示變更詳情

        Args:
            project_path: 專案路徑
            change_name: 變更名稱

        Returns:
            SpecResult: 包含變更詳情
        """
        result = OpenSpecWrapper._run_command(['show', change_name], cwd=project_path)
        if result.success:
            result.data = {'change_name': change_name, 'content': result.message}
        return result

    @staticmethod
    def validate(project_path: str, change_name: str) -> SpecResult:
        """驗證規格格式

        Args:
            project_path: 專案路徑
            change_name: 變更名稱

        Returns:
            SpecResult: 驗證結果
        """
        result = OpenSpecWrapper._run_command(['validate', change_name], cwd=project_path)
        if result.success:
            result.data = {'change_name': change_name, 'valid': True}
        else:
            result.data = {'change_name': change_name, 'valid': False}
        return result

    @staticmethod
    def archive(project_path: str, change_name: str, yes: bool = False) -> SpecResult:
        """歸檔完成的變更

        Args:
            project_path: 專案路徑
            change_name: 變更名稱
            yes: 自動確認

        Returns:
            SpecResult: 歸檔結果
        """
        args = ['archive', change_name]
        if yes:
            args.append('-y')
        result = OpenSpecWrapper._run_command(args, cwd=project_path)
        if result.success:
            result.message = f"變更 '{change_name}' 已歸檔"
            result.data = {'change_name': change_name, 'archived': True}
        return result


def get_spec_status(project_path: str) -> dict:
    """取得專案的 OpenSpec 狀態摘要

    Args:
        project_path: 專案路徑

    Returns:
        dict: 狀態摘要
    """
    path = Path(project_path)
    openspec_dir = path / 'openspec'

    status = {
        'initialized': openspec_dir.exists(),
        'specs_count': 0,
        'changes_count': 0,
        'archive_count': 0,
        'stale_changes': [],  # 超過 7 天未處理的提案
    }

    if not openspec_dir.exists():
        return status

    # 統計 specs
    specs_dir = openspec_dir / 'specs'
    if specs_dir.exists():
        status['specs_count'] = len(list(specs_dir.glob('*.md')))

    # 統計 changes
    changes_dir = openspec_dir / 'changes'
    if changes_dir.exists():
        import time
        now = time.time()
        seven_days = 7 * 24 * 60 * 60

        for change_file in changes_dir.glob('*.md'):
            status['changes_count'] += 1
            # 檢查是否過期
            mtime = change_file.stat().st_mtime
            if now - mtime > seven_days:
                status['stale_changes'].append(change_file.stem)

    # 統計 archive
    archive_dir = openspec_dir / 'archive'
    if archive_dir.exists():
        status['archive_count'] = len(list(archive_dir.glob('*.md')))

    return status
