"""
專案類型偵測器

自動偵測專案的技術堆疊：
- 前端：Angular / Vite / 原生 JS
- 後端：Node.js / Python
- 混合專案
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
                elif '@pxblue/angular-components' in deps:
                    ui_framework = 'pxblue'

                return {
                    'type': 'angular',
                    'version': deps.get('@angular/core', 'unknown'),
                    'ui_framework': ui_framework,
                    'has_tailwind': 'tailwindcss' in deps
                }

            # Vite 偵測
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

            # Vue 偵測
            if 'vue' in deps:
                return {
                    'type': 'vue',
                    'version': deps.get('vue', 'unknown')
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
        # 檢查 requirements.txt
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

            # Vercel Serverless 偵測
            vercel_json = self.project_path / 'vercel.json'
            api_dir = self.project_path / 'api'

            if vercel_json.exists() or api_dir.exists():
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

    def get_applicable_validators(self) -> Set[str]:
        """取得適用的驗證器類型"""
        info = self.detect()
        validators = {'common'}  # 通用驗證器永遠適用

        if info['frontend'] == 'angular':
            validators.add('frontend.angular')
        elif info['frontend'] in ['vite', 'vanilla']:
            validators.add('frontend.vite')
        elif info['frontend'] == 'react':
            validators.add('frontend.react')

        if info['backend'] == 'python':
            validators.add('backend.python')
        elif info['backend'] == 'nodejs':
            validators.add('backend.nodejs')

        return validators
