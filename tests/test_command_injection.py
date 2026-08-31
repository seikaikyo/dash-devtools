"""外部指令呼叫的注入回歸測試

- Lighthouse 腳本不得把 url / categories 拼進交給 shell 的字串
- 截圖腳本不得把 url / 輸出路徑插值進 JS 字面量
"""

import shutil
import subprocess
import sys

import pytest

from dash_devtools import word_report
from dash_devtools.perf import LIGHTHOUSE_SCRIPT, run_perf_test


MALICIOUS_URL = 'https://example.com/"; touch /tmp/dash_pwned; #'


def _node_check(tmp_path, script, name):
    script_file = tmp_path / name
    script_file.write_text(script, encoding='utf-8')
    return subprocess.run(
        ['node', '--check', str(script_file)],
        capture_output=True, text=True
    )


def test_lighthouse_script_does_not_use_shell():
    assert 'execFileSync' in LIGHTHOUSE_SCRIPT
    assert 'execSync(' not in LIGHTHOUSE_SCRIPT.replace('execFileSync(', '')
    # 不得有把值拼進指令字串的 template literal
    assert '`npx' not in LIGHTHOUSE_SCRIPT
    assert '${url}' not in LIGHTHOUSE_SCRIPT


@pytest.mark.skipif(shutil.which('node') is None, reason='需要 node')
def test_lighthouse_script_is_valid_js(tmp_path):
    result = _node_check(tmp_path, LIGHTHOUSE_SCRIPT, 'lighthouse.js')
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("bad_url", [
    'file:///etc/passwd',
    '$(touch /tmp/dash_pwned)',
    '-–print-config',
    'javascript:alert(1)',
])
def test_run_perf_test_rejects_non_http_url(monkeypatch, bad_url):
    def _boom(*args, **kwargs):
        raise AssertionError(f'不該執行外部指令: {args}')

    monkeypatch.setattr(subprocess, 'run', _boom)

    result = run_perf_test(bad_url)
    assert result['success'] is False
    assert 'Invalid URL' in result['error']


def test_screenshot_script_passes_values_as_argv(tmp_path, monkeypatch):
    """url 與輸出路徑必須是獨立的 argv 元素，不能出現在腳本內容裡"""
    project = tmp_path / 'app'
    (project / 'node_modules' / 'puppeteer').mkdir(parents=True)

    captured = {}

    class _Result:
        returncode = 0

    def _fake_run(cmd, **kwargs):
        captured['cmd'] = cmd
        return _Result()

    monkeypatch.setattr(subprocess, 'run', _fake_run)

    word_report.take_screenshots(str(project), urls=[MALICIOUS_URL])

    cmd = captured['cmd']
    assert cmd[0] == 'node'
    assert cmd[1] == '-e'
    script = cmd[2]
    assert MALICIOUS_URL not in script
    assert cmd[3] == MALICIOUS_URL
    assert cmd[4].endswith('screenshot-1.png')
    assert 'process.argv' in script


@pytest.mark.skipif(shutil.which('node') is None, reason='需要 node')
def test_screenshot_script_is_valid_js(tmp_path, monkeypatch):
    project = tmp_path / 'app'
    (project / 'node_modules' / 'puppeteer').mkdir(parents=True)

    captured = {}

    class _Result:
        returncode = 0

    def _fake_run(cmd, **kwargs):
        captured['cmd'] = cmd
        return _Result()

    monkeypatch.setattr(subprocess, 'run', _fake_run)
    word_report.take_screenshots(str(project), urls=['https://example.com'])

    result = _node_check(tmp_path, captured['cmd'][2], 'screenshot.js')
    assert result.returncode == 0, result.stderr


@pytest.mark.skipif(shutil.which('node') is None, reason='需要 node')
def test_node_dash_e_argv_offsets():
    """確認 node -e 的額外參數落在 process.argv[1] 與 [2]"""
    result = subprocess.run(
        [shutil.which('node'), '-e',
         'console.log(JSON.stringify([process.argv[1], process.argv[2]]))',
         'URL', 'PATH'],
        capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
    assert '"URL"' in result.stdout and '"PATH"' in result.stdout


@pytest.mark.skipif(sys.platform == 'win32', reason='POSIX only')
def test_no_pwn_side_effect():
    """上面的注入字串不得真的建立檔案"""
    from pathlib import Path
    assert not Path('/tmp/dash_pwned').exists()
