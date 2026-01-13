# DashAI DevTools v2.0

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)

**English** | **[日本語](README.ja.md)** | **[正體中文](README.md)**

Unified development toolkit - validation, testing, and AI-powered analysis tools.

## Features

- **E2E Testing**: Web automation using [agent-browser](https://github.com/vercel-labs/agent-browser) by Vercel Labs
- **AI Visual Analysis**: Screenshot + Gemini AI for UI/UX, accessibility, and performance analysis
- **Code Quality**: Automated security, standards, and technical debt checking
- **Test Suite**: Complete UIT/Smoke/E2E/UAT testing with Word/Markdown reports

## Installation

```bash
cd dash-devtools
pip install -e .

# For browser automation
npm install -g agent-browser
agent-browser install
```

## Command Overview

| Category | Command | Description |
|----------|---------|-------------|
| **Validate** | `dash validate` | Validate project against standards |
| **Health** | `dash health` | Project health score (Lighthouse-style) |
| **Stats** | `dash stats` | Code statistics dashboard |
| **Test** | `dash test` | Run tests (vitest/jest/pytest) |
| **Test Suite** | `dash test-suite` | Four test types (UIT/Smoke/E2E/UAT) + reports |
| **E2E** | `dash e2e` | E2E smoke testing (agent-browser) |
| **Report** | `dash report` | Generate HTML report |
| **Watch** | `dash watch` | Real-time monitoring |
| **Scan** | `dash scan` | Scan for sensitive data |
| **AI** | `dash ai` | AI code assistant (Gemini) |
| **Vision** | `dash vision` | AI visual analysis |
| **Database** | `dash db` | Database migration (Alembic) |
| **Diagram** | `dash dbdiagram` | Generate database ERD |
| **Doctor** | `dash doctor` | Diagnose dev environment |

## Quick Start

### Validate Project

```bash
# Smart validation (auto-detect project type)
dash validate /path/to/project

# Validate and auto-fix
dash validate /path/to/project --fix

# Validate all projects
dash validate --all
```

### E2E Smoke Testing

Using agent-browser for page error checking:

```bash
# Basic test
dash e2e https://your-app.vercel.app

# Check page load only
dash e2e https://example.com --check load

# Extended timeout
dash e2e https://example.com --timeout 60000

# Screenshot on failure
dash e2e https://example.com --screenshot

# Mobile test
dash e2e https://example.com --mobile

# JSON output
dash e2e https://example.com --json
```

### AI Visual Analysis

Screenshot + Gemini AI for UI/UX analysis:

```bash
# Basic visual analysis
dash vision https://example.com

# UI/UX expert analysis
dash vision https://example.com --type ui_ux

# Accessibility (WCAG 2.1) check
dash vision https://example.com --type accessibility

# Performance visual metrics
dash vision https://example.com --type performance

# Analyze local screenshot
dash vision /path/to/screenshot.png
```

Analysis types:

| Type | Description |
|------|-------------|
| `general` | Overall UI/UX evaluation |
| `ui_ux` | Professional UI/UX analysis |
| `accessibility` | WCAG 2.1 accessibility check |
| `performance` | Visual performance metrics |

### Browser Automation API

Python API for complete browser control:

```python
from dash_devtools.browser import AgentBrowser, quick_screenshot

# Quick screenshot
quick_screenshot("https://example.com", "/tmp/screenshot.png")

# Full control
browser = AgentBrowser()
browser.open("https://example.com")
browser.snapshot(interactive_only=True)  # Get interactive elements
browser.fill("@e1", "test@example.com")  # Fill form
browser.click("@e2")                      # Click button
browser.screenshot("/tmp/result.png")
browser.close()
```

Visual analysis API:

```python
from dash_devtools.vision import analyze_url, compare_screenshots

# Screenshot and analyze
result = analyze_url("https://example.com", analysis_type="ui_ux")
print(result.issues)
print(result.recommendations)

# Compare screenshots (visual regression)
result = compare_screenshots("before.png", "after.png")
print(result.analysis)
```

### Project Health Score

Lighthouse-style scoring:

```bash
# Single project
dash health .

# All projects
dash health --all

# JSON output
dash health . --json
```

Scoring categories:
- Security: Sensitive data, dependency vulnerabilities
- Quality: Code standards, file structure
- Maintainability: Technical debt, documentation completeness
- Performance: Bundle size, dependency count

### Test Suite

Run complete test suite and generate reports:

```bash
# Run all four test types
dash test-suite .

# Generate Word report
dash test-suite . --word test-report.docx

# Generate Markdown report
dash test-suite . --md test-report.md

# Run specific types only
dash test-suite . --types UIT,Smoke
```

| Test Type | Description | Test File |
|-----------|-------------|-----------|
| UIT | Unit tests | `*.spec.ts` |
| Smoke | Smoke tests | `e2e/smoke.spec.ts` |
| E2E | End-to-end tests | `e2e/mes-system.spec.ts` |
| UAT | Acceptance tests | `e2e/uat.spec.ts` |

### AI Code Assistant

Using Gemini 2.5 for code analysis:

```bash
# Analyze code
dash ai analyze src/main.py

# Security analysis
dash ai analyze src/api.ts --focus security

# Suggest fixes
dash ai fix src/main.py -e "TypeError: Cannot read property"

# Generate tests
dash ai test src/utils.py

# Explain code
dash ai explain src/complex-algo.py

# Review commit
dash ai review .
```

Requires: `export GEMINI_API_KEY="your-api-key"`

## Git Hooks

Install pre-push hook for automatic validation:

```bash
# Basic install
dash hooks install .

# Strict mode: test failures block push
dash hooks install . --strict

# Enable E2E smoke testing
dash hooks install . --e2e https://your-app.vercel.app
```

Pre-push automatically runs:
1. Emoji check
2. Sensitive data scan (GitGuardian or local rules)
3. Project standards validation
4. Tests (vitest/jest/pytest)
5. E2E smoke test (if configured)

## Claude Code Integration

### Skill Installation

```bash
mkdir -p ~/.claude/skills/agent-browser
curl -o ~/.claude/skills/agent-browser/SKILL.md \
  https://raw.githubusercontent.com/vercel-labs/agent-browser/main/skills/agent-browser/SKILL.md
```

Once installed, Claude Code will automatically use agent-browser for browser automation tasks.

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Format code
black .
```

## Acknowledgments

This project uses the following open-source tools:

- **[agent-browser](https://github.com/vercel-labs/agent-browser)** - Browser automation by Vercel Labs
- **[Playwright](https://playwright.dev/)** - E2E testing framework by Microsoft
- **[Google Gemini](https://ai.google.dev/)** - AI visual analysis engine
- **[Rich](https://github.com/Textualize/rich)** - Terminal UI beautification

## License

MIT License - DashAI
