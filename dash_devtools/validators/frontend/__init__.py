"""
前端驗證器

支援框架：
- Vite + Vue 3 + PrimeVue
- Angular + PrimeNG
- GAS (Google Apps Script) + Vue 3
- Next.js (React + App Router)
"""

from .vite import ViteValidator
from .angular import AngularValidator
from .gas import GasValidator
from .nextjs import NextjsValidator

__all__ = ['ViteValidator', 'AngularValidator', 'GasValidator', 'NextjsValidator']
