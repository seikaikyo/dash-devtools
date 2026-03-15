"""
圖表生成模組

提供測試報告用的圖表：
- 通過率圓餅圖
- 各類型測試長條圖
"""

import io
from typing import Dict, Optional

try:
    import matplotlib
    matplotlib.use('Agg')  # 非互動模式
    import matplotlib.pyplot as plt
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False


# macOS 中文字型設定
CHINESE_FONTS_PIE = ['Arial Unicode MS', 'Heiti TC', 'PingFang TC', 'STHeiti']
CHINESE_FONTS_BAR = ['Arial Unicode MS', 'Heiti TC', 'PingFang TC', 'Microsoft JhengHei']

# 圖表配色
COLOR_PASS = '#4CAF50'
COLOR_FAIL = '#F44336'
COLOR_EMPTY = '#E0E0E0'


def _setup_chinese_fonts(font_list: list):
    """設定 matplotlib 中文字型"""
    plt.rcParams['font.sans-serif'] = font_list
    plt.rcParams['axes.unicode_minus'] = False


def create_pass_rate_chart(passed: int, failed: int) -> Optional[bytes]:
    """建立通過率圓餅圖"""
    if not HAS_MATPLOTLIB:
        return None

    _setup_chinese_fonts(CHINESE_FONTS_PIE)

    fig, ax = plt.subplots(figsize=(4, 4))

    if passed + failed == 0:
        sizes = [1]
        colors = [COLOR_EMPTY]
        labels = ['無測試']
    else:
        sizes = [passed, failed] if failed > 0 else [passed]
        colors = [COLOR_PASS, COLOR_FAIL] if failed > 0 else [COLOR_PASS]
        labels = ['通過', '失敗'] if failed > 0 else ['通過']

    wedges, texts, autotexts = ax.pie(
        sizes,
        labels=labels,
        colors=colors,
        autopct='%1.1f%%',
        startangle=90,
        textprops={'fontsize': 12}
    )

    ax.set_title('測試通過率', fontsize=14, fontweight='bold')

    # 儲存為 bytes
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    buf.seek(0)
    return buf.read()


def create_test_type_chart(results: Dict) -> Optional[bytes]:
    """建立各類型測試長條圖"""
    if not HAS_MATPLOTLIB:
        return None

    # 過濾掉未設定的測試
    configured_results = {k: v for k, v in results.items() if not v.get('not_configured', False)}
    if not configured_results:
        return None

    _setup_chinese_fonts(CHINESE_FONTS_BAR)

    fig, ax = plt.subplots(figsize=(8, 4))

    types = list(configured_results.keys())
    passed = [configured_results[t].get('passed', 0) for t in types]
    failed = [configured_results[t].get('failed', 0) for t in types]

    x = range(len(types))
    width = 0.35

    bars1 = ax.bar([i - width/2 for i in x], passed, width, label='通過', color=COLOR_PASS)
    bars2 = ax.bar([i + width/2 for i in x], failed, width, label='失敗', color=COLOR_FAIL)

    ax.set_ylabel('測試數量')
    ax.set_title('各類型測試結果', fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(types)
    ax.legend()

    # 加上數值標籤
    for bar in bars1:
        height = bar.get_height()
        if height > 0:
            ax.annotate(f'{int(height)}',
                       xy=(bar.get_x() + bar.get_width() / 2, height),
                       xytext=(0, 3),
                       textcoords="offset points",
                       ha='center', va='bottom', fontsize=10)

    for bar in bars2:
        height = bar.get_height()
        if height > 0:
            ax.annotate(f'{int(height)}',
                       xy=(bar.get_x() + bar.get_width() / 2, height),
                       xytext=(0, 3),
                       textcoords="offset points",
                       ha='center', va='bottom', fontsize=10)

    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    buf.seek(0)
    return buf.read()
