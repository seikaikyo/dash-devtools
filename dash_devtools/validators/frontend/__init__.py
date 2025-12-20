"""
前端驗證器

支援框架：
- Vite + Tailwind + DaisyUI
- Angular + PrimeNG
"""

from .vite import ViteValidator
from .angular import AngularValidator

__all__ = ['ViteValidator', 'AngularValidator']
