"""
i18n 同步驗證器

檢查內容：
1. 所有 locale 檔案的 key 一致性
2. 找出某語言有但其他語言缺的 key
3. 支援 .ts/.json 格式的 locale 檔案
"""

import re
import json
from pathlib import Path

from .constants import BANNED_CONCEPTS


class I18nSyncValidator:
    """i18n key 同步驗證器"""

    name = 'i18n_sync'

    LOCALE_DIRS = ['src/locales', 'src/i18n', 'locales', 'i18n', 'src/lib/i18n']

    def __init__(self, project_path):
        self.project_path = Path(project_path)
        self.result = {
            'name': self.name,
            'passed': True,
            'errors': [],
            'warnings': [],
            'checks': {},
        }

    def run(self):
        locale_dir = self._find_locale_dir()
        locale_files = {}

        if locale_dir:
            locale_files = self._find_locale_files(locale_dir)
            if len(locale_files) >= 2:
                all_keys = {}
                for name, file_path in locale_files.items():
                    keys = self._extract_keys(file_path)
                    all_keys[name] = keys
                self._check_sync(all_keys)

        # 禁用概念掃描：不管有沒有 locale dir 都跑（也掃 data/ JSON）
        self._check_banned_concepts(locale_files)
        return self.result

    def _find_locale_dir(self):
        for d in self.LOCALE_DIRS:
            p = self.project_path / d
            if p.exists() and p.is_dir():
                return p
        return None

    def _find_locale_files(self, locale_dir):
        """找出所有 locale 檔案，回傳 {locale_name: path}"""
        files = {}
        for f in sorted(locale_dir.iterdir()):
            if f.suffix in ('.ts', '.tsx', '.js', '.json') and f.stem not in ('index', 'i18n', '__init__'):
                files[f.stem] = f
        return files

    def _extract_keys(self, file_path):
        """從 locale 檔案提取所有 key（支援 TS object 和 JSON）"""
        content = file_path.read_text(encoding='utf-8', errors='ignore')

        if file_path.suffix == '.json':
            try:
                data = json.loads(content)
                return self._flatten_keys(data)
            except json.JSONDecodeError:
                return set()

        # TypeScript/JavaScript: 用正則提取所有 key
        return self._extract_ts_keys(content)

    def _extract_ts_keys(self, content):
        """從 TS export default { ... } 提取所有 nested key"""
        keys = set()
        # 匹配 key: 'value' 或 key: { 或 key: `value` 或 key: value
        # 用縮排層級追蹤 nested path
        stack = []
        indent_stack = [0]

        for line in content.split('\n'):
            stripped = line.strip()
            if not stripped or stripped.startswith('//') or stripped.startswith('/*') or stripped.startswith('*'):
                continue

            # 計算縮排
            indent = len(line) - len(line.lstrip())

            # 關閉大括號：退出 nested level
            if stripped.startswith('}') or stripped == '},':
                if stack:
                    stack.pop()
                if indent_stack:
                    indent_stack.pop()
                continue

            # 匹配 key: value 或 key: {
            match = re.match(r"""^['"]?(\w+)['"]?\s*:\s*(.*)$""", stripped)
            if not match:
                continue

            key = match.group(1)
            value_part = match.group(2).strip()

            # 調整 stack 到正確層級
            while indent_stack and indent <= indent_stack[-1] and stack:
                stack.pop()
                indent_stack.pop()

            if value_part == '{' or value_part.endswith('{'):
                # 進入 nested object
                stack.append(key)
                indent_stack.append(indent)
            else:
                # 葉子節點
                full_key = '.'.join(stack + [key])
                keys.add(full_key)

        return keys

    def _flatten_keys(self, data, prefix=''):
        """將 JSON dict 攤平為 dot notation key 集合"""
        keys = set()
        if isinstance(data, dict):
            for k, v in data.items():
                full_key = f'{prefix}.{k}' if prefix else k
                if isinstance(v, dict):
                    keys.update(self._flatten_keys(v, full_key))
                else:
                    keys.add(full_key)
        return keys

    def _check_sync(self, all_keys):
        """比對所有 locale 的 key 差異"""
        locale_names = list(all_keys.keys())
        union_keys = set()
        for keys in all_keys.values():
            union_keys.update(keys)

        total_keys = len(union_keys)
        missing_report = {}

        for locale, keys in all_keys.items():
            missing = union_keys - keys
            if missing:
                # 只報告前 20 個，避免太長
                missing_sorted = sorted(missing)[:20]
                missing_report[locale] = {
                    'count': len(missing),
                    'sample': missing_sorted,
                }

        self.result['checks']['sync'] = {
            'locales': locale_names,
            'total_keys': total_keys,
            'per_locale': {name: len(keys) for name, keys in all_keys.items()},
            'missing': missing_report,
        }

        if missing_report:
            for locale, info in missing_report.items():
                count = info['count']
                sample = ', '.join(info['sample'][:5])
                self.result['warnings'].append(
                    f'{locale} 缺少 {count} 個 key（如 {sample}）'
                )

    def _check_banned_concepts(self, locale_files):
        """掃描 i18n 值中是否包含已移除概念（傍通曆、五行、暦注等）"""
        # 同時掃描 data/ 目錄下的 JSON
        scan_files = dict(locale_files)
        data_dir = self.project_path / 'data'
        if data_dir.exists():
            for f in data_dir.rglob('*.json'):
                scan_files[f'data/{f.name}'] = f

        hits = []
        for name, file_path in scan_files.items():
            try:
                content = file_path.read_text(encoding='utf-8', errors='ignore')
            except Exception:
                continue
            for term, reason in BANNED_CONCEPTS.items():
                # 逐行掃描，跳過註解行
                for lineno, line in enumerate(content.split('\n'), 1):
                    stripped = line.strip()
                    if stripped.startswith('//') or stripped.startswith('#') or stripped.startswith('*'):
                        continue
                    if term in line:
                        hits.append(f'{name}:{lineno} 含已移除概念「{term}」（{reason}）')

        if hits:
            self.result['passed'] = False
            for hit in hits[:10]:
                self.result['errors'].append(hit)
