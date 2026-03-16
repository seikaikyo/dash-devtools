"""
DashAI DevTools CLI 子指令模組

每個模組提供 register(main) 函數，將指令註冊到主 CLI group。
"""

from . import validate, health, spec, test, deploy, db, ai, hooks, misc
from . import analyze, generate, api_test


def register_all(main):
    """註冊所有子指令到主 CLI group"""
    validate.register(main)
    health.register(main)
    spec.register(main)
    test.register(main)
    deploy.register(main)
    db.register(main)
    ai.register(main)
    hooks.register(main)
    misc.register(main)
    analyze.register(main)
    generate.register(main)
    api_test.register(main)
