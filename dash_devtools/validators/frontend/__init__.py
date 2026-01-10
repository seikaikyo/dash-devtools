"""
前端驗證器

支援框架：
- Vite + Tailwind + DaisyUI
- Angular + PrimeNG
- GAS (Google Apps Script) + Vue 3 + Shoelace/DaisyUI
"""

from .vite import ViteValidator
from .angular import AngularValidator
from .gas import GasValidator

__all__ = ['ViteValidator', 'AngularValidator', 'GasValidator']
