"""路徑排除比對單元測試"""

from pathlib import Path

import pytest

from dash_devtools.path_filters import (
    is_gitignored,
    is_in_ignored_dir,
    parse_gitignore,
    to_relative_parts,
)


IGNORE_DIRS = ['node_modules', '.git', 'dist', 'build', 'venv', 'coverage',
               'tests', '__tests__', 'test', 'spec']


@pytest.mark.parametrize("rel_path", [
    "src/api/distributor.ts",   # 含 dist
    "src/lib/latest.ts",        # 含 test
    "src/utils/inspector.ts",   # 含 spec
    "src/rebuild_helper.ts",    # 含 build
    "src/coverage_report.ts",   # 含 coverage
    "src/prevented/index.ts",   # 含 vent
])
def test_ignore_dirs_do_not_match_substrings(rel_path):
    project = Path("/repo")
    assert is_in_ignored_dir(project / rel_path, project, IGNORE_DIRS) is False


@pytest.mark.parametrize("rel_path", [
    "node_modules/pkg/index.js",
    "dist/bundle.js",
    "tests/fixtures/sample.py",
    "src/__tests__/a.spec.ts",
    "packages/app/dist/main.js",
])
def test_ignore_dirs_match_real_directories(rel_path):
    project = Path("/repo")
    assert is_in_ignored_dir(project / rel_path, project, IGNORE_DIRS) is True


def test_ignore_dirs_ignore_project_root_name():
    """專案根目錄叫 latest-app（含 test）不能讓整個 repo 被跳過"""
    project = Path("/home/dash/github/latest-app")
    assert is_in_ignored_dir(project / "src/main.ts", project, IGNORE_DIRS) is False


def test_ignore_dirs_do_not_match_file_name():
    project = Path("/repo")
    assert is_in_ignored_dir(project / "src/dist", project, IGNORE_DIRS) is False


def test_to_relative_parts_outside_project():
    parts = to_relative_parts(Path("/other/src/a.ts"), Path("/repo"))
    assert parts[-1] == "a.ts"


def test_parse_gitignore(tmp_path):
    (tmp_path / ".gitignore").write_text("# comment\n\nnode_modules/\n*.log\n", encoding="utf-8")
    assert parse_gitignore(tmp_path) == ["node_modules/", "*.log"]


def test_parse_gitignore_missing_file(tmp_path):
    assert parse_gitignore(tmp_path) == []


@pytest.mark.parametrize("rel_path,patterns,expected", [
    # 子字串不再誤殺
    ("src/logs_helper.ts", ["logs"], False),
    ("src/library/index.ts", ["lib"], False),
    ("src/environment.ts", ["env/"], False),
    ("src/outbound.ts", ["out"], False),
    # 正常的目錄與檔名比對
    ("logs/app.ts", ["logs"], True),
    ("src/lib/index.ts", ["lib"], True),
    ("build/generated.js", ["build/"], True),
    ("src/build.ts", ["build/"], False),
    ("a/b/debug.log", ["*.log"], True),
    ("a/b/debug.txt", ["*.log"], False),
    (".env", [".env"], True),
    ("src/.env", [".env"], True),
    # 錨定規則
    ("env/settings.py", ["/env"], True),
    ("src/env/settings.py", ["/env"], False),
    ("src/generated/api.ts", ["src/generated/"], True),
    ("lib/src/generated/api.ts", ["src/generated/"], False),
    # 反向規則後者覆蓋前者
    ("keep.log", ["*.log", "!keep.log"], False),
    ("drop.log", ["*.log", "!keep.log"], True),
])
def test_is_gitignored(rel_path, patterns, expected):
    assert is_gitignored(rel_path, patterns) is expected


def test_is_gitignored_empty_patterns():
    assert is_gitignored("src/a.ts", []) is False
