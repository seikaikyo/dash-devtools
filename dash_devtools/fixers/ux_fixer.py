"""
UI/UX 自動修復器

修復項目：
1. 圖示按鈕加入 title 屬性 (Shoelace sl-icon-button)
2. 空白按鈕警告

注意：此修復器適用於 Shoelace UI 框架專案
"""

import re
from pathlib import Path


class UxFixer:
    """UI/UX 自動修復器 (Shoelace)"""

    def __init__(self, project_path):
        self.project_path = Path(project_path)
        self.src_path = self.project_path / 'src'
        self.fixes = []

    def fix_all(self):
        """執行所有修復"""
        if not self.src_path.exists():
            return self.fixes

        # 只執行 Shoelace 兼容的修復
        self.fix_shoelace_icon_button_titles()

        return self.fixes

    def fix_shoelace_icon_button_titles(self):
        """為 Shoelace 圖示按鈕加入 label 屬性（用於無障礙存取）"""
        # Shoelace 圖示對應的中文標籤
        icon_labels = {
            'pencil': '編輯',
            'trash': '刪除',
            'eye': '檢視',
            'plus': '新增',
            'x': '關閉',
            'check': '確認',
            'arrow-clockwise': '重新整理',
            'download': '下載',
            'upload': '上傳',
            'search': '搜尋',
            'gear': '設定',
            'key': '密碼',
            'shield': '安全',
            'person': '使用者',
            'people': '群組',
            'three-dots': '更多',
            'three-dots-vertical': '更多',
            'box-arrow-right': '登出',
            'box-arrow-in-right': '登入',
            'save': '儲存',
            'copy': '複製',
            'link': '連結',
            'send': '送出',
        }

        for file_path in self.src_path.rglob('*.js'):
            try:
                content = file_path.read_text(encoding='utf-8')
                original = content
                rel_path = str(file_path.relative_to(self.project_path))

                # 找出缺少 label 的 sl-icon-button
                # <sl-icon-button name="pencil"></sl-icon-button>
                pattern = re.compile(
                    r'(<sl-icon-button[^>]*name="([^"]+)"[^>]*)'  # 捕獲 name 屬性
                    r'([^>]*>)',  # 其他屬性和結束
                    re.DOTALL
                )

                def add_label(match):
                    btn_start = match.group(1)
                    icon_name = match.group(2)
                    btn_end = match.group(3)

                    # 如果已有 label，不處理
                    if 'label=' in btn_start:
                        return match.group(0)

                    # 查找對應標籤
                    label = icon_labels.get(icon_name)
                    if not label:
                        # 嘗試從 icon 名稱推測
                        for key, val in icon_labels.items():
                            if key in icon_name:
                                label = val
                                break

                    if label:
                        return f'{btn_start} label="{label}"{btn_end}'

                    return match.group(0)

                content = pattern.sub(add_label, content)

                if content != original:
                    file_path.write_text(content, encoding='utf-8')
                    self.fixes.append(f'{rel_path}: sl-icon-button 加入 label 屬性')

            except Exception:
                pass
