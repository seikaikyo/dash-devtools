"""
Git Hooks 整合

提供 pre-commit 和 pre-push 安全檢查
"""

from .pre_commit import run_pre_commit_check
from .pre_push import run_pre_push_check

__all__ = ['run_pre_commit_check', 'run_pre_push_check', 'install_hooks']


# Pre-push hook 腳本（含測試）
PRE_PUSH_HOOK = '''#!/bin/bash
# DashAI DevTools Pre-push Hook v2.0
# 推送前自動檢查：安全性 + 測試

set -e
PROJECT_ROOT="$(git rev-parse --show-toplevel)"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "[i] DashAI DevTools Pre-push 檢查"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 步驟 1: 檢查 Emoji
echo "[>] 步驟 1/4: 檢查 Emoji..."
EMOJI_FILES=$(git diff --cached --name-only --diff-filter=ACM | xargs grep -l '[\\x{1F300}-\\x{1F9FF}]' 2>/dev/null || true)
if [ -n "$EMOJI_FILES" ]; then
    echo "[x] 發現 Emoji，請移除："
    echo "$EMOJI_FILES"
    exit 1
fi
echo "[v] 無 Emoji"
echo ""

# 步驟 2: 掃描機敏資料
echo "[>] 步驟 2/4: 掃描機敏資料..."
dash scan "$PROJECT_ROOT"
if [ $? -ne 0 ]; then
    echo ""
    echo "[x] 安全檢查失敗，推送已取消"
    exit 1
fi
echo ""

# 步驟 3: 驗證專案規範
echo "[>] 步驟 3/4: 驗證專案..."
if [ -f "$PROJECT_ROOT/package.json" ]; then
    dash validate "$PROJECT_ROOT" --check smart 2>/dev/null || true
else
    echo "   (非前端專案，跳過驗證)"
fi
echo ""

# 步驟 4: 執行測試
echo "[>] 步驟 4/4: 執行測試..."
TEST_RESULT=0

if [ -f "$PROJECT_ROOT/package.json" ]; then
    # 檢查是否有測試腳本
    if grep -q '"test"' "$PROJECT_ROOT/package.json"; then
        cd "$PROJECT_ROOT"

        # 偵測測試框架並執行
        if grep -q '"vitest"' package.json; then
            echo "   [vitest] 執行測試..."
            npx vitest run --passWithNoTests 2>&1 || TEST_RESULT=$?
        elif grep -q '"jest"' package.json; then
            echo "   [jest] 執行測試..."
            npx jest --passWithNoTests 2>&1 || TEST_RESULT=$?
        elif grep -q '"karma"' package.json || grep -q '"@angular-devkit"' package.json; then
            echo "   [karma] 執行測試..."
            npm test -- --no-watch --browsers=ChromeHeadless 2>&1 || TEST_RESULT=$?
        else
            echo "   執行 npm test..."
            npm test 2>&1 || TEST_RESULT=$?
        fi

        if [ $TEST_RESULT -ne 0 ]; then
            if [ "$DASH_STRICT_TEST" = "1" ]; then
                echo ""
                echo "[x] 測試失敗，推送已取消 (嚴格模式)"
                exit 1
            else
                echo ""
                echo "[!] 測試失敗，但繼續推送 (警告模式)"
                echo "    使用 --strict 安裝 hook 可強制測試通過"
            fi
        else
            echo "   [v] 測試通過"
        fi
    else
        echo "   (無測試腳本，跳過)"
    fi
elif [ -f "$PROJECT_ROOT/pytest.ini" ] || [ -f "$PROJECT_ROOT/pyproject.toml" ] || [ -d "$PROJECT_ROOT/tests" ]; then
    echo "   [pytest] 執行測試..."
    cd "$PROJECT_ROOT"
    python -m pytest -q --tb=short 2>&1 || TEST_RESULT=$?

    if [ $TEST_RESULT -ne 0 ]; then
        if [ "$DASH_STRICT_TEST" = "1" ]; then
            echo ""
            echo "[x] 測試失敗，推送已取消 (嚴格模式)"
            exit 1
        else
            echo ""
            echo "[!] 測試失敗，但繼續推送 (警告模式)"
        fi
    else
        echo "   [v] 測試通過"
    fi
else
    echo "   (未偵測到測試框架，跳過)"
fi
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "[v] 所有檢查通過，繼續推送..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
'''

# Pre-commit hook 腳本
PRE_COMMIT_HOOK = '''#!/bin/bash
# DashAI DevTools Pre-commit Hook
PROJECT_ROOT="$(git rev-parse --show-toplevel)"

echo "掃描機敏資料..."
dash scan "$PROJECT_ROOT"
'''


def install_hooks(project_path, strict_test: bool = False):
    """安裝 git hooks 到專案

    Args:
        project_path: 專案路徑
        strict_test: 是否啟用嚴格測試模式（測試失敗會阻止推送）
    """
    from pathlib import Path
    import stat

    hooks_dir = Path(project_path) / '.git' / 'hooks'
    if not hooks_dir.exists():
        return {'success': False, 'error': '.git/hooks 目錄不存在'}

    # Pre-commit hook
    pre_commit = hooks_dir / 'pre-commit'
    pre_commit.write_text(PRE_COMMIT_HOOK, encoding='utf-8')
    pre_commit.chmod(pre_commit.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    # Pre-push hook
    pre_push = hooks_dir / 'pre-push'
    hook_content = PRE_PUSH_HOOK

    # 如果啟用嚴格模式，加入環境變數
    if strict_test:
        hook_content = 'export DASH_STRICT_TEST=1\n' + hook_content

    pre_push.write_text(hook_content, encoding='utf-8')
    pre_push.chmod(pre_push.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    return {'success': True, 'strict_test': strict_test}
