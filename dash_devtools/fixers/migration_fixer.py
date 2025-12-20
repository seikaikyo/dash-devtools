"""
UI 遷移自動修復器

修復項目：
1. 不完整的 HTML 標籤 (缺少結束標籤)
2. 空白事件處理器
"""

import re
from pathlib import Path


class MigrationFixer:
    """UI 遷移自動修復器"""

    def __init__(self, project_path):
        self.project_path = Path(project_path)
        self.src_path = self.project_path / 'src'
        self.fixes = []

    def fix_all(self):
        """執行所有修復"""
        if not self.src_path.exists():
            return self.fixes

        self.fix_incomplete_html_tags()
        self.fix_empty_event_handlers()

        return self.fixes

    def fix_incomplete_html_tags(self):
        """修復不完整的 HTML 標籤"""
        tags_to_fix = ['select', 'textarea', 'table', 'ul', 'ol']

        for file_path in self.src_path.rglob('*.js'):
            try:
                content = file_path.read_text(encoding='utf-8')
                original_content = content
                rel_path = str(file_path.relative_to(self.project_path))

                for tag in tags_to_fix:
                    # 計算開始和結束標籤數量
                    open_pattern = rf'<{tag}[^>]*>'
                    close_pattern = rf'</{tag}>'

                    open_matches = list(re.finditer(open_pattern, content))
                    close_count = len(re.findall(close_pattern, content))

                    if len(open_matches) > close_count:
                        # 需要補上結束標籤
                        missing = len(open_matches) - close_count

                        # 找到每個開始標籤，嘗試補上結束標籤
                        for match in reversed(open_matches[-missing:]):
                            # 找到這個標籤後的位置，在適當位置插入結束標籤
                            start_pos = match.end()

                            # 對於 select，找到下一個換行或 > 後插入
                            if tag == 'select':
                                # 找到選項結束的位置（通常是 </option> 之後的換行）
                                remaining = content[start_pos:]
                                # 找最後一個 </option> 或 option value
                                option_end = remaining.rfind('</option>')
                                if option_end == -1:
                                    # 沒有 option，找下一個 >
                                    next_line = remaining.find('\n')
                                    if next_line != -1:
                                        insert_pos = start_pos + next_line
                                        content = content[:insert_pos] + f'</{tag}>' + content[insert_pos:]
                                else:
                                    insert_pos = start_pos + option_end + len('</option>')
                                    content = content[:insert_pos] + f'\n            </{tag}>' + content[insert_pos:]

                            elif tag == 'textarea':
                                # textarea 通常是自閉合的，在 > 後面加上 </textarea>
                                if content[match.end()-2:match.end()] != '/>':
                                    content = content[:match.end()] + f'</{tag}>' + content[match.end():]

                if content != original_content:
                    file_path.write_text(content, encoding='utf-8')
                    self.fixes.append(f'{rel_path}: 修復 HTML 標籤')

            except Exception as e:
                pass

    def fix_empty_event_handlers(self):
        """修復空白事件處理器"""
        # 找出 addEventListener('', ...) 並移除或註解
        pattern = r"(\w+)\?*\.addEventListener\s*\(\s*['\"]['\"]"

        for file_path in self.src_path.rglob('*.js'):
            try:
                content = file_path.read_text(encoding='utf-8')
                original_content = content
                rel_path = str(file_path.relative_to(self.project_path))

                # 找到並移除空事件處理器
                matches = list(re.finditer(pattern, content))
                if matches:
                    for match in reversed(matches):
                        # 找到整個 addEventListener 語句
                        start = match.start()
                        # 找到語句結束（;）
                        end = content.find(';', start)
                        if end != -1:
                            statement = content[start:end+1]
                            # 註解掉這行
                            content = content[:start] + '// [AUTO-REMOVED] ' + statement + content[end+1:]

                if content != original_content:
                    file_path.write_text(content, encoding='utf-8')
                    self.fixes.append(f'{rel_path}: 移除空白事件處理器')

            except Exception:
                pass
