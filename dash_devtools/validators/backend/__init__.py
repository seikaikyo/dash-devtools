"""
後端驗證器

支援：
- Node.js (Vercel Serverless, Express, NestJS)
- Python (FastAPI, Flask, Django, Streamlit)
"""

from .nodejs import NodejsValidator
from .python import PythonValidator

__all__ = ['NodejsValidator', 'PythonValidator']
