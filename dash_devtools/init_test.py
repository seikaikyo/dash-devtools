"""
測試框架初始化工具

自動為專案設定測試框架：
- Vite 專案 → Vitest
- Angular 專案 → Jest
- 加入範例測試
"""

import json
import subprocess
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm

console = Console()


# Vitest 設定模板
VITEST_CONFIG = '''import { defineConfig } from 'vitest/config'

export default defineConfig({
  test: {
    globals: true,
    environment: 'jsdom',
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html'],
      exclude: ['node_modules/', 'dist/']
    }
  }
})
'''

# 範例測試 (Vitest)
VITEST_EXAMPLE = '''import { describe, it, expect } from 'vitest'

describe('範例測試', () => {
  it('應該正確計算加法', () => {
    expect(1 + 1).toBe(2)
  })

  it('應該正確處理字串', () => {
    const name = '測試'
    expect(name).toContain('測')
  })
})
'''

# Jest 設定 (Angular)
JEST_CONFIG_ANGULAR = '''module.exports = {
  preset: 'jest-preset-angular',
  setupFilesAfterEnv: ['<rootDir>/setup-jest.ts'],
  testPathIgnorePatterns: ['<rootDir>/node_modules/', '<rootDir>/dist/'],
  coverageDirectory: 'coverage',
  collectCoverageFrom: [
    'src/**/*.ts',
    '!src/**/*.module.ts',
    '!src/main.ts',
    '!src/polyfills.ts'
  ]
};
'''

JEST_SETUP_ANGULAR = '''import 'jest-preset-angular/setup-jest';
'''

# Playwright 設定
PLAYWRIGHT_CONFIG = '''import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  timeout: 30000,
  expect: { timeout: 5000 },
  fullyParallel: true,
  retries: process.env.CI ? 2 : 0,
  reporter: 'html',
  use: {
    baseURL: 'http://localhost:5173',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure'
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
    { name: 'Mobile Safari', use: { ...devices['iPhone 12'] } }
  ],
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:5173',
    reuseExistingServer: !process.env.CI
  }
});
'''

PLAYWRIGHT_EXAMPLE = '''import { test, expect } from '@playwright/test';

test('首頁應該正確載入', async ({ page }) => {
  await page.goto('/');

  // 檢查標題
  await expect(page).toHaveTitle(/./);

  // 檢查主要內容區塊存在
  const main = page.locator('main, #app, .container');
  await expect(main).toBeVisible();
});

test('應該可以導航', async ({ page }) => {
  await page.goto('/');

  // 點擊連結並確認導航
  // await page.click('text=關於');
  // await expect(page).toHaveURL(/about/);
});
'''


def detect_project_type(project_path: Path) -> dict:
    """偵測專案類型"""
    package_json = project_path / 'package.json'

    if not package_json.exists():
        return {'type': 'unknown'}

    try:
        pkg = json.loads(package_json.read_text())
        deps = {**pkg.get('dependencies', {}), **pkg.get('devDependencies', {})}

        if '@angular/core' in deps:
            return {'type': 'angular', 'pkg': pkg}
        elif 'vite' in deps:
            return {'type': 'vite', 'pkg': pkg}
        elif 'react' in deps:
            return {'type': 'react', 'pkg': pkg}
        else:
            return {'type': 'vanilla', 'pkg': pkg}

    except Exception:
        return {'type': 'unknown'}


def init_vitest(project_path: Path, pkg: dict) -> dict:
    """初始化 Vitest"""
    results = {'success': True, 'steps': []}

    # 1. 安裝依賴
    console.print("[cyan]安裝 Vitest...[/cyan]")
    proc = subprocess.run(
        ['npm', 'install', '-D', 'vitest', '@vitest/coverage-v8', 'jsdom'],
        cwd=project_path,
        capture_output=True,
        text=True
    )
    if proc.returncode != 0:
        results['success'] = False
        results['error'] = proc.stderr
        return results
    results['steps'].append('安裝 vitest, @vitest/coverage-v8, jsdom')

    # 2. 建立設定檔
    config_path = project_path / 'vitest.config.ts'
    if not config_path.exists():
        config_path.write_text(VITEST_CONFIG)
        results['steps'].append('建立 vitest.config.ts')

    # 3. 建立測試目錄和範例
    tests_dir = project_path / 'tests'
    tests_dir.mkdir(exist_ok=True)

    example_path = tests_dir / 'example.test.ts'
    if not example_path.exists():
        example_path.write_text(VITEST_EXAMPLE)
        results['steps'].append('建立 tests/example.test.ts')

    # 4. 更新 package.json scripts
    package_json = project_path / 'package.json'
    pkg = json.loads(package_json.read_text())

    if 'scripts' not in pkg:
        pkg['scripts'] = {}

    pkg['scripts']['test'] = 'vitest'
    pkg['scripts']['test:run'] = 'vitest run'
    pkg['scripts']['test:coverage'] = 'vitest run --coverage'

    package_json.write_text(json.dumps(pkg, indent=2, ensure_ascii=False))
    results['steps'].append('更新 package.json scripts')

    return results


