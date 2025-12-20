"""
dbdiagram.io 整合工具

自動產生資料庫圖表連結，供外包廠商查看。

支援：
- Prisma schema → DBML → dbdiagram.io 連結
- DBML 檔案直接轉換
"""

import base64
import urllib.parse
from pathlib import Path
import subprocess


def encode_dbml_to_link(dbml_content: str) -> str:
    """將 DBML 編碼為 dbdiagram.io 分享連結

    編碼步驟：
    1. UTF-8 編碼
    2. Base64 轉換
    3. URL 編碼

    Args:
        dbml_content: DBML 文字內容

    Returns:
        dbdiagram.io 分享連結
    """
    # 移除自動產生的註解（節省 URL 長度）
    clean_dbml = '\n'.join(
        line for line in dbml_content.split('\n')
        if not line.startswith('////')
    ).strip()

    # UTF-8 → Base64 → URL encode
    base64_bytes = base64.b64encode(clean_dbml.encode('utf-8'))
    encoded = urllib.parse.quote(base64_bytes.decode('ascii'))

    return f'https://dbdiagram.io/d?c={encoded}'


def find_prisma_schema(project_path: str) -> Path | None:
    """尋找專案中的 Prisma schema 檔案"""
    project = Path(project_path)

    # 常見位置
    possible_paths = [
        project / 'prisma' / 'schema.prisma',
        project / 'schema.prisma',
    ]

    for path in possible_paths:
        if path.exists():
            return path

    return None


def find_dbml_file(project_path: str) -> Path | None:
    """尋找專案中的 DBML 檔案"""
    project = Path(project_path)

    # 常見位置
    possible_paths = [
        project / 'docs' / 'schema.dbml',
        project / 'prisma' / 'dbml' / 'schema.dbml',
        project / 'schema.dbml',
    ]

    for path in possible_paths:
        if path.exists():
            return path

    return None


def generate_dbml_from_prisma(project_path: str) -> dict:
    """從 Prisma schema 產生 DBML

    需要先安裝 prisma-dbml-generator：
    npm install -D prisma-dbml-generator

    並在 schema.prisma 加入：
    generator dbml {
      provider   = "prisma-dbml-generator"
      output     = "../docs"
      outputName = "schema.dbml"
    }

    Returns:
        {'success': bool, 'dbml_path': str, 'error': str}
    """
    project = Path(project_path)
    schema_path = find_prisma_schema(project_path)

    if not schema_path:
        return {'success': False, 'error': '找不到 schema.prisma'}

    # 檢查是否有 generator dbml
    schema_content = schema_path.read_text()
    if 'prisma-dbml-generator' not in schema_content:
        return {
            'success': False,
            'error': '請在 schema.prisma 加入 generator dbml { provider = "prisma-dbml-generator" }'
        }

    # 執行 prisma generate
    try:
        result = subprocess.run(
            ['npx', 'prisma', 'generate'],
            cwd=project,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            return {'success': False, 'error': result.stderr}

        # 尋找產生的 DBML 檔案
        dbml_path = find_dbml_file(project_path)
        if dbml_path:
            return {'success': True, 'dbml_path': str(dbml_path)}
        else:
            return {'success': False, 'error': '產生失敗，找不到 DBML 檔案'}

    except FileNotFoundError:
        return {'success': False, 'error': '找不到 npx，請確認已安裝 Node.js'}


def generate_dbdiagram_link(project_path: str) -> dict:
    """產生 dbdiagram.io 連結

    流程：
    1. 尋找現有的 DBML 檔案
    2. 若無，嘗試從 Prisma schema 產生
    3. 編碼為 dbdiagram.io 連結

    Returns:
        {
            'success': bool,
            'link': str,
            'embed_link': str,
            'source': str,  # 'dbml' or 'prisma'
            'error': str
        }
    """
    # 尋找現有的 DBML
    dbml_path = find_dbml_file(project_path)

    if not dbml_path:
        # 嘗試從 Prisma 產生
        gen_result = generate_dbml_from_prisma(project_path)
        if not gen_result['success']:
            return {'success': False, 'error': gen_result['error']}
        dbml_path = Path(gen_result['dbml_path'])

    # 讀取 DBML
    try:
        dbml_content = dbml_path.read_text()
    except Exception as e:
        return {'success': False, 'error': f'讀取 DBML 失敗: {e}'}

    # 編碼為連結
    link = encode_dbml_to_link(dbml_content)
    embed_link = link.replace('/d?', '/embed?')

    return {
        'success': True,
        'link': link,
        'embed_link': embed_link,
        'source': 'dbml',
        'dbml_path': str(dbml_path)
    }


def save_link_to_file(project_path: str, link: str) -> str:
    """儲存連結到檔案"""
    output_path = Path(project_path) / 'docs' / 'dbdiagram-link.txt'
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(link)
    return str(output_path)
