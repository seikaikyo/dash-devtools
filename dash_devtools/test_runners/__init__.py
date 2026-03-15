"""
測試執行器模組

提供各測試框架的統一介面：
- Vitest (推薦)
- Jest
- Pytest
- Karma (Playwright-based: Smoke/E2E/UAT)
"""

from .vitest import run_vitest
from .jest import run_jest
from .pytest_runner import run_pytest
from .karma import (
    run_playwright_tests,
    parse_playwright_suite,
)

__all__ = [
    'run_vitest',
    'run_jest',
    'run_pytest',
    'run_playwright_tests',
    'parse_playwright_suite',
]
