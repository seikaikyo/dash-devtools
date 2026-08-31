"""掃描器覆蓋率回歸測試

驗證排除規則不會把真實原始碼靜默跳過：

1. 路徑中「含有」排除字串（distributor 含 dist、latest 含 test、inspector 含 spec）的檔案要被掃到
2. 專案根目錄名稱含排除字串時（例 latest-app）整個 repo 不能被跳過
3. 真正的排除目錄（node_modules/ dist/ tests/）仍要跳過
4. .gitignore 的規則要用 gitignore 語意比對，不能拿子字串誤殺原始碼

三個掃描進入點都要覆蓋：
- dash_devtools.hooks.pre_push.run_pre_push_check
- dash_devtools.validators.common.security.SecurityValidator
- dash_devtools.validators.security.SecurityValidator（legacy）
"""

import pytest

from dash_devtools.hooks.pre_push import run_pre_push_check
from dash_devtools.validators.common.security import SecurityValidator
from dash_devtools.validators.security import SecurityValidator as LegacySecurityValidator


# 佔位用假金鑰，刻意拆成兩段避免自家 pre-commit 掃描誤攔
FAKE_KEY = "sk-test-" + "FAKE-PLACEHOLDER-000000000000"
LEAK_LINE = f'const apiKey = "{FAKE_KEY}";\n'

# 路徑含排除字串、但其實是正常原始碼的檔案
SHOULD_SCAN = [
    "src/api/distributor.ts",   # 含 dist
    "src/lib/latest.ts",        # 含 test
    "src/utils/inspector.ts",   # 含 spec
    "src/rebuild_helper.ts",    # 含 build
    "src/logs_helper.ts",       # .gitignore 寫了 logs
]

# 真正該跳過的路徑
SHOULD_SKIP = [
    "node_modules/some-pkg/leak.js",
    "dist/bundle.js",
    "tests/fixtures/sample_secret.py",
    "build/generated.js",       # 同時被 .gitignore 的 build/ 命中
]


def _write(root, rel_path, content):
    target = root / rel_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return target


@pytest.fixture(autouse=True)
def _no_ggshield(monkeypatch):
    """確保走本地正則備援，不受環境中的 GitGuardian 設定影響"""
    monkeypatch.delenv("GITGUARDIAN_API_KEY", raising=False)


def _build_project(tmp_path, name="sample-app"):
    root = tmp_path / name
    root.mkdir()
    _write(root, ".gitignore", "node_modules/\nbuild/\nlogs\n*.log\n")
    for rel in SHOULD_SCAN + SHOULD_SKIP:
        _write(root, rel, LEAK_LINE)
    return root


def _pre_push_files(root):
    result = run_pre_push_check(str(root))
    return {issue["file"] for issue in result["issues"]}


def _validator_files(validator_cls, root):
    validator = validator_cls(str(root))
    validator.check_hardcoded_secrets()
    return {
        issue["file"]
        for issue in validator.result["checks"]["hardcoded_secrets"]["issues"]
    }


@pytest.mark.parametrize("rel_path", SHOULD_SCAN)
def test_pre_push_scans_paths_containing_ignore_words(tmp_path, rel_path):
    root = _build_project(tmp_path)
    assert rel_path in _pre_push_files(root)


@pytest.mark.parametrize("rel_path", SHOULD_SKIP)
def test_pre_push_still_skips_real_ignored_dirs(tmp_path, rel_path):
    root = _build_project(tmp_path)
    assert rel_path not in _pre_push_files(root)


def test_pre_push_fails_when_secret_present(tmp_path):
    root = _build_project(tmp_path)
    assert run_pre_push_check(str(root))["passed"] is False


def test_pre_push_passes_on_clean_project(tmp_path):
    root = tmp_path / "clean-app"
    root.mkdir()
    _write(root, "src/api/distributor.ts", "export const ok = 1;\n")
    assert run_pre_push_check(str(root))["passed"] is True


def test_pre_push_scans_project_whose_root_name_contains_ignore_word(tmp_path):
    """專案根目錄叫 latest-app（含 test）時不能整個 repo 跳過"""
    root = tmp_path / "latest-app"
    root.mkdir()
    _write(root, "src/main.ts", LEAK_LINE)
    assert "src/main.ts" in _pre_push_files(root)


@pytest.mark.parametrize(
    "validator_cls", [SecurityValidator, LegacySecurityValidator]
)
@pytest.mark.parametrize("rel_path", SHOULD_SCAN)
def test_validators_scan_paths_containing_ignore_words(tmp_path, validator_cls, rel_path):
    root = _build_project(tmp_path)
    assert rel_path in _validator_files(validator_cls, root)


@pytest.mark.parametrize(
    "validator_cls", [SecurityValidator, LegacySecurityValidator]
)
@pytest.mark.parametrize("rel_path", ["node_modules/some-pkg/leak.js", "dist/bundle.js",
                                      "tests/fixtures/sample_secret.py"])
def test_validators_still_skip_real_ignored_dirs(tmp_path, validator_cls, rel_path):
    root = _build_project(tmp_path)
    assert rel_path not in _validator_files(validator_cls, root)


@pytest.mark.parametrize(
    "validator_cls", [SecurityValidator, LegacySecurityValidator]
)
def test_validators_scan_project_whose_root_name_contains_ignore_word(tmp_path, validator_cls):
    root = tmp_path / "latest-app"
    root.mkdir()
    _write(root, "src/main.ts", LEAK_LINE)
    assert "src/main.ts" in _validator_files(validator_cls, root)


@pytest.mark.parametrize(
    "validator_cls", [SecurityValidator, LegacySecurityValidator]
)
def test_validators_report_untracked_env_file_in_ignore_word_root(tmp_path, validator_cls):
    """check_sensitive_files 也不能因為根目錄名稱含排除字串就跳過"""
    root = tmp_path / "latest-app"
    root.mkdir()
    _write(root, ".env", "DB_PASSWORD=placeholder\n")
    _write(root, ".gitignore", "node_modules/\n")

    validator = validator_cls(str(root))
    validator.check_sensitive_files()
    assert ".env" in validator.result["checks"]["sensitive_files"]["files"]


@pytest.mark.parametrize(
    "validator_cls", [SecurityValidator, LegacySecurityValidator]
)
def test_validators_skip_gitignored_env_file(tmp_path, validator_cls):
    root = tmp_path / "sample-app"
    root.mkdir()
    _write(root, ".env", "DB_PASSWORD=placeholder\n")
    _write(root, ".gitignore", ".env\nnode_modules/\n")

    validator = validator_cls(str(root))
    validator.check_sensitive_files()
    assert validator.result["checks"]["sensitive_files"]["files"] == []
