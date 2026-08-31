"""路徑排除比對（掃描器共用）

掃描器先前用裸字串包含比對判斷排除目錄與 .gitignore：

    any(ignore in str(file_path) for ignore in ignore_dirs)   # dist / test / spec ...
    if pattern in rel_path: return True                       # .gitignore 任一行

兩者都會把真實原始碼靜默跳過（src/api/distributor.ts 含 dist、src/lib/latest.ts 含 test、
專案根目錄叫 latest-app 時整個 repo 都跳過），掃描仍回報通過。

本模組改用路徑元件比對與 fnmatch，是 dash_devtools/commands/analyze.py 既有正確寫法的共用版本。
只用標準庫，不新增相依。
"""

from fnmatch import fnmatch
from pathlib import Path


def to_relative_parts(file_path, project_path):
    """取得檔案相對於專案根目錄的路徑元件

    無法相對化時（不在專案底下）回傳絕對路徑元件，寧可多掃不少掃。
    """
    file_path = Path(file_path)
    try:
        rel = file_path.relative_to(Path(project_path))
    except ValueError:
        rel = file_path
    return rel.parts


def is_under(file_path, ancestor):
    """檔案是否位於 ancestor 目錄底下

    裸字串 startswith 會把 /p/foobar/x.py 判成在 /p/foo 底下，讓相鄰目錄
    整批被誤跳過。改用路徑關係判定，只有真正的祖先才算。
    """
    file_path = Path(file_path).resolve()
    ancestor = Path(ancestor).resolve()
    if file_path == ancestor:
        return True
    return ancestor in file_path.parents


def is_in_ignored_dir(file_path, project_path, ignore_dirs):
    """檔案是否位於排除目錄底下

    只比對相對路徑的「目錄」元件，且要求整段相等。
    src/api/distributor.ts 不會因為含有 dist 就被跳過。
    """
    parts = to_relative_parts(file_path, project_path)
    if not parts:
        return False
    ignore_set = set(ignore_dirs)
    return any(part in ignore_set for part in parts[:-1])


def parse_gitignore(project_path):
    """讀出 .gitignore 的有效規則（保留順序，反向規則要靠順序判定）"""
    gitignore = Path(project_path) / '.gitignore'
    if not gitignore.exists():
        return []

    patterns = []
    try:
        for line in gitignore.read_text(encoding='utf-8').splitlines():
            line = line.strip()
            if line and not line.startswith('#'):
                patterns.append(line)
    except Exception:
        return []
    return patterns


def _matches(pattern, rel_path):
    """單一 gitignore 規則是否命中（不含 ! 反向處理）

    規則語意：
    - 結尾 / 表示只比對目錄元件
    - 含有斜線（結尾斜線除外）表示錨定專案根目錄
    - 其餘規則比對任一層的路徑元件
    """
    dir_only = pattern.endswith('/')
    pattern = pattern.rstrip('/')
    if not pattern:
        return False

    parts = rel_path.split('/')
    anchored = '/' in pattern
    pattern = pattern.lstrip('/')
    if not pattern:
        return False

    if anchored:
        if not dir_only and fnmatch(rel_path, pattern):
            return True
        # 目錄型規則：命中任一層前綴即代表整個子樹被排除
        for i in range(1, len(parts)):
            if fnmatch('/'.join(parts[:i]), pattern):
                return True
        return False

    # 未錨定：比對任一路徑元件；目錄型規則不比對最後一段（檔名）
    candidates = parts[:-1] if dir_only else parts
    return any(fnmatch(part, pattern) for part in candidates)


def is_gitignored(rel_path, patterns):
    """以 gitignore 語意判斷路徑是否被忽略

    Args:
        rel_path: 相對於專案根目錄的路徑（str，以 / 分隔）
        patterns: parse_gitignore() 的回傳值

    Returns:
        bool

    未支援：被排除目錄底下的檔案無法用 ! 重新納入（與 git 相同）以外的細節，
    例如跳脫字元與 ** 的完整語意。判定偏向「少忽略」，寧可多掃。
    """
    rel_path = str(rel_path).replace('\\', '/')
    if rel_path.startswith('./'):
        rel_path = rel_path[2:]
    ignored = False

    for pattern in patterns:
        negated = pattern.startswith('!')
        if negated:
            pattern = pattern[1:]
        if _matches(pattern, rel_path):
            ignored = not negated

    return ignored
