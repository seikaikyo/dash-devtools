"""
Pre-commit 檢查
"""

import re
from pathlib import Path


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
]


def run_pre_commit_check(project_path):
    """執行 pre-commit 檢查"""
    project = Path(project_path)
    issues = []

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

        try:
            content = file_path.read_text(encoding='utf-8')
            for pattern, desc in SENSITIVE_PATTERNS:
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
