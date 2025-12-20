"""
Shoelace → Tailwind CSS 4 + DaisyUI 5 遷移器
"""

import re
import json
import subprocess
from pathlib import Path


# 元件轉換規則
COMPONENT_MAPPINGS = [
    # Buttons
    (r'<sl-button\s+variant="primary"([^>]*)>', r'<button class="btn btn-primary"\1>'),
    (r'<sl-button\s+variant="success"([^>]*)>', r'<button class="btn btn-success"\1>'),
    (r'<sl-button\s+variant="warning"([^>]*)>', r'<button class="btn btn-warning"\1>'),
    (r'<sl-button\s+variant="danger"([^>]*)>', r'<button class="btn btn-error"\1>'),
    (r'<sl-button\s+variant="neutral"([^>]*)>', r'<button class="btn btn-ghost"\1>'),
    (r'<sl-button\s+variant="default"([^>]*)>', r'<button class="btn"\1>'),
    (r'<sl-button([^>]*)>', r'<button class="btn"\1>'),
    (r'</sl-button>', r'</button>'),

    # Input
    (r'<sl-input([^>]*)>', r'<input class="input input-bordered"\1>'),
    (r'</sl-input>', r''),

    # Select
    (r'<sl-select([^>]*)>', r'<select class="select select-bordered"\1>'),
    (r'</sl-select>', r'</select>'),
    (r'<sl-option([^>]*)>', r'<option\1>'),
    (r'</sl-option>', r'</option>'),

    # Dialog / Modal
    (r'<sl-dialog([^>]*)>', r'<dialog class="modal"\1><div class="modal-box">'),
    (r'</sl-dialog>', r'</div><form method="dialog" class="modal-backdrop"><button>close</button></form></dialog>'),

    # Drawer
    (r'<sl-drawer([^>]*)>', r'<dialog class="modal modal-bottom sm:modal-middle"\1><div class="modal-box">'),
    (r'</sl-drawer>', r'</div><form method="dialog" class="modal-backdrop"><button>close</button></form></dialog>'),

    # Card
    (r'<sl-card([^>]*)>', r'<div class="card bg-base-100 shadow"\1><div class="card-body">'),
    (r'</sl-card>', r'</div></div>'),

    # Badge
    (r'<sl-badge\s+variant="primary"([^>]*)>', r'<span class="badge badge-primary"\1>'),
    (r'<sl-badge\s+variant="success"([^>]*)>', r'<span class="badge badge-success"\1>'),
    (r'<sl-badge\s+variant="warning"([^>]*)>', r'<span class="badge badge-warning"\1>'),
    (r'<sl-badge\s+variant="danger"([^>]*)>', r'<span class="badge badge-error"\1>'),
    (r'<sl-badge([^>]*)>', r'<span class="badge"\1>'),
    (r'</sl-badge>', r'</span>'),

    # Spinner
    (r'<sl-spinner([^>]*)>', r'<span class="loading loading-spinner"\1>'),
    (r'</sl-spinner>', r'</span>'),
]

# Icon 轉換
ICON_MAPPINGS = {
    'plus': '➕', 'plus-lg': '➕', 'pencil': '✏️', 'trash': '🗑️',
    'eye': '👁️', 'search': '🔍', 'x': '✕', 'check': '✓',
    'arrow-clockwise': '🔄', 'gear': '⚙️', 'house': '🏠',
    'person': '👤', 'calendar': '📅', 'download': '📥',
    'upload': '📤', 'file-earmark': '📄', 'printer': '🖨️',
    'broadcast': '📡', 'shield-lock': '🔐', 'recycle': '♻️',
}


class ShoelaceToDaisyUIMigrator:
    """Shoelace → DaisyUI 遷移器"""

    def __init__(self, project_path, dry_run=False):
        self.project_path = Path(project_path)
        self.src_path = self.project_path / 'src'
        self.dry_run = dry_run
        self.stats = {
            'files': 0,
            'components': 0,
            'icons': 0,
        }

    def run(self):
        """執行遷移"""
        try:
            if not self.dry_run:
                self.install_dependencies()
            self.update_vite_config()
            self.update_css()
            self.migrate_files()
            self.fix_duplicate_classes()
            if not self.dry_run:
                self.remove_shoelace()
                self.test_build()

            return {
                'success': True,
                'stats': self.stats
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def install_dependencies(self):
        """安裝依賴"""
        subprocess.run(
            ['npm', 'install', 'tailwindcss@latest', 'daisyui@latest', '@tailwindcss/vite'],
            cwd=self.project_path,
            capture_output=True,
            timeout=120
        )

    def update_vite_config(self):
        """更新 vite.config.js"""
        vite_config = self.project_path / 'vite.config.js'
        if not vite_config.exists():
            return

        content = vite_config.read_text(encoding='utf-8')
        original = content

        if '@tailwindcss/vite' not in content:
            content = "import tailwindcss from '@tailwindcss/vite';\n" + content

        if 'tailwindcss()' not in content:
            content = re.sub(
                r'plugins:\s*\[',
                'plugins: [tailwindcss(), ',
                content
            )

        if content != original and not self.dry_run:
            vite_config.write_text(content, encoding='utf-8')

    def update_css(self):
        """更新 CSS"""
        css_path = self.src_path / 'styles' / 'main.css'
        if not css_path.exists():
            css_path = self.src_path / 'main.css'
        if not css_path.exists():
            return

        content = css_path.read_text(encoding='utf-8')
        if '@import "tailwindcss"' not in content:
            content = '@import "tailwindcss";\n@plugin "daisyui";\n\n' + content
            if not self.dry_run:
                css_path.write_text(content, encoding='utf-8')

    def migrate_files(self):
        """遷移 JS 檔案"""
        if not self.src_path.exists():
            return

        for file_path in self.src_path.rglob('*.js'):
            self._migrate_file(file_path)

    def _migrate_file(self, file_path):
        """遷移單一檔案"""
        content = file_path.read_text(encoding='utf-8')
        original = content

        # 轉換元件
        for pattern, replacement in COMPONENT_MAPPINGS:
            matches = len(re.findall(pattern, content))
            if matches:
                content = re.sub(pattern, replacement, content)
                self.stats['components'] += matches

        # 轉換圖示
        for icon_name, emoji in ICON_MAPPINGS.items():
            pattern = rf'<sl-icon\s+name="{icon_name}"[^>]*>\s*</sl-icon>'
            matches = len(re.findall(pattern, content))
            if matches:
                content = re.sub(pattern, emoji, content)
                self.stats['icons'] += matches

        if content != original:
            self.stats['files'] += 1
            if not self.dry_run:
                file_path.write_text(content, encoding='utf-8')

    def fix_duplicate_classes(self):
        """修復重複 class"""
        if not self.src_path.exists():
            return

        for file_path in self.src_path.rglob('*.js'):
            content = file_path.read_text(encoding='utf-8')
            original = content

            pattern = r'class="([^"]+)"\s+class="([^"]+)"'
            while re.search(pattern, content):
                content = re.sub(pattern, r'class="\1 \2"', content)

            if content != original and not self.dry_run:
                file_path.write_text(content, encoding='utf-8')

    def remove_shoelace(self):
        """移除 Shoelace"""
        subprocess.run(
            ['npm', 'uninstall', '@shoelace-style/shoelace'],
            cwd=self.project_path,
            capture_output=True,
            timeout=60
        )

    def test_build(self):
        """測試建構"""
        result = subprocess.run(
            ['npm', 'run', 'build'],
            cwd=self.project_path,
            capture_output=True,
            timeout=120
        )
        if result.returncode != 0:
            raise Exception('建構失敗')
