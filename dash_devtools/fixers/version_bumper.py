"""
版本號自動更新器

自動偵測並更新專案版本號
支援格式：
- index.html: <div class="version-info">vX.Y.Z</div>
- package.json: "version": "X.Y.Z"
"""

import re
import json
from pathlib import Path


class VersionBumper:
    """版本號自動更新器"""

    def __init__(self, project_path):
        self.project_path = Path(project_path)
        self.fixes = []

    def bump_patch(self):
        """更新 patch 版本號 (X.Y.Z -> X.Y.Z+1)"""
        bumped = False

        # 嘗試更新 index.html
        index_html = self.project_path / 'index.html'
        if index_html.exists():
            if self._bump_html_version(index_html):
                bumped = True

        # 嘗試更新 package.json
        package_json = self.project_path / 'package.json'
        if package_json.exists():
            if self._bump_package_version(package_json):
                bumped = True

        return self.fixes

    def _bump_html_version(self, file_path):
        """更新 HTML 中的版本號"""
        try:
            content = file_path.read_text(encoding='utf-8')

            # 匹配 version-info 中的版本號
            pattern = r'(<div[^>]*class="[^"]*version-info[^"]*"[^>]*>)v?(\d+)\.(\d+)\.(\d+)(</div>)'
            match = re.search(pattern, content)

            if match:
                prefix = match.group(1)
                major = int(match.group(2))
                minor = int(match.group(3))
                patch = int(match.group(4))
                suffix = match.group(5)

                new_patch = patch + 1
                old_version = f'{major}.{minor}.{patch}'
                new_version = f'{major}.{minor}.{new_patch}'

                new_content = content.replace(
                    match.group(0),
                    f'{prefix}v{new_version}{suffix}'
                )

                file_path.write_text(new_content, encoding='utf-8')
                self.fixes.append(f'index.html: 版本 v{old_version} -> v{new_version}')
                return True

        except Exception:
            pass

        return False

    def _bump_package_version(self, file_path):
        """更新 package.json 中的版本號"""
        try:
            content = file_path.read_text(encoding='utf-8')
            data = json.loads(content)

            if 'version' in data:
                old_version = data['version']
                parts = old_version.split('.')

                if len(parts) >= 3:
                    parts[2] = str(int(parts[2]) + 1)
                    new_version = '.'.join(parts)
                    data['version'] = new_version

                    # 保持格式
                    new_content = json.dumps(data, indent=2, ensure_ascii=False) + '\n'
                    file_path.write_text(new_content, encoding='utf-8')
                    self.fixes.append(f'package.json: 版本 {old_version} -> {new_version}')
                    return True

        except Exception:
            pass

        return False


def bump_version_if_fixed(project_path, fixes):
    """如果有修復，自動更新版本號

    Args:
        project_path: 專案路徑
        fixes: 修復清單

    Returns:
        list: 版本更新訊息
    """
    if not fixes:
        return []

    bumper = VersionBumper(project_path)
    return bumper.bump_patch()
