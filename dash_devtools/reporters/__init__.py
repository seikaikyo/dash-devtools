"""
報告產生工具

包含圖表生成、模板樣式、資料收集與截圖模組。
"""

from .report_data import (
    TestResult,
    ScreenshotResult,
    ReportData,
    collect_health,
    collect_stats,
    run_tests,
)
from .screenshot import take_screenshots
from .charts import (
    HAS_MATPLOTLIB,
    create_pass_rate_chart,
    create_test_type_chart,
)
from .templates import (
    # 色彩常數
    COLOR_PASS_RGB,
    COLOR_FAIL_RGB,
    COLOR_SKIP_RGB,
    COLOR_GREY_RGB,
    COLOR_LIGHT_GREY_RGB,
    COLOR_SUBTITLE_RGB,
    COLOR_HEADER_HEX,
    COLOR_LABEL_BG_HEX,
    COLOR_PASS_BG_HEX,
    COLOR_FAIL_BG_HEX,
    COLOR_API_RGB,
    COLOR_TERMINAL_RGB,
    COLOR_CODE_RGB,
    # 測試類型
    TYPE_LABELS,
    TYPE_DESCRIPTIONS,
    # 函數
    set_cell_shading,
    format_duration,
    format_duration_detail,
    format_table_duration,
    rgb,
    # 文件建構
    build_single_test_case,
    build_text_output,
)

__all__ = [
    # report_data
    'TestResult',
    'ScreenshotResult',
    'ReportData',
    'collect_health',
    'collect_stats',
    'run_tests',
    # screenshot
    'take_screenshots',
    # charts
    'HAS_MATPLOTLIB',
    'create_pass_rate_chart',
    'create_test_type_chart',
    # templates - 色彩
    'COLOR_PASS_RGB',
    'COLOR_FAIL_RGB',
    'COLOR_SKIP_RGB',
    'COLOR_GREY_RGB',
    'COLOR_LIGHT_GREY_RGB',
    'COLOR_SUBTITLE_RGB',
    'COLOR_HEADER_HEX',
    'COLOR_LABEL_BG_HEX',
    'COLOR_PASS_BG_HEX',
    'COLOR_FAIL_BG_HEX',
    'COLOR_API_RGB',
    'COLOR_TERMINAL_RGB',
    'COLOR_CODE_RGB',
    # templates - 類型
    'TYPE_LABELS',
    'TYPE_DESCRIPTIONS',
    # templates - 函數
    'set_cell_shading',
    'format_duration',
    'format_duration_detail',
    'format_table_duration',
    'rgb',
    # templates - 文件建構
    'build_single_test_case',
    'build_text_output',
]


def generate_html_report(results, output_path):
    """產生 HTML 報告"""
    # TODO: 實作 HTML 報告產生
    pass
