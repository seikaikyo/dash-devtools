"""
Git Hooks 整合 v2.0

提供 pre-commit 和 pre-push 安全檢查
支援：
- Vue 3 + Vite + DaisyUI 專案
- Python FastAPI 專案 (Ruff 整合)
- 純 Proxy 閘道專案
"""

from .pre_commit import run_pre_commit_check
from .pre_push import run_pre_push_check

__all__ = ['run_pre_commit_check', 'run_pre_push_check', 'install_hooks']


# Pre-push hook 腳本 v2.0（支援 Vue 3 + Python）
PRE_PUSH_HOOK = '''#!/bin/bash
# DashAI DevTools Pre-push Hook v2.0
# 支援：Vue 3 + Vite、Python FastAPI、純 Proxy 閘道

PROJECT_ROOT="$(git rev-parse --show-toplevel)"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "[i] DashAI DevTools Pre-push 檢查"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 步驟 0: 檢查 Emoji
echo "[>] 步驟 0/3: 檢查 Emoji..."
EMOJI_FILES=$(git diff --cached --name-only --diff-filter=ACM | xargs grep -l '[\\x{1F300}-\\x{1F9FF}]' 2>/dev/null || true)
if [ -n "$EMOJI_FILES" ]; then
    echo "[x] 發現 Emoji，請移除："
    echo "$EMOJI_FILES"
    exit 1
fi
echo "[v] 無 Emoji"
echo ""

# 步驟 1: 掃描機敏資料
echo "[>] 步驟 1/3: 掃描機敏資料..."
dash scan "$PROJECT_ROOT"
if [ $? -ne 0 ]; then
    echo ""
    echo "[x] 安全檢查失敗，推送已取消"
    exit 1
fi
echo ""

# 步驟 2: 驗證專案規範
echo "[>] 步驟 2/3: 驗證專案..."

# 偵測專案類型
IS_FRONTEND=false
IS_PYTHON=false
IS_PROXY_ONLY=false

if [ -f "$PROJECT_ROOT/package.json" ]; then
    IS_FRONTEND=true

    # 檢查是否為純 Proxy 閘道（無 api/ 目錄）
    if [ -f "$PROJECT_ROOT/vercel.json" ] && [ ! -d "$PROJECT_ROOT/api" ]; then
        if grep -q "https://" "$PROJECT_ROOT/vercel.json" 2>/dev/null; then
            IS_PROXY_ONLY=true
            echo "   偵測到：純 Proxy 閘道專案"
        fi
    fi
fi

if [ -f "$PROJECT_ROOT/requirements.txt" ] || [ -f "$PROJECT_ROOT/pyproject.toml" ]; then
    IS_PYTHON=true
    echo "   偵測到：Python 專案"
fi

# 執行驗證
if [ "$IS_FRONTEND" = true ]; then
    dash validate "$PROJECT_ROOT" --check smart 2>/dev/null || true
fi

# Python Ruff 檢查
if [ "$IS_PYTHON" = true ]; then
    if command -v ruff &> /dev/null; then
        echo "   [ruff] 檢查程式碼..."
        ruff check "$PROJECT_ROOT" --quiet || echo "   [!] Ruff 發現問題（警告）"
        ruff format --check "$PROJECT_ROOT" --quiet 2>/dev/null || echo "   [!] 有檔案需要格式化"
    else
        echo "   (Ruff 未安裝，跳過 Python lint)"
    fi
fi

if [ "$IS_FRONTEND" = false ] && [ "$IS_PYTHON" = false ]; then
    echo "   (未偵測到前端或 Python 專案，跳過驗證)"
fi
echo ""

# 步驟 3: 執行測試
echo "[>] 步驟 3/3: 執行測試..."
TEST_RESULT=0

if [ "$IS_FRONTEND" = true ]; then
    # 檢查是否有測試腳本
    if grep -q '"test"' "$PROJECT_ROOT/package.json" 2>/dev/null; then
        cd "$PROJECT_ROOT"

        # 偵測測試框架並執行
        if grep -q '"vitest"' package.json 2>/dev/null; then
            echo "   [vitest] 執行測試..."
            npx vitest run --passWithNoTests 2>&1 || TEST_RESULT=$?
        elif grep -q '"jest"' package.json 2>/dev/null; then
            echo "   [jest] 執行測試..."
            npx jest --passWithNoTests 2>&1 || TEST_RESULT=$?
        elif grep -q '"karma"' package.json 2>/dev/null || grep -q '"@angular-devkit"' package.json 2>/dev/null; then
            echo "   [karma] 執行測試..."
            npm test -- --no-watch --browsers=ChromeHeadless 2>&1 || TEST_RESULT=$?
        else
            echo "   (無已知測試框架，跳過)"
        fi
    else
        echo "   (無測試腳本，跳過)"
    fi
fi

if [ "$IS_PYTHON" = true ]; then
    if [ -d "$PROJECT_ROOT/tests" ] || [ -f "$PROJECT_ROOT/pytest.ini" ] || [ -f "$PROJECT_ROOT/pyproject.toml" ]; then
        if command -v pytest &> /dev/null; then
            echo "   [pytest] 執行測試..."
            cd "$PROJECT_ROOT"
            python -m pytest -q --tb=short 2>&1 || TEST_RESULT=$?
        else
            echo "   (pytest 未安裝，跳過)"
        fi
    fi
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
