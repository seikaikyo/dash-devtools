"""
OpenSpec 規格驗證器

檢查內容：
1. openspec/ 目錄存在性
2. 規格檔案格式正確 (YAML frontmatter)
3. 無孤立的提案（超過 7 天未處理）
4. specs/ 與 changes/ 一致性
"""

import re
import time
from pathlib import Path


class SpecValidator:
    """OpenSpec 規格驗證器"""

    name = 'spec'

    # 忽略目錄
    IGNORE_DIRS = [
        'node_modules', '.git', 'dist', 'build', '__pycache__', 'venv'
    ]

    # 規格檔案必要欄位
    REQUIRED_FRONTMATTER = ['title', 'status']

    # 變更檔案必要欄位
    REQUIRED_CHANGE_FIELDS = ['title', 'type']

    def __init__(self, project_path):
        self.project_path = Path(project_path)
        self.project_name = self.project_path.name
        self.openspec_dir = self.project_path / 'openspec'
        self.result = {
            'name': self.name,
            'passed': True,
            'errors': [],
            'warnings': [],
            'checks': {}
        }

    def run(self):
        """執行所有驗證"""
        if not self.project_path.exists():
            self.result['passed'] = False
            self.result['errors'].append(f'專案路徑不存在: {self.project_path}')
            return self.result

        # 如果沒有 openspec 目錄，跳過驗證
        if not self.openspec_dir.exists():
            self.result['checks']['initialized'] = {'exists': False}
            return self.result

        self.check_directory_structure()
        self.check_specs_format()
        self.check_changes_format()
        self.check_stale_changes()
        self.check_consistency()

        return self.result

    def check_directory_structure(self):
        """檢查目錄結構"""
        specs_dir = self.openspec_dir / 'specs'
        changes_dir = self.openspec_dir / 'changes'

        structure = {
            'openspec_exists': self.openspec_dir.exists(),
            'specs_exists': specs_dir.exists(),
            'changes_exists': changes_dir.exists(),
        }

        self.result['checks']['directory_structure'] = structure

        # 目錄存在但子目錄缺失是警告
        if self.openspec_dir.exists():
            if not specs_dir.exists():
                self.result['warnings'].append('openspec/specs/ 目錄不存在')
            if not changes_dir.exists():
                self.result['warnings'].append('openspec/changes/ 目錄不存在')

    def check_specs_format(self):
        """檢查規格檔案格式"""
        specs_dir = self.openspec_dir / 'specs'
        if not specs_dir.exists():
            return

        issues = []
        valid_count = 0

        for spec_file in specs_dir.glob('*.md'):
            try:
                content = spec_file.read_text(encoding='utf-8')
                frontmatter = self._parse_frontmatter(content)

                if frontmatter is None:
                    issues.append({
                        'file': spec_file.name,
                        'error': '缺少 YAML frontmatter'
                    })
                    continue

                # 檢查必要欄位
                missing = [f for f in self.REQUIRED_FRONTMATTER if f not in frontmatter]
                if missing:
                    issues.append({
                        'file': spec_file.name,
                        'error': f'缺少欄位: {", ".join(missing)}'
                    })
                else:
                    valid_count += 1

            except Exception as e:
                issues.append({
                    'file': spec_file.name,
                    'error': str(e)
                })

        self.result['checks']['specs_format'] = {
            'valid_count': valid_count,
            'issues': issues
        }

        for issue in issues:
            self.result['warnings'].append(
                f"規格格式問題: {issue['file']} - {issue['error']}"
            )

    def check_changes_format(self):
        """檢查變更檔案格式"""
        changes_dir = self.openspec_dir / 'changes'
        if not changes_dir.exists():
            return

        issues = []
        valid_count = 0

        for change_file in changes_dir.glob('*.md'):
            try:
                content = change_file.read_text(encoding='utf-8')
                frontmatter = self._parse_frontmatter(content)

                if frontmatter is None:
                    issues.append({
                        'file': change_file.name,
                        'error': '缺少 YAML frontmatter'
                    })
                    continue

                # 檢查必要欄位
                missing = [f for f in self.REQUIRED_CHANGE_FIELDS if f not in frontmatter]
                if missing:
                    issues.append({
                        'file': change_file.name,
                        'error': f'缺少欄位: {", ".join(missing)}'
                    })
                else:
                    valid_count += 1

            except Exception as e:
                issues.append({
                    'file': change_file.name,
                    'error': str(e)
                })

        self.result['checks']['changes_format'] = {
            'valid_count': valid_count,
            'issues': issues
        }

        for issue in issues:
            self.result['warnings'].append(
                f"變更格式問題: {issue['file']} - {issue['error']}"
            )

    def check_stale_changes(self):
        """檢查過期的變更提案（超過 7 天未處理）"""
        changes_dir = self.openspec_dir / 'changes'
        if not changes_dir.exists():
            return

        stale = []
        now = time.time()
        seven_days = 7 * 24 * 60 * 60

        for change_file in changes_dir.glob('*.md'):
            mtime = change_file.stat().st_mtime
            age_days = (now - mtime) / (24 * 60 * 60)

            if now - mtime > seven_days:
                stale.append({
                    'file': change_file.stem,
                    'age_days': int(age_days)
                })

        self.result['checks']['stale_changes'] = {
            'count': len(stale),
            'changes': stale
        }

        for change in stale:
            self.result['warnings'].append(
                f"過期變更: {change['file']} (已 {change['age_days']} 天未處理)"
            )

    def check_consistency(self):
        """檢查 specs 與 changes 的一致性"""
        specs_dir = self.openspec_dir / 'specs'
        changes_dir = self.openspec_dir / 'changes'

        if not specs_dir.exists() or not changes_dir.exists():
            return

        # 收集 specs 中參照的變更
        referenced_changes = set()
        for spec_file in specs_dir.glob('*.md'):
            try:
                content = spec_file.read_text(encoding='utf-8')
                # 簡單解析 changes 參照 (格式: [[change-name]])
                refs = re.findall(r'\[\[([^\]]+)\]\]', content)
                referenced_changes.update(refs)
            except Exception:
                pass

        existing_changes = {f.stem for f in changes_dir.glob('*.md')}

        # specs 內完全沒有 [[]] 引用 → 視為 flat 結構，跳過 orphan check
        # opt-in 機制：repo 加入第一個 [[ref]] 即自動啟動階層模式
        if not referenced_changes:
            self.result['checks']['consistency'] = {
                'specs_count': len(list(specs_dir.glob('*.md'))),
                'changes_count': len(existing_changes),
                'orphan_changes': [],
                'note': 'flat structure detected (specs 內無 [[]] 引用)，略過 orphan check'
            }
            return

        # 找出孤立的變更（在 changes/ 但沒被任何 spec 參照）
        orphan_changes = existing_changes - referenced_changes

        self.result['checks']['consistency'] = {
            'specs_count': len(list(specs_dir.glob('*.md'))),
            'changes_count': len(existing_changes),
            'orphan_changes': list(orphan_changes)
        }

        # 孤立變更只是警告，不是錯誤
        if orphan_changes:
            for change in orphan_changes:
                self.result['warnings'].append(
                    f"孤立變更: {change} (未被任何規格參照)"
                )

    def _parse_frontmatter(self, content: str) -> dict | None:
        """解析 YAML frontmatter

        Args:
            content: Markdown 檔案內容

        Returns:
            dict: frontmatter 資料，如果沒有則回傳 None
        """
        # 檢查是否以 --- 開頭
        if not content.startswith('---'):
            return None

        # 找到結束的 ---
        end_match = re.search(r'\n---\n', content)
        if not end_match:
            return None

        frontmatter_text = content[3:end_match.start()]

        # 簡單解析 YAML (只處理 key: value 格式)
        result = {}
        for line in frontmatter_text.strip().split('\n'):
            if ':' in line:
                key, value = line.split(':', 1)
                result[key.strip()] = value.strip().strip('"\'')

        return result if result else None
