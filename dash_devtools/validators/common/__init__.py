"""
通用驗證器

適用於所有專案類型
"""

from .security import SecurityValidator
from .quality import QualityValidator

__all__ = ['SecurityValidator', 'QualityValidator']
