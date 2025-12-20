"""
效能驗證器

檢查項目：
1. Bundle 大小限制
2. 圖片優化
3. 未使用的依賴
4. CSS 編譯狀態
"""

import json
import subprocess
from pathlib import Path


class PerformanceValidator:
    """效能驗證器"""

    name = 'performance'

    # 限制設定
    LIMITS = {
        'max_css_kb': 200,        # CSS 最大 200KB
        'min_css_kb': 30,         # CSS 最小 30KB (確保 Tailwind 編譯)
        'max_js_kb': 500,         # JS 最大 500KB
        'max_image_kb': 500,      # 圖片最大 500KB
    }

    def __init__(self, project_path):
        self.project_path = Path(project_path)
        self.project_name = self.project_path.name
        self.dist_path = self.project_path / 'dist'
        self.result = {
            'name': self.name,
            'passed': True,
            'errors': [],
            'warnings': [],
            'checks': {}
        }

    def run(self):
        """執行所有驗證"""
        if not self.project_path.exists():
            self.result['passed'] = False
            self.result['errors'].append(f'專案路徑不存在: {self.project_path}')
            return self.result

        self.check_bundle_size()
        self.check_image_sizes()
        self.check_unused_dependencies()

        return self.result

    def check_bundle_size(self):
        """檢查 Bundle 大小"""
        if not self.dist_path.exists():
            self.result['warnings'].append('dist 目錄不存在，跳過 bundle 檢查')
            return

        css_files = list(self.dist_path.rglob('*.css'))
        js_files = list(self.dist_path.rglob('*.js'))

        # CSS 檢查
        total_css_size = sum(f.stat().st_size for f in css_files)
        css_kb = total_css_size / 1024

        self.result['checks']['css_bundle'] = {
            'size_kb': round(css_kb, 1),
            'files': len(css_files)
        }

        if css_kb < self.LIMITS['min_css_kb']:
            self.result['warnings'].append(
                f'CSS 過小 ({css_kb:.1f} KB)，可能 Tailwind 未正確編譯'
            )
        elif css_kb > self.LIMITS['max_css_kb']:
            self.result['warnings'].append(
                f'CSS 過大 ({css_kb:.1f} KB)，考慮優化'
            )

        # JS 檢查
        total_js_size = sum(f.stat().st_size for f in js_files)
        js_kb = total_js_size / 1024

        self.result['checks']['js_bundle'] = {
            'size_kb': round(js_kb, 1),
            'files': len(js_files)
        }

        if js_kb > self.LIMITS['max_js_kb']:
            self.result['warnings'].append(
                f'JS 過大 ({js_kb:.1f} KB)，考慮 code splitting'
            )

    def check_image_sizes(self):
        """檢查圖片大小"""
        public_path = self.project_path / 'public'
        src_path = self.project_path / 'src'

        large_images = []
        extensions = ['*.png', '*.jpg', '*.jpeg', '*.gif', '*.webp', '*.svg']

        for path in [public_path, src_path]:
            if not path.exists():
                continue
            for ext in extensions:
                for img in path.rglob(ext):
                    size_kb = img.stat().st_size / 1024
                    if size_kb > self.LIMITS['max_image_kb']:
                        large_images.append({
                            'file': str(img.relative_to(self.project_path)),
                            'size_kb': round(size_kb, 1)
                        })

        self.result['checks']['images'] = {
            'large_count': len(large_images),
            'files': large_images
        }

        if large_images:
            for img in large_images[:3]:
                self.result['warnings'].append(
                    f"圖片過大: {img['file']} ({img['size_kb']} KB)"
                )

    def check_unused_dependencies(self):
        """檢查未使用的依賴"""
        pkg_path = self.project_path / 'package.json'
        if not pkg_path.exists():
            return

        try:
            pkg = json.loads(pkg_path.read_text(encoding='utf-8'))
            deps = list(pkg.get('dependencies', {}).keys())

            # 簡單檢查：搜尋 src 中是否有 import
            src_path = self.project_path / 'src'
            if not src_path.exists():
                return

            all_content = ''
            for f in src_path.rglob('*.js'):
                try:
                    all_content += f.read_text(encoding='utf-8')
                except Exception:
                    pass

            unused = []
            for dep in deps:
                # 跳過一些特殊依賴
                if dep.startswith('@types/') or dep in ['vite', 'tailwindcss', 'daisyui']:
                    continue
                if dep not in all_content and f"'{dep}'" not in all_content:
                    unused.append(dep)

            self.result['checks']['unused_deps'] = {
                'count': len(unused),
                'packages': unused[:10]  # 只顯示前 10 個
            }

            if unused:
                self.result['warnings'].append(
                    f'可能未使用的依賴: {", ".join(unused[:5])}'
                )

        except Exception:
            pass
