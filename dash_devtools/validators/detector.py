"""
專案類型偵測器 v2.0

自動偵測專案的技術堆疊：
- 前端：Angular / Vue+Vite / React / Vanilla JS
- 後端：Node.js / Python (FastAPI/Flask/Django)
- 部署：Vercel Serverless / Vercel Proxy / Render

新增功能：
- 區分「Serverless API」與「純 Proxy 閘道」
- 偵測 Vue 3 + DaisyUI 組合
"""

import json
from pathlib import Path
from typing import Set


class ProjectDetector:
    """專案類型偵測器"""

    def __init__(self, project_path):
        self.project_path = Path(project_path)
        self.project_name = self.project_path.name

    def detect(self) -> dict:
        """偵測專案類型，回傳技術堆疊資訊"""
        result = {
            'name': self.project_name,
            'types': set(),
            'frontend': None,
            'backend': None,
            'ui_framework': None,
            'deployment': None,
            'details': {}
        }

        # 偵測前端
        frontend = self._detect_frontend()
        if frontend:
            result['types'].add('frontend')
            result['frontend'] = frontend['type']
            result['ui_framework'] = frontend.get('ui_framework')
            result['details']['frontend'] = frontend

        # 偵測後端
        backend = self._detect_backend()
        if backend:
            result['types'].add('backend')
            result['backend'] = backend['type']
            result['details']['backend'] = backend

        # 偵測部署模式
        deployment = self._detect_deployment()
        if deployment:
            result['deployment'] = deployment
            result['details']['deployment'] = deployment

        # 轉換 set 為 list（JSON 序列化用）
        result['types'] = list(result['types'])

        return result

    def _detect_frontend(self) -> dict | None:
        """偵測前端技術"""
        package_json = self.project_path / 'package.json'

        if not package_json.exists():
            return None

        try:
            pkg = json.loads(package_json.read_text(encoding='utf-8'))
            deps = {**pkg.get('dependencies', {}), **pkg.get('devDependencies', {})}

            # Angular 偵測
            if '@angular/core' in deps:
                ui_framework = None
                if 'primeng' in deps:
                    ui_framework = 'primeng'

                return {
                    'type': 'angular',
                    'version': deps.get('@angular/core', 'unknown'),
                    'ui_framework': ui_framework,
                    'has_tailwind': 'tailwindcss' in deps
                }

            # Vue + Vite 偵測
            if 'vue' in deps:
                ui_framework = None
                if 'daisyui' in deps:
                    ui_framework = 'daisyui'
                elif '@shoelace-style/shoelace' in deps:
                    ui_framework = 'shoelace'

                return {
                    'type': 'vue-vite' if 'vite' in deps else 'vue',
                    'version': deps.get('vue', 'unknown'),
                    'ui_framework': ui_framework,
                    'has_tailwind': 'tailwindcss' in deps or '@tailwindcss/vite' in deps,
                    'has_typescript': 'typescript' in deps or 'vue-tsc' in deps
                }

            # Vite (非 Vue)
            if 'vite' in deps:
                ui_framework = None
                if 'daisyui' in deps:
                    ui_framework = 'daisyui'
                elif '@shoelace-style/shoelace' in deps:
                    ui_framework = 'shoelace'

                return {
                    'type': 'vite',
                    'version': deps.get('vite', 'unknown'),
                    'ui_framework': ui_framework,
                    'has_tailwind': 'tailwindcss' in deps
                }

            # React 偵測
            if 'react' in deps:
                return {
                    'type': 'react',
                    'version': deps.get('react', 'unknown'),
                    'ui_framework': self._detect_react_ui(deps)
                }

            # 原生 JS（有 package.json 但無框架）
            return {
                'type': 'vanilla',
                'ui_framework': None
            }

        except Exception:
            return None

    def _detect_react_ui(self, deps: dict) -> str | None:
        """偵測 React UI 框架"""
        if '@mui/material' in deps:
            return 'mui'
        if 'antd' in deps:
            return 'antd'
        if '@chakra-ui/react' in deps:
            return 'chakra'
        return None

    def _detect_backend(self) -> dict | None:
        """偵測後端技術"""
        # Python 後端偵測
        python_result = self._detect_python_backend()
        if python_result:
            return python_result

        # Node.js 後端偵測
        nodejs_result = self._detect_nodejs_backend()
        if nodejs_result:
            return nodejs_result

        return None

    def _detect_python_backend(self) -> dict | None:
        """偵測 Python 後端"""
        requirements = self.project_path / 'requirements.txt'
        pyproject = self.project_path / 'pyproject.toml'
        setup_py = self.project_path / 'setup.py'

        if not any(f.exists() for f in [requirements, pyproject, setup_py]):
            return None

        framework = None
        deps_content = ''

        if requirements.exists():
            deps_content = requirements.read_text(encoding='utf-8').lower()
        elif pyproject.exists():
            deps_content = pyproject.read_text(encoding='utf-8').lower()

        # 偵測框架
        if 'fastapi' in deps_content:
            framework = 'fastapi'
        elif 'flask' in deps_content:
            framework = 'flask'
        elif 'django' in deps_content:
            framework = 'django'
        elif 'streamlit' in deps_content:
            framework = 'streamlit'

        return {
            'type': 'python',
            'framework': framework
        }

    def _detect_nodejs_backend(self) -> dict | None:
        """偵測 Node.js 後端"""
        package_json = self.project_path / 'package.json'

        if not package_json.exists():
            return None

        try:
            pkg = json.loads(package_json.read_text(encoding='utf-8'))
            deps = {**pkg.get('dependencies', {}), **pkg.get('devDependencies', {})}

            # Vercel Serverless 偵測（有 api/ 目錄且有函數檔案）
            api_dir = self.project_path / 'api'
            if api_dir.exists():
                api_files = list(api_dir.rglob('*.js')) + list(api_dir.rglob('*.ts'))
                if api_files:
                    return {
                        'type': 'nodejs',
                        'framework': 'vercel-serverless'
                    }

            # Express 偵測
            if 'express' in deps:
                return {
                    'type': 'nodejs',
                    'framework': 'express'
                }

            # Fastify 偵測
            if 'fastify' in deps:
                return {
                    'type': 'nodejs',
                    'framework': 'fastify'
                }

            # NestJS 偵測
            if '@nestjs/core' in deps:
                return {
                    'type': 'nodejs',
                    'framework': 'nestjs'
                }

        except Exception:
            pass

        return None

    def _detect_deployment(self) -> dict | None:
        """偵測部署模式"""
        vercel_json = self.project_path / 'vercel.json'

        if not vercel_json.exists():
            return None

        try:
            config = json.loads(vercel_json.read_text(encoding='utf-8'))
            rewrites = config.get('rewrites', [])

            # 檢查是否為純 Proxy 模式
            is_proxy_only = False
            proxy_target = None

            for rewrite in rewrites:
                dest = rewrite.get('destination', '')
                source = rewrite.get('source', '')

                # 如果 destination 是外部 URL，則是 Proxy
                if dest.startswith('http://') or dest.startswith('https://'):
                    is_proxy_only = True
                    proxy_target = dest.split('/')[2]  # 取得域名

            # 檢查是否有 api/ 目錄（Serverless）
            api_dir = self.project_path / 'api'
            has_api_functions = api_dir.exists() and any(api_dir.rglob('*.ts')) or any(api_dir.rglob('*.js'))

            if is_proxy_only and not has_api_functions:
                return {
                    'type': 'vercel-proxy',
                    'proxy_target': proxy_target,
                    'description': '純前端 + API 代理'
                }
            elif has_api_functions:
                return {
                    'type': 'vercel-serverless',
                    'has_proxy': is_proxy_only,
                    'description': 'Serverless Functions' + (' + Proxy' if is_proxy_only else '')
                }
            else:
                return {
                    'type': 'vercel-static',
                    'description': '純靜態網站'
                }

        except Exception:
            pass

        return None

    def get_applicable_validators(self) -> Set[str]:
        """取得適用的驗證器類型"""
        info = self.detect()
        validators = {'common'}  # 通用驗證器永遠適用

        frontend_type = info['frontend']
        if frontend_type == 'angular':
            validators.add('frontend.angular')
        elif frontend_type in ['vite', 'vanilla', 'vue-vite', 'vue']:
            validators.add('frontend.vite')
        elif frontend_type == 'react':
            validators.add('frontend.react')

        backend_type = info['backend']
        if backend_type == 'python':
            validators.add('backend.python')
        elif backend_type == 'nodejs':
            validators.add('backend.nodejs')

        return validators

    def get_project_summary(self) -> str:
        """取得專案摘要（供 CLI 顯示）"""
        info = self.detect()

        parts = []

        # 前端
        if info['frontend']:
            frontend_str = info['frontend']
            if info['ui_framework']:
                frontend_str += f" + {info['ui_framework']}"
            parts.append(f"Frontend: {frontend_str}")

        # 後端
        if info['backend']:
            backend = info['details'].get('backend', {})
            framework = backend.get('framework', '')
            backend_str = f"{info['backend']}"
            if framework:
                backend_str += f" ({framework})"
            parts.append(f"Backend: {backend_str}")

        # 部署
        if info['deployment']:
            deploy = info['deployment']
            parts.append(f"Deploy: {deploy.get('type', 'unknown')}")
            if deploy.get('proxy_target'):
                parts.append(f"Proxy: {deploy['proxy_target']}")

        return ' | '.join(parts) if parts else 'Unknown project type'
