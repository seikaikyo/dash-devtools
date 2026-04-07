"""
通用驗證器

適用於所有專案類型
"""

from .security import SecurityValidator
from .quality import QualityValidator
from .spec import SpecValidator
from .i18n_sync import I18nSyncValidator
from .a11y import A11yValidator

__all__ = ['SecurityValidator', 'QualityValidator', 'SpecValidator', 'I18nSyncValidator', 'A11yValidator']
