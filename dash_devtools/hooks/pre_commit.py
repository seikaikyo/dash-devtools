"""
Pre-commit 檢查
"""

import re
from pathlib import Path
from fnmatch import fnmatch


# 敏感資料正則表達式
# 注意：要避免假陽性，模式需要精確匹配硬編碼的值，而非變數賦值
SENSITIVE_PATTERNS = [
    # API Key: 必須有引號包住的值（排除函數呼叫）
    (r'(?i)(api[_-]?key|apikey)\s*[=:]\s*["\'][a-zA-Z0-9_-]{20,}["\']', 'API Key'),
    # Secret/Token: 特定命名且有引號包住的值
    (r'(?i)(client_?secret|api_?secret|secret_?key)\s*[=:]\s*["\'][a-zA-Z0-9_-]{20,}["\']', 'Secret/Token'),
    # 密碼: 需要引號且長度 >= 8
    (r'(?i)password\s*[=:]\s*["\'][^"\']{8,}["\']', '密碼'),
    # 特定格式的 Key (這些格式明確，不會有假陽性)
    (r'sk-[a-zA-Z0-9]{48}', 'OpenAI API Key'),
    (r'sk_live_[a-zA-Z0-9]{24,}', 'Stripe Live Key'),
    (r'ghp_[a-zA-Z0-9]{36}', 'GitHub Token'),
    (r'CLERK_SECRET_KEY\s*=\s*["\']?sk_[a-zA-Z0-9_-]{20,}', 'Clerk Secret Key'),
    (r'-----BEGIN (RSA )?PRIVATE KEY-----', '私鑰'),
    (r'AKIA[0-9A-Z]{16}', 'AWS Access Key'),
    # Neon Database API Key (napi_ 開頭)
    (r'napi_[a-zA-Z0-9]{60,}', 'Neon API Key'),
    # PostgreSQL 連線字串 (含密碼)
    (r'postgres(?:ql)?://[^:<]+:[^@<]+@[^\s"\']+', 'PostgreSQL 連線字串'),
    # Neon PostgreSQL 密碼 (npg_ 開頭)
    (r'npg_[a-zA-Z0-9]{10,}', 'Neon PostgreSQL 密碼'),
]


def parse_scanignore(project_path):
    """解析 .scanignore 檔案

    格式：
    - # 開頭為註解
    - 空行忽略
    - path/to/file 或 path/to/dir/ - 排除檔案或目錄
    - [pattern:名稱] path/glob - 只排除特定 pattern

    Returns:
        dict: {
            'paths': [str, ...],                    # 全排除的路徑 glob
            'pattern_paths': [(pattern_name, glob), ...]  # 特定 pattern 排除
        }
    """
    scanignore_file = Path(project_path) / '.scanignore'
    result = {'paths': [], 'pattern_paths': []}

    if not scanignore_file.exists():
        return result

    try:
        for line in scanignore_file.read_text(encoding='utf-8').splitlines():
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            # [pattern:名稱] path/glob
            pattern_match = re.match(r'^\[pattern:(.+?)\]\s+(.+)$', line)
            if pattern_match:
                pattern_name = pattern_match.group(1).strip()
                path_glob = pattern_match.group(2).strip()
                result['pattern_paths'].append((pattern_name, path_glob))
            else:
                result['paths'].append(line)
    except Exception:
        pass

    return result


def is_scan_ignored(rel_path, pattern_name, scanignore):
    """檢查檔案是否在 .scanignore 中

    Args:
        rel_path: 相對於專案根目錄的路徑 (str)
        pattern_name: 目前檢測的 pattern 名稱 (str)，None 表示檢查所有 pattern
        scanignore: parse_scanignore() 的回傳值

    Returns:
        bool: True 表示應跳過
    """
    # 全排除路徑
    for glob_pattern in scanignore['paths']:
        # 目錄匹配 (pattern 以 / 結尾或不含 .)
        if glob_pattern.endswith('/'):
            if rel_path.startswith(glob_pattern) or rel_path.startswith(glob_pattern.rstrip('/')):
                return True
        # glob 匹配
        if fnmatch(rel_path, glob_pattern):
            return True
        # 前綴匹配 (目錄)
        if rel_path.startswith(glob_pattern.rstrip('/') + '/'):
            return True

    # 特定 pattern 排除
    if pattern_name:
        for p_name, p_glob in scanignore['pattern_paths']:
            if p_name == pattern_name:
                if fnmatch(rel_path, p_glob):
                    return True
                if p_glob.endswith('/') and rel_path.startswith(p_glob.rstrip('/') + '/'):
                    return True
                if rel_path.startswith(p_glob.rstrip('/') + '/'):
                    return True

    return False


def run_pre_commit_check(project_path):
    """執行 pre-commit 檢查"""
    project = Path(project_path)
    issues = []
    scanignore = parse_scanignore(project_path)

    # 檢查 staged 檔案
    import subprocess
    result = subprocess.run(
        ['git', 'diff', '--cached', '--name-only'],
        cwd=project,
        capture_output=True,
        text=True
    )

    staged_files = result.stdout.strip().split('\n') if result.stdout.strip() else []

    for file_name in staged_files:
        file_path = project / file_name
        if not file_path.exists() or not file_path.is_file():
            continue

        # 跳過二進制檔案
        if file_path.suffix in ['.png', '.jpg', '.gif', '.ico', '.pdf', '.zip']:
            continue

        # 跳過 .scanignore 全排除的檔案
        if is_scan_ignored(file_name, None, scanignore):
            continue

        try:
            content = file_path.read_text(encoding='utf-8')
            for pattern, desc in SENSITIVE_PATTERNS:
                # 跳過 .scanignore 特定 pattern 排除
                if is_scan_ignored(file_name, desc, scanignore):
                    continue
                if re.search(pattern, content):
                    issues.append({
                        'file': file_name,
                        'type': desc
                    })
        except Exception:
            pass

    return {
        'passed': len(issues) == 0,
        'issues': issues
    }
