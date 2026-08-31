"""scripts/ 底下腳本的強化回歸測試

- pre-push 不得使用固定可猜的暫存檔路徑，且結束時要清乾淨
- screenshot.js 預設要保留 Chrome sandbox
"""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / 'scripts'
PRE_PUSH = SCRIPTS_DIR / 'pre-push'
SCREENSHOT_JS = SCRIPTS_DIR / 'screenshot.js'


def test_pre_push_has_no_fixed_tmp_path():
    content = PRE_PUSH.read_text(encoding='utf-8')
    assert '/tmp/dash_hook_$$' not in content
    assert '/tmp/dash_commit_$$' not in content
    assert 'mktemp' in content
    assert 'trap ' in content
    # mktemp 會先建好空檔，判定必須改看內容
    assert '[ -s "$TMP_EMOJI" ]' in content
    assert '[ -s "$TMP_COMMIT" ]' in content


def test_pre_push_syntax():
    result = subprocess.run(['bash', '-n', str(PRE_PUSH)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


@pytest.mark.skipif(shutil.which('git') is None, reason='需要 git')
def test_pre_push_cleans_up_temp_files(tmp_path):
    """實跑 hook：暫存檔要落在 TMPDIR 且結束時被 trap 清掉"""
    repo = tmp_path / 'repo'
    repo.mkdir()
    env_base = {
        'PATH': os.environ['PATH'],
        'HOME': str(tmp_path / 'home'),
        'GIT_CONFIG_GLOBAL': str(tmp_path / 'gitconfig'),
        'GIT_CONFIG_SYSTEM': '/dev/null',
    }
    (tmp_path / 'home').mkdir()

    def git(*args):
        subprocess.run(['git', *args], cwd=repo, check=True,
                       capture_output=True, env=env_base)

    git('init', '-q')
    git('config', 'user.email', 'test@example.com')
    git('config', 'user.name', 'test')
    (repo / 'a.txt').write_text('hello\n', encoding='utf-8')
    git('add', 'a.txt')
    git('commit', '-qm', 'chore: first')
    (repo / 'b.txt').write_text('world\n', encoding='utf-8')
    git('add', 'b.txt')
    git('commit', '-qm', 'chore: second')

    # 假的 dash 指令，讓 hook 走完整流程
    bin_dir = tmp_path / 'bin'
    bin_dir.mkdir()
    stub = bin_dir / 'dash'
    stub.write_text('#!/bin/sh\nexit 0\n', encoding='utf-8')
    stub.chmod(0o755)

    tmpdir = tmp_path / 'tmp'
    tmpdir.mkdir()

    env = dict(env_base)
    env['PATH'] = f"{bin_dir}{os.pathsep}{os.environ['PATH']}"
    env['TMPDIR'] = str(tmpdir)

    result = subprocess.run(
        ['bash', str(PRE_PUSH)],
        cwd=repo, env=env, input='', capture_output=True, text=True, timeout=120
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert list(tmpdir.iterdir()) == [], '暫存檔沒有被清掉'
    assert not list(Path('/tmp').glob('dash_hook_*')), '仍在寫固定路徑暫存檔'
    assert not list(Path('/tmp').glob('dash_commit_*')), '仍在寫固定路徑暫存檔'


def test_screenshot_keeps_sandbox_by_default():
    content = SCREENSHOT_JS.read_text(encoding='utf-8')
    assert 'DASH_SCREENSHOT_NO_SANDBOX' in content
    # --no-sandbox 只能出現在顯式開啟的分支裡
    for line in content.splitlines():
        if '--no-sandbox' in line and not line.strip().startswith('*'):
            assert 'args.push' in line, f'sandbox 旗標不在環境變數分支內: {line}'
    assert "args: launchArgs()" in content


@pytest.mark.skipif(shutil.which('node') is None, reason='需要 node')
def test_screenshot_syntax():
    result = subprocess.run(['node', '--check', str(SCREENSHOT_JS)],
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
