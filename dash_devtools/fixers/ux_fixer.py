"""
UI/UX 自動修復器

注意：Shoelace 專用修復已移除（框架已棄用）
目前為空殼，保留介面供 run_auto_fix 呼叫
"""

from pathlib import Path


class UxFixer:
    """UI/UX 自動修復器（預留介面）"""

    def __init__(self, project_path):
        self.project_path = Path(project_path)
        self.src_path = self.project_path / 'src'
        self.fixes = []

    def fix_all(self):
        """執行所有修復（目前無待修復項）"""
        return self.fixes