def init_jest_angular(project_path: Path, pkg: dict) -> dict:
    """初始化 Jest (Angular)"""
    results = {'success': True, 'steps': []}

    # 1. 安裝依賴
    console.print("[cyan]安裝 Jest for Angular...[/cyan]")
    proc = subprocess.run(
        ['npm', 'install', '-D', 'jest', 'jest-preset-angular', '@types/jest'],
        cwd=project_path,
        capture_output=True,
        text=True
    )
    if proc.returncode != 0:
        results['success'] = False
        results['error'] = proc.stderr
        return results
    results['steps'].append('安裝 jest, jest-preset-angular')

    # 2. 建立設定檔
    config_path = project_path / 'jest.config.js'
    if not config_path.exists():
        config_path.write_text(JEST_CONFIG_ANGULAR)
        results['steps'].append('建立 jest.config.js')

    setup_path = project_path / 'setup-jest.ts'
    if not setup_path.exists():
        setup_path.write_text(JEST_SETUP_ANGULAR)
        results['steps'].append('建立 setup-jest.ts')

    # 3. 更新 package.json
    package_json = project_path / 'package.json'
    pkg = json.loads(package_json.read_text())

    if 'scripts' not in pkg:
        pkg['scripts'] = {}

    pkg['scripts']['test'] = 'jest'
    pkg['scripts']['test:watch'] = 'jest --watch'
    pkg['scripts']['test:coverage'] = 'jest --coverage'

    package_json.write_text(json.dumps(pkg, indent=2, ensure_ascii=False))
    results['steps'].append('更新 package.json scripts')

    return results


def init_playwright(project_path: Path) -> dict:
    """初始化 Playwright E2E"""
    results = {'success': True, 'steps': []}

    # 1. 安裝依賴
    console.print("[cyan]安裝 Playwright...[/cyan]")
    proc = subprocess.run(
        ['npm', 'install', '-D', '@playwright/test'],
        cwd=project_path,
        capture_output=True,
        text=True
    )
    if proc.returncode != 0:
        results['success'] = False
        results['error'] = proc.stderr
        return results
    results['steps'].append('安裝 @playwright/test')

    # 安裝瀏覽器
    console.print("[cyan]安裝瀏覽器...[/cyan]")
    subprocess.run(
        ['npx', 'playwright', 'install', 'chromium'],
        cwd=project_path,
        capture_output=True
    )
    results['steps'].append('安裝 Chromium')

    # 2. 建立設定檔
    config_path = project_path / 'playwright.config.ts'
    if not config_path.exists():
        config_path.write_text(PLAYWRIGHT_CONFIG)
        results['steps'].append('建立 playwright.config.ts')

    # 3. 建立 e2e 目錄和範例
    e2e_dir = project_path / 'e2e'
    e2e_dir.mkdir(exist_ok=True)

    example_path = e2e_dir / 'home.spec.ts'
    if not example_path.exists():
        example_path.write_text(PLAYWRIGHT_EXAMPLE)
        results['steps'].append('建立 e2e/home.spec.ts')

    # 4. 更新 package.json
    package_json = project_path / 'package.json'
    pkg = json.loads(package_json.read_text())

    pkg['scripts']['e2e'] = 'playwright test'
    pkg['scripts']['e2e:ui'] = 'playwright test --ui'
    pkg['scripts']['e2e:report'] = 'playwright show-report'

    package_json.write_text(json.dumps(pkg, indent=2, ensure_ascii=False))
    results['steps'].append('更新 package.json scripts')

    return results


def run_init_test(project_path: str, include_e2e: bool = False) -> dict:
    """初始化測試框架"""
    project = Path(project_path)
    project_name = project.name

    # 偵測專案類型
    info = detect_project_type(project)

    console.print(Panel(
        f"[bold]{project_name}[/bold] 測試框架初始化",
        border_style="cyan"
    ))

    if info['type'] == 'unknown':
        console.print("[red]無法偵測專案類型 (缺少 package.json)[/red]")
        return {'success': False}

    console.print(f"[dim]專案類型:[/dim] {info['type']}")
    console.print()

    results = {'unit': None, 'e2e': None}

    # 單元測試
    if info['type'] == 'angular':
        console.print("[bold]設定 Jest (Angular)[/bold]")
        results['unit'] = init_jest_angular(project, info.get('pkg', {}))
    else:
        console.print("[bold]設定 Vitest[/bold]")
        results['unit'] = init_vitest(project, info.get('pkg', {}))

    if results['unit']['success']:
        for step in results['unit']['steps']:
            console.print(f"  [green]✓[/green] {step}")
    else:
        console.print(f"  [red]✗[/red] {results['unit'].get('error', '未知錯誤')}")

    # E2E 測試
    if include_e2e:
        console.print()
        console.print("[bold]設定 Playwright (E2E)[/bold]")
        results['e2e'] = init_playwright(project)

        if results['e2e']['success']:
            for step in results['e2e']['steps']:
                console.print(f"  [green]✓[/green] {step}")

    # 完成訊息
    console.print()
    console.print("[green]測試框架設定完成！[/green]")
    console.print()
    console.print("[dim]使用方式：[/dim]")
    console.print("  npm test          # 執行測試")
    console.print("  npm run test:coverage  # 產生覆蓋率報告")
    if include_e2e:
        console.print("  npm run e2e       # 執行 E2E 測試")
        console.print("  npm run e2e:ui    # 開啟 Playwright UI")

    return results
