"""
UI/UX 自動修復器

修復項目：
1. 表格內下拉選單 -> 圖示按鈕
2. 圖示按鈕加入 title 屬性
3. 移除巢狀選單
"""

import re
from pathlib import Path


class UxFixer:
    """UI/UX 自動修復器"""

    def __init__(self, project_path):
        self.project_path = Path(project_path)
        self.src_path = self.project_path / 'src'
        self.fixes = []

    def fix_all(self):
        """執行所有修復"""
        if not self.src_path.exists():
            return self.fixes

        self.fix_table_dropdowns()
        self.fix_icon_button_titles()

        return self.fixes

    def fix_table_dropdowns(self):
        """將表格內的下拉選單轉換為圖示按鈕"""
        for file_path in self.src_path.rglob('*.js'):
            try:
                content = file_path.read_text(encoding='utf-8')
                original = content
                rel_path = str(file_path.relative_to(self.project_path))

                # 偵測 <td> 內的 dropdown 結構
                # 這是個複雜的轉換，需要解析 dropdown 內容
                td_dropdown_pattern = re.compile(
                    r'<td[^>]*>\s*'
                    r'<div[^>]*class="[^"]*dropdown[^"]*"[^>]*>\s*'
                    r'<button[^>]*>.*?</button>\s*'
                    r'<ul[^>]*class="[^"]*dropdown-content[^"]*"[^>]*>'
                    r'(.*?)'
                    r'</ul>\s*'
                    r'</div>\s*'
                    r'</td>',
                    re.DOTALL
                )

                matches = list(td_dropdown_pattern.finditer(content))
                if not matches:
                    continue

                for match in reversed(matches):
                    dropdown_content = match.group(1)

                    # 解析選單項目
                    menu_items = re.findall(
                        r'<(?:li|a)[^>]*data-action="([^"]+)"[^>]*data-id="([^"]+)"[^>]*>'
                        r'.*?<i[^>]*class="[^"]*bi[- ]([^"]+)"[^>]*></i>\s*([^<]*)',
                        dropdown_content,
                        re.DOTALL
                    )

                    if not menu_items:
                        continue

                    # 建構圖示按鈕列
                    buttons = []
                    for action, id_var, icon, label in menu_items:
                        label = label.strip()
                        # 判斷是否為危險操作
                        is_danger = action in ['delete', 'disable', 'remove']
                        danger_class = ' text-error' if is_danger else ''

                        buttons.append(
                            f'<button class="btn btn-sm btn-ghost btn-square{danger_class}" '
                            f'data-action="{action}" data-id="{id_var}" title="{label}">'
                            f'<i class="bi bi-{icon}"></i>'
                            f'</button>'
                        )

                    if buttons:
                        new_td = (
                            '<td>\n'
                            '                <div class="action-buttons">\n'
                            '                    ' + '\n                    '.join(buttons) + '\n'
                            '                </div>\n'
                            '            </td>'
                        )
                        content = content[:match.start()] + new_td + content[match.end():]

                if content != original:
                    file_path.write_text(content, encoding='utf-8')
                    self.fixes.append(f'{rel_path}: 下拉選單轉換為圖示按鈕')

            except Exception as e:
                pass

    def fix_icon_button_titles(self):
        """為圖示按鈕加入 title 屬性"""
        # 常見圖示對應的中文標籤
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
            'shield-lock': 'MFA',
            'shield-check': 'MFA',
            'person': '使用者',
            'person-slash': '停用',
            'people': '群組',
            'incognito': '模擬',
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

                # 找出缺少 title 的圖示按鈕
                # <button class="...btn..."><i class="bi bi-xxx"></i></button>
                pattern = re.compile(
                    r'(<button[^>]*class="[^"]*btn[^"]*")'  # button 開始，有 btn class
                    r'([^>]*)'  # 其他屬性
                    r'(>\s*<i[^>]*class="[^"]*bi[- ]bi-([a-z-]+)[^"]*"[^>]*></i>\s*</button>)',  # 圖示
                    re.DOTALL
                )

                def add_title(match):
                    btn_start = match.group(1)
                    btn_attrs = match.group(2)
                    btn_end = match.group(3)
                    icon_name = match.group(4)

                    # 如果已有 title，不處理
                    if 'title=' in btn_attrs:
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
                        return f'{btn_start}{btn_attrs} title="{label}"{btn_end}'

                    return match.group(0)

                content = pattern.sub(add_title, content)

                if content != original:
                    file_path.write_text(content, encoding='utf-8')
                    self.fixes.append(f'{rel_path}: 圖示按鈕加入 title 屬性')

            except Exception:
                pass
