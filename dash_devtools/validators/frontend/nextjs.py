"""
Next.js 驗證器

檢查內容：
1. SEO: 每個 page.tsx 必須 export metadata（或由 layout 提供）
2. Security Headers: next.config 必須有 headers() 含 CSP/X-Frame 等
3. 頁面結構: Server/Client Component 拆分正確性
"""

import re
from pathlib import Path


class NextjsValidator:
    """Next.js SEO + Security Headers 驗證器"""

    name = 'nextjs'

    REQUIRED_HEADERS = [
        'X-Content-Type-Options',
        'X-Frame-Options',
        'Content-Security-Policy',
        'Referrer-Policy',
    ]

    IGNORE_DIRS = ['node_modules', '.git', '.next', '__pycache__']

    def __init__(self, project_path):
        self.project_path = Path(project_path)
        self.result = {
            'name': self.name,
            'passed': True,
            'errors': [],
            'warnings': [],
            'checks': {},
        }

    def run(self):
        self._check_metadata()
        self._check_security_headers()
        self._check_page_structure()
        return self.result

    def _check_metadata(self):
        """檢查所有 page.tsx 是否 export metadata"""
        app_dir = self.project_path / 'src' / 'app'
        if not app_dir.exists():
            app_dir = self.project_path / 'app'
        if not app_dir.exists():
            return

        pages = list(app_dir.rglob('page.tsx')) + list(app_dir.rglob('page.ts'))
        missing = []
        covered = []

        # 收集所有 layout 有 metadata 的路由前綴
        layout_metadata_dirs = set()
        for layout_file in list(app_dir.rglob('layout.tsx')) + list(app_dir.rglob('layout.ts')):
            content = layout_file.read_text(encoding='utf-8', errors='ignore')
            if 'export const metadata' in content or 'export async function generateMetadata' in content:
                layout_metadata_dirs.add(str(layout_file.parent))

        for page_file in pages:
            rel = page_file.relative_to(self.project_path)
            content = page_file.read_text(encoding='utf-8', errors='ignore')

            has_metadata = (
                'export const metadata' in content
                or 'export async function generateMetadata' in content
            )
            has_redirect = 'redirect(' in content

            # 根目錄 page.tsx 由 root layout 覆蓋
            is_root = page_file.parent == app_dir

            # 檢查是否有 layout 提供 metadata
            covered_by_layout = any(
                str(page_file.parent).startswith(d)
                for d in layout_metadata_dirs
            )

            if has_metadata or has_redirect or is_root:
                covered.append(str(rel))
            elif covered_by_layout:
                covered.append(str(rel))
            else:
                missing.append(str(rel))

        self.result['checks']['metadata'] = {
            'total': len(pages),
            'covered': len(covered),
            'missing': missing,
        }

        if missing:
            self.result['warnings'].append(
                f'缺少 SEO metadata 的頁面: {", ".join(missing)}'
            )

    def _check_security_headers(self):
        """檢查 next.config 是否有 security headers"""
        config_files = [
            self.project_path / 'next.config.ts',
            self.project_path / 'next.config.js',
            self.project_path / 'next.config.mjs',
        ]

        config_file = None
        for f in config_files:
            if f.exists():
                config_file = f
                break

        if not config_file:
            return

        content = config_file.read_text(encoding='utf-8', errors='ignore')

        # 檢查 headers() 函式是否存在
        has_headers_fn = bool(re.search(r'(?:async\s+)?headers\s*\(\s*\)', content))

        missing_headers = []
        if has_headers_fn:
            for header in self.REQUIRED_HEADERS:
                if header not in content:
                    missing_headers.append(header)
        else:
            missing_headers = list(self.REQUIRED_HEADERS)

        self.result['checks']['security_headers'] = {
            'has_headers_fn': has_headers_fn,
            'missing': missing_headers,
        }

        if not has_headers_fn:
            self.result['errors'].append(
                f'next.config 缺少 headers() 函式，無 security headers 防護'
            )
            self.result['passed'] = False
        elif missing_headers:
            self.result['warnings'].append(
                f'next.config 缺少 security headers: {", ".join(missing_headers)}'
            )

    def _check_page_structure(self):
        """檢查 use client 的 page.tsx 是否應該拆分"""
        app_dir = self.project_path / 'src' / 'app'
        if not app_dir.exists():
            app_dir = self.project_path / 'app'
        if not app_dir.exists():
            return

        client_pages = []
        for page_file in list(app_dir.rglob('page.tsx')) + list(app_dir.rglob('page.ts')):
            content = page_file.read_text(encoding='utf-8', errors='ignore')
            # page.tsx 有 'use client' 且沒有 metadata export = 需要拆分
            if "'use client'" in content or '"use client"' in content:
                has_metadata = 'export const metadata' in content
                if not has_metadata:
                    rel = page_file.relative_to(self.project_path)
                    client_pages.append(str(rel))

        self.result['checks']['page_structure'] = {
            'client_pages_without_metadata': client_pages,
        }

        if client_pages:
            self.result['errors'].append(
                f"page.tsx 同時有 'use client' 且無 metadata export（無法 SEO）: "
                f'{", ".join(client_pages)}'
            )
            self.result['passed'] = False
