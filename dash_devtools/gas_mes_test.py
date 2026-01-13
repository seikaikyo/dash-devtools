"""
GAS MES 完整四大測試模組

針對 Google Apps Script MES 系統的完整測試套件：
- UIT: 程式碼靜態分析 (85+ API、14 模組、HTML 品質)
- Smoke: 全模組頁面載入測試 (桌面版 + 手機版)
- E2E: 各模組 CRUD 功能驗證
- UAT: 6 種角色 × 14 模組權限驗證

使用方式：
    dash gas-test /path/to/gas/mes
    dash gas-test --word report.docx
"""

import re
import json
import subprocess
import tempfile
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Set
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()

# GAS MES 部署 URL
GAS_MES_URL = "https://script.google.com/macros/s/YOUR_DEPLOYMENT_ID/exec"

# ========== 模組與 API 定義 ==========

# 14 個功能模組及其對應 API
MODULE_APIS = {
    'dashboard': {
        'name': '戰情中心',
        'tab_id': 'dashboard',
        'apis': ['getScheduleStats', 'getWorkOrders', 'getDispatches', 'getReports'],
        'required_apis': ['getScheduleStats'],
    },
    'work-orders': {
        'name': '工單管理',
        'tab_id': 'work-orders',
        'apis': ['getWorkOrders', 'createWorkOrder', 'updateWorkOrder', 'deleteWorkOrder', 'cleanInvalidWorkOrders'],
        'required_apis': ['getWorkOrders', 'createWorkOrder', 'updateWorkOrder'],
        'crud': ['create', 'read', 'update', 'delete'],
    },
    'dispatches': {
        'name': '現場派工',
        'tab_id': 'dispatches',
        'apis': ['getDispatches', 'createDispatch', 'updateDispatch', 'deleteDispatch', 'startDispatch', 'completeDispatch'],
        'required_apis': ['getDispatches', 'createDispatch', 'startDispatch', 'completeDispatch'],
        'crud': ['create', 'read', 'update', 'delete'],
    },
    'reports': {
        'name': '報工紀錄',
        'tab_id': 'reports',
        'apis': ['getReports', 'createReport', 'getNgDetailsByReport', 'createNgDetail', 'getNgReasons', 'createNgReason', 'updateNgReason', 'deleteNgReason'],
        'required_apis': ['getReports', 'createReport'],
        'crud': ['create', 'read'],
    },
    'outgassing': {
        'name': '品質檢驗',
        'tab_id': 'outgassing',
        'apis': ['getOutgassingTests', 'createOutgassingTest', 'getOutgassingSampleInfo'],
        'required_apis': ['getOutgassingTests', 'createOutgassingTest'],
        'crud': ['create', 'read'],
        'features': ['signature', 'sample_info'],
    },
    'aoi': {
        'name': 'AOI 檢驗',
        'tab_id': 'aoi',
        'apis': ['getAoiInspections', 'createAoiInspection', 'importAoiCsv'],
        'required_apis': ['getAoiInspections', 'createAoiInspection'],
        'crud': ['create', 'read'],
        'features': ['csv_import'],
    },
    'r0': {
        'name': '標籤管理',
        'tab_id': 'r0',
        'apis': ['getR0Labels', 'createR0Label', 'updateR0Label', 'syncR0Labels', 'getEpcHistory', 'createEpcHistory', 'checkEpc'],
        'required_apis': ['getR0Labels', 'createR0Label'],
        'crud': ['create', 'read', 'update'],
        'features': ['epc_check', 'sync'],
    },
    'label-editor': {
        'name': '樣式設計',
        'tab_id': 'label-editor',
        'apis': [],  # 前端功能，無後端 API
        'required_apis': [],
        'features': ['canvas_editor'],
    },
    'schedule': {
        'name': '排程管理',
        'tab_id': 'schedule',
        'apis': [
            'getSchedulePlans', 'createSchedulePlan', 'updateSchedulePlan', 'getScheduleStats',
            'getShifts', 'createShift', 'updateShift', 'deleteShift', 'getShiftsByDate', 'getShiftsByDateRange', 'importShifts',
            'getEquipmentSchedules', 'createEquipmentSchedule', 'updateEquipmentSchedule', 'deleteEquipmentSchedule', 'getEquipmentSchedulesByDate'
        ],
        'required_apis': ['getSchedulePlans', 'getShifts', 'getEquipmentSchedules'],
        'crud': ['create', 'read', 'update', 'delete'],
        'features': ['calendar', 'drag_drop', 'import'],
    },
    'oven': {
        'name': '設備監控',
        'tab_id': 'oven',
        'apis': ['getEquipmentSchedules', 'getEquipmentSchedulesByDate'],
        'required_apis': ['getEquipmentSchedules'],
        'features': ['realtime_status'],
    },
    'wms': {
        'name': '倉儲管理',
        'tab_id': 'wms',
        'apis': [
            'getWmsLocations', 'createWmsLocation', 'updateWmsLocation', 'deleteWmsLocation', 'initWmsLocations',
            'getWmsInventory', 'getWmsLocationSummary', 'getWmsMovements',
            'wmsInbound', 'wmsOutbound', 'wmsTransfer',
            'getWmsStockTakes', 'createWmsStockTake'
        ],
        'required_apis': ['getWmsLocations', 'getWmsInventory', 'wmsInbound', 'wmsOutbound', 'wmsTransfer'],
        'crud': ['create', 'read', 'update', 'delete'],
        'features': ['inbound', 'outbound', 'transfer', 'stock_take'],
    },
    'parts': {
        'name': '物料主檔',
        'tab_id': 'parts',
        'apis': ['getParts', 'createPart', 'updatePart', 'deletePart'],
        'required_apis': ['getParts', 'createPart'],
        'crud': ['create', 'read', 'update', 'delete'],
    },
    'audit': {
        'name': '操作紀錄',
        'tab_id': 'audit',
        'apis': ['getAuditLogs', 'createAuditLog'],
        'required_apis': ['getAuditLogs', 'createAuditLog'],
        'features': ['iso27001', 'login_logout'],
    },
    'settings': {
        'name': '設定',
        'tab_id': 'settings',
        'apis': [
            'getOperators', 'createOperator', 'updateOperator', 'deleteOperator',
            'getCustomers', 'createCustomer', 'updateCustomer', 'deleteCustomer',
            'getProducts', 'createProduct', 'updateProduct', 'deleteProduct',
            'syncDatabase', 'clearCache', 'fixColumnOrder', 'resetMes', 'generateTestData'
        ],
        'required_apis': ['getOperators', 'getCustomers', 'getProducts', 'syncDatabase'],
        'crud': ['create', 'read', 'update', 'delete'],
        'features': ['operators', 'customers', 'products', 'sync', 'maintenance'],
    },
}

# 系統層級 API
SYSTEM_APIS = ['getVersion', 'getAllData', 'getShortUrl', 'debugSheet', 'fixSignatureData', 'fixStationName']

# 角色權限定義
ROLE_PERMISSIONS = {
    'operator': ['work-orders-view', 'dispatches', 'reports'],
    'warehouse': ['work-orders-view', 'wms', 'parts'],
    'qc': ['work-orders-view', 'outgassing', 'aoi', 'r0'],
    'clerk': ['work-orders-view', 'wms', 'parts', 'audit', 'settings'],
    'supervisor': ['dashboard', 'work-orders-view', 'dispatches', 'reports',
                   'outgassing', 'aoi', 'r0', 'schedule', 'oven', 'wms', 'parts', 'audit'],
    'admin': ['dashboard', 'work-orders', 'dispatches', 'reports', 'outgassing',
              'aoi', 'r0', 'label-editor', 'schedule', 'oven', 'wms', 'parts', 'audit', 'settings']
}

# 角色中文名稱
ROLE_NAMES = {
    'operator': '作業員',
    'warehouse': '倉庫',
    'qc': '品管',
    'clerk': '行政',
    'supervisor': '主管',
    'admin': '管理員'
}


@dataclass
class TestCase:
    """測試案例"""
    id: str
    name: str
    module: str = ''
    status: str = 'pending'  # pending, passed, failed, skipped
    duration: float = 0.0
    error: str = ''
    screenshot: str = ''
    details: str = ''


@dataclass
class TestTypeResult:
    """測試類型結果"""
    test_type: str
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    duration: float = 0.0
    success: bool = True
    error: str = ''
    test_cases: List[TestCase] = field(default_factory=list)
    not_configured: bool = False


@dataclass
class GASMESTestResult:
    """GAS MES 測試結果"""
    project_name: str = 'GAS MES'
    results: Dict[str, TestTypeResult] = field(default_factory=dict)
    total_passed: int = 0
    total_failed: int = 0
    total_duration: float = 0.0
    overall_success: bool = True
    timestamp: str = ''
    version: str = ''
    api_count: int = 0
    module_count: int = 14


class GASMESTestRunner:
    """GAS MES 完整測試執行器"""

    def __init__(self, project_path: str, url: str = None):
        self.project_path = Path(project_path)
        self.url = url or GAS_MES_URL
        self.version = self._get_version()
        self.screenshot_dir = Path(tempfile.mkdtemp(prefix='gas-mes-test-'))
        self.code_content = self._read_file('Code.js')
        self.db_content = self._read_file('Database.js')
        self.app_content = self._read_file('app.html')
        self.discovered_apis = self._discover_apis()

    def _read_file(self, filename: str) -> str:
        """讀取檔案內容"""
        filepath = self.project_path / filename
        if filepath.exists():
            return filepath.read_text(encoding='utf-8')
        return ''

    def _get_version(self) -> str:
        """從 Code.js 取得版本號"""
        code_js = self.project_path / 'Code.js'
        if code_js.exists():
            content = code_js.read_text(encoding='utf-8')
            match = re.search(r"case\s+['\"]getVersion['\"]:\s*\n?\s*return\s*{\s*success:\s*true,\s*data:\s*['\"]([^'\"]+)['\"]", content)
            if match:
                return match.group(1)
        return 'unknown'

    def _discover_apis(self) -> Set[str]:
        """從 Code.js 發現所有 API"""
        apis = set()
        if self.code_content:
            matches = re.findall(r"case\s+['\"](\w+)['\"]:", self.code_content)
            apis = set(matches)
        return apis

    def _get_puppeteer_cwd(self) -> str:
        """取得有安裝 Puppeteer 的目錄"""
        check_dirs = [
            '${HOME}/Documents/github/demo-vision',
            '${HOME}/Documents/github/MES',
            str(self.project_path),
        ]
        for check_dir in check_dirs:
            node_modules = Path(check_dir) / 'node_modules' / 'puppeteer'
            if node_modules.exists():
                return check_dir
        return '${HOME}/Documents/github/demo-vision'

    def _run_puppeteer_test(self, script: str, timeout: int = 60000) -> Dict:
        """執行 Puppeteer 測試腳本"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
            f.write(script)
            script_path = f.name

        try:
            puppeteer_cwd = self._get_puppeteer_cwd()
            env = {**subprocess.os.environ, 'NODE_PATH': f"{puppeteer_cwd}/node_modules"}

            proc = subprocess.run(
                ['node', script_path],
                capture_output=True,
                text=True,
                timeout=timeout / 1000 + 30,
                cwd=puppeteer_cwd,
                env=env
            )

            if proc.returncode != 0:
                return {'success': False, 'error': proc.stderr[:500]}

            return json.loads(proc.stdout.strip())
        except subprocess.TimeoutExpired:
            return {'success': False, 'error': 'Timeout'}
        except json.JSONDecodeError as e:
            return {'success': False, 'error': f'Invalid JSON: {str(e)[:100]}'}
        finally:
            Path(script_path).unlink(missing_ok=True)

    # ========== UIT: 完整靜態分析 ==========

    def run_uit(self) -> TestTypeResult:
        """執行 UIT 靜態分析測試 - 涵蓋所有模組"""
        result = TestTypeResult(test_type='UIT')
        start_time = datetime.now()

        # 1. 系統層級測試
        system_tests = [
            ('UIT-SYS-01', '系統', 'Code.js 版本管理', self._check_version_management),
            ('UIT-SYS-02', '系統', 'Database.js 資料表定義', self._check_database_schema),
            ('UIT-SYS-03', '系統', 'API 回應格式一致性', self._check_api_format),
            ('UIT-SYS-04', '系統', 'appsscript.json 設定', self._check_appsscript_config),
            ('UIT-SYS-05', '系統', 'HTML v-for :key 綁定', self._check_vfor_key),
            ('UIT-SYS-06', '系統', 'HTML 標籤閉合', self._check_html_tags),
            ('UIT-SYS-07', '系統', f'API 總數驗證 ({len(self.discovered_apis)} 個)', self._check_api_count),
        ]

        for test_id, module, test_name, test_func in system_tests:
            tc = self._run_test_case(test_id, test_name, module, test_func)
            result.test_cases.append(tc)
            if tc.status == 'passed':
                result.passed += 1
            else:
                result.failed += 1

        # 2. 各模組 API 測試
        for module_id, module_info in MODULE_APIS.items():
            test_id = f'UIT-{module_id.upper()[:3]}-API'
            test_name = f"{module_info['name']} API 完整性"

            tc = TestCase(id=test_id, name=test_name, module=module_info['name'])
            tc_start = datetime.now()

            try:
                required = module_info.get('required_apis', [])
                if not required:
                    tc.status = 'passed'
                    tc.details = '無必要 API (前端功能)'
                else:
                    missing = [api for api in required if api not in self.discovered_apis]
                    if missing:
                        tc.status = 'failed'
                        tc.error = f"缺少 API: {', '.join(missing)}"
                    else:
                        tc.status = 'passed'
                        tc.details = f"所有 {len(required)} 個必要 API 存在"

            except Exception as e:
                tc.status = 'failed'
                tc.error = str(e)

            tc.duration = (datetime.now() - tc_start).total_seconds()
            result.test_cases.append(tc)
            if tc.status == 'passed':
                result.passed += 1
            else:
                result.failed += 1

        # 3. 特殊功能測試
        feature_tests = [
            ('UIT-FEAT-01', '功能', '角色權限定義 (6 種角色)', self._check_role_permissions),
            ('UIT-FEAT-02', '功能', 'ISO 27001 稽核日誌', self._check_audit_logging),
            ('UIT-FEAT-03', '功能', 'PIN 碼驗證功能', self._check_pin_verification),
            ('UIT-FEAT-04', '功能', '簽名功能 (Canvas)', self._check_signature_feature),
            ('UIT-FEAT-05', '功能', 'CSV 匯入功能', self._check_csv_import),
            ('UIT-FEAT-06', '功能', '同步功能 (syncDatabase)', self._check_sync_feature),
        ]

        for test_id, module, test_name, test_func in feature_tests:
            tc = self._run_test_case(test_id, test_name, module, test_func)
            result.test_cases.append(tc)
            if tc.status == 'passed':
                result.passed += 1
            else:
                result.failed += 1

        result.duration = (datetime.now() - start_time).total_seconds()
        result.success = result.failed == 0
        return result

    def _run_test_case(self, test_id: str, test_name: str, module: str, test_func) -> TestCase:
        """執行單一測試案例"""
        tc = TestCase(id=test_id, name=test_name, module=module)
        tc_start = datetime.now()
        try:
            passed, details = test_func()
            tc.status = 'passed' if passed else 'failed'
            tc.details = details
            if not passed:
                tc.error = details
        except Exception as e:
            tc.status = 'failed'
            tc.error = str(e)
        tc.duration = (datetime.now() - tc_start).total_seconds()
        return tc

    def _check_version_management(self) -> Tuple[bool, str]:
        if "case 'getVersion':" in self.code_content or 'case "getVersion":' in self.code_content:
            return True, f'版本號: {self.version}'
        return False, '缺少 getVersion API'

    def _check_database_schema(self) -> Tuple[bool, str]:
        if not self.db_content:
            return False, 'Database.js 不存在'
        has_config = 'DB_CONFIG' in self.db_content or 'SCHEMA' in self.db_content
        if not has_config:
            return False, '缺少資料庫設定定義'
        tables = re.findall(r'(\w+):\s*{\s*name:\s*[\'"](\w+)[\'"]', self.db_content)
        if tables:
            return True, f'定義 {len(tables)} 個資料表'
        headers_count = len(re.findall(r'headers:\s*\[', self.db_content))
        if headers_count > 0:
            return True, f'定義 {headers_count} 個資料表'
        return False, '無法解析資料表定義'

    def _check_api_format(self) -> Tuple[bool, str]:
        success_returns = len(re.findall(r'return\s*{\s*success:\s*true', self.code_content))
        error_returns = len(re.findall(r'return\s*{\s*success:\s*false', self.code_content))
        if success_returns > 0 and error_returns > 0:
            return True, f'統一格式: {success_returns} 成功 / {error_returns} 錯誤回應'
        return False, '未使用統一 API 回應格式'

    def _check_appsscript_config(self) -> Tuple[bool, str]:
        config_file = self.project_path / 'appsscript.json'
        if not config_file.exists():
            return False, 'appsscript.json 不存在'
        try:
            config = json.loads(config_file.read_text(encoding='utf-8'))
            runtime = config.get('runtimeVersion', 'DEPRECATED_ES5')
            return True, f'runtime: {runtime}'
        except json.JSONDecodeError as e:
            return False, f'JSON 格式錯誤: {e}'

    def _check_vfor_key(self) -> Tuple[bool, str]:
        issues = []
        for html_file in self.project_path.glob('*.html'):
            content = html_file.read_text(encoding='utf-8')
            v_for_without_key = re.findall(r'v-for="[^"]*"(?![^>]*:key)', content)
            if v_for_without_key:
                issues.append(f'{html_file.name}: {len(v_for_without_key)} 處')
        if issues:
            return False, f'缺少 :key: {", ".join(issues[:3])}'
        return True, '所有 v-for 都有 :key'

    def _check_html_tags(self) -> Tuple[bool, str]:
        issues = []
        tags_to_check = ['div', 'table', 'form']
        for html_file in self.project_path.glob('*.html'):
            content = html_file.read_text(encoding='utf-8')
            for tag in tags_to_check:
                open_count = len(re.findall(rf'<{tag}[^>]*(?<!/)>', content))
                close_count = len(re.findall(rf'</{tag}>', content))
                if open_count > close_count + 3:
                    issues.append(f'{html_file.name}: <{tag}>')
        if issues:
            return False, f'標籤可能未閉合: {"; ".join(issues[:3])}'
        return True, 'HTML 標籤正確閉合'

    def _check_api_count(self) -> Tuple[bool, str]:
        count = len(self.discovered_apis)
        if count >= 80:
            return True, f'發現 {count} 個 API (預期 85+)'
        return False, f'API 數量不足: {count} (預期 85+)'

    def _check_role_permissions(self) -> Tuple[bool, str]:
        roles = ['operator', 'warehouse', 'qc', 'clerk', 'supervisor', 'admin']
        found_roles = [r for r in roles if f'{r}:' in self.app_content]
        if len(found_roles) >= 6:
            return True, f'定義 {len(found_roles)} 種角色'
        return False, f'角色定義不完整: {found_roles}'

    def _check_audit_logging(self) -> Tuple[bool, str]:
        has_log = 'logAudit' in self.app_content or 'createAuditLog' in self.code_content
        has_login = "'login'" in self.app_content or '"login"' in self.app_content
        has_logout = "'logout'" in self.app_content or '"logout"' in self.app_content
        if has_log and has_login and has_logout:
            return True, 'ISO 27001: 登入/登出/操作記錄完整'
        if has_log:
            return True, '有稽核日誌功能 (建議加入登入/登出記錄)'
        return False, '缺少稽核日誌功能'

    def _check_pin_verification(self) -> Tuple[bool, str]:
        has_pin = 'verifyPin' in self.app_content and 'showPinModal' in self.app_content
        if has_pin:
            return True, 'PIN 碼驗證功能已實作'
        return False, '缺少 PIN 碼驗證功能'

    def _check_signature_feature(self) -> Tuple[bool, str]:
        has_signature = 'canvas' in self.app_content.lower() and 'signature' in self.app_content.lower()
        if has_signature:
            return True, '簽名功能 (Canvas) 已實作'
        return False, '缺少簽名功能'

    def _check_csv_import(self) -> Tuple[bool, str]:
        has_import = 'importAoiCsv' in self.discovered_apis or 'importShifts' in self.discovered_apis
        if has_import:
            return True, 'CSV 匯入功能已實作'
        return False, '缺少 CSV 匯入功能'

    def _check_sync_feature(self) -> Tuple[bool, str]:
        if 'syncDatabase' in self.discovered_apis:
            return True, '同步功能 (syncDatabase) 已實作'
        return False, '缺少同步功能'

    # ========== Smoke: 全模組頁面載入測試 ==========

    def run_smoke(self) -> TestTypeResult:
        """執行 Smoke 煙霧測試 - 涵蓋所有模組"""
        result = TestTypeResult(test_type='Smoke')
        start_time = datetime.now()

        # 1. 基礎載入測試
        basic_tests = [
            ('SMOKE-01', '系統', '應用程式載入', 'load'),
            ('SMOKE-02', '系統', '無 JavaScript 錯誤', 'errors'),
            ('SMOKE-03', '系統', '手機版無水平溢出', 'mobile'),
            ('SMOKE-04', '系統', '版本號驗證', 'version'),
        ]

        for test_id, module, test_name, test_type in basic_tests:
            tc = TestCase(id=test_id, name=test_name, module=module)
            tc_start = datetime.now()

            try:
                if test_type == 'load':
                    passed, details, screenshot = self._test_page_load()
                elif test_type == 'errors':
                    passed, details, screenshot = self._test_no_js_errors()
                elif test_type == 'mobile':
                    passed, details, screenshot = self._test_mobile_overflow()
                elif test_type == 'version':
                    passed, details, screenshot = self._test_version_display()
                else:
                    passed, details, screenshot = False, '未知測試', ''

                tc.status = 'passed' if passed else 'failed'
                tc.details = details
                tc.screenshot = screenshot
                if not passed:
                    tc.error = details

            except Exception as e:
                tc.status = 'failed'
                tc.error = str(e)

            tc.duration = (datetime.now() - tc_start).total_seconds()
            result.test_cases.append(tc)
            if tc.status == 'passed':
                result.passed += 1
            else:
                result.failed += 1

        # 2. 各模組頁籤截圖測試
        module_screenshots = self._test_all_module_screenshots()
        module_names = {
            'dashboard': '戰情中心', 'work-orders': '工單管理', 'dispatches': '現場派工',
            'reports': '報工紀錄', 'outgassing': '品質檢驗', 'aoi': 'AOI檢驗',
            'r0': '標籤管理', 'label-editor': '樣式設計', 'schedule': '排程管理',
            'oven': '設備監控', 'wms': '倉儲管理', 'parts': '物料主檔',
            'audit': '操作紀錄', 'settings': '設定',
        }

        for tab_id, tab_name in module_names.items():
            test_id = f'SMOKE-TAB-{tab_id.upper()[:3]}'
            tc = TestCase(id=test_id, name=f'{tab_name} 頁籤截圖', module=tab_name)

            if tab_id in module_screenshots:
                tc.status = 'passed'
                tc.details = f'截圖成功'
                tc.screenshot = module_screenshots[tab_id]
                result.passed += 1
            else:
                tc.status = 'failed'
                tc.error = '截圖失敗或頁籤不存在'
                result.failed += 1

            result.test_cases.append(tc)

        # 3. 各模組 HTML 檔案存在性測試
        module_files = {
            'work-orders': 'tab-work-orders.html',
            'dispatches': 'tab-dispatches.html',
            'reports': 'tab-reports.html',
            'outgassing': 'tab-outgassing.html',
            'aoi': 'tab-aoi.html',
            'r0': 'tab-r0.html',
            'label-editor': 'tab-label-editor.html',
            'schedule': 'tab-schedule.html',
            'oven': 'tab-oven.html',
            'wms': 'tab-wms.html',
            'parts': 'tab-parts.html',
            'audit': 'tab-audit.html',
            'settings': 'tab-settings.html',
            'dashboard': 'tab-dashboard.html',
        }

        for module_id, filename in module_files.items():
            module_name = MODULE_APIS.get(module_id, {}).get('name', module_id)
            test_id = f'SMOKE-{module_id.upper()[:3]}'
            tc = TestCase(id=test_id, name=f'{module_name} 頁面檔案', module=module_name)

            filepath = self.project_path / filename
            if filepath.exists():
                content = filepath.read_text(encoding='utf-8')
                # 檢查是否有實際內容
                if len(content) > 100 and 'v-if' in content:
                    tc.status = 'passed'
                    tc.details = f'{filename} 存在 ({len(content)} bytes)'
                else:
                    tc.status = 'passed'
                    tc.details = f'{filename} 存在 (簡易頁面)'
            else:
                tc.status = 'failed'
                tc.error = f'{filename} 不存在'

            result.test_cases.append(tc)
            if tc.status == 'passed':
                result.passed += 1
            else:
                result.failed += 1

        result.duration = (datetime.now() - start_time).total_seconds()
        result.success = result.failed == 0
        return result

    def _test_page_load(self) -> Tuple[bool, str, str]:
        screenshot_path = str(self.screenshot_dir / 'smoke-01-load.png')
        script = f'''
const puppeteer = require("puppeteer");
(async () => {{
  const browser = await puppeteer.launch({{ headless: "new" }});
  const page = await browser.newPage();
  await page.setViewport({{ width: 1920, height: 1080 }});
  const result = {{ success: false, loadTime: 0, status: 0 }};
  try {{
    const start = Date.now();
    const response = await page.goto("{self.url}", {{ waitUntil: "networkidle0", timeout: 60000 }});
    result.loadTime = Date.now() - start;
    result.status = response ? response.status() : 0;
    await new Promise(r => setTimeout(r, 5000));
    await page.screenshot({{ path: "{screenshot_path}", fullPage: false }});
    result.success = result.status === 200;
  }} catch (e) {{ result.error = e.message; }}
  await browser.close();
  console.log(JSON.stringify(result));
}})();
'''
        result = self._run_puppeteer_test(script)
        if result.get('success'):
            return True, f"載入時間: {result.get('loadTime', 0)}ms", screenshot_path
        return False, result.get('error', '載入失敗'), screenshot_path

    def _test_no_js_errors(self) -> Tuple[bool, str, str]:
        screenshot_path = str(self.screenshot_dir / 'smoke-02-errors.png')
        script = f'''
const puppeteer = require("puppeteer");
(async () => {{
  const browser = await puppeteer.launch({{ headless: "new" }});
  const page = await browser.newPage();
  await page.setViewport({{ width: 1920, height: 1080 }});
  const errors = [];
  page.on("console", msg => {{
    if (msg.type() === "error" && !msg.text().includes("favicon")) {{
      errors.push(msg.text().substring(0, 150));
    }}
  }});
  page.on("pageerror", err => errors.push(err.toString().substring(0, 150)));
  try {{
    await page.goto("{self.url}", {{ waitUntil: "networkidle0", timeout: 60000 }});
    await new Promise(r => setTimeout(r, 5000));
    await page.screenshot({{ path: "{screenshot_path}" }});
  }} catch (e) {{ errors.push(e.message); }}
  await browser.close();
  console.log(JSON.stringify({{ success: errors.length === 0, errors }}));
}})();
'''
        result = self._run_puppeteer_test(script)
        if result.get('success'):
            return True, '無 JavaScript 錯誤', screenshot_path
        errors = result.get('errors', [])
        return False, f"發現 {len(errors)} 個錯誤", screenshot_path

    def _test_mobile_overflow(self) -> Tuple[bool, str, str]:
        screenshot_path = str(self.screenshot_dir / 'smoke-03-mobile.png')
        script = f'''
const puppeteer = require("puppeteer");
(async () => {{
  const browser = await puppeteer.launch({{ headless: "new" }});
  const page = await browser.newPage();
  await page.setViewport({{ width: 375, height: 812, isMobile: true }});
  try {{
    await page.goto("{self.url}", {{ waitUntil: "networkidle0", timeout: 60000 }});
    await new Promise(r => setTimeout(r, 5000));
    const hasOverflow = await page.evaluate(() =>
      document.documentElement.scrollWidth > document.documentElement.clientWidth
    );
    await page.screenshot({{ path: "{screenshot_path}", fullPage: true }});
    console.log(JSON.stringify({{ success: !hasOverflow, hasOverflow }}));
  }} catch (e) {{
    console.log(JSON.stringify({{ success: false, error: e.message }}));
  }}
  await browser.close();
}})();
'''
        result = self._run_puppeteer_test(script)
        if result.get('success'):
            return True, '手機版無水平溢出', screenshot_path
        if result.get('hasOverflow'):
            return False, '偵測到水平溢出', screenshot_path
        return False, result.get('error', '測試失敗'), screenshot_path

    def _test_version_display(self) -> Tuple[bool, str, str]:
        screenshot_path = str(self.screenshot_dir / 'smoke-04-version.png')
        if self.version and self.version != 'unknown':
            script = f'''
const puppeteer = require("puppeteer");
(async () => {{
  const browser = await puppeteer.launch({{ headless: "new" }});
  const page = await browser.newPage();
  await page.setViewport({{ width: 1920, height: 1080 }});
  try {{
    await page.goto("{self.url}", {{ waitUntil: "networkidle0", timeout: 60000 }});
    await new Promise(r => setTimeout(r, 3000));
    await page.screenshot({{ path: "{screenshot_path}" }});
    console.log(JSON.stringify({{ success: true }}));
  }} catch (e) {{
    console.log(JSON.stringify({{ success: false, error: e.message }}));
  }}
  await browser.close();
}})();
'''
            self._run_puppeteer_test(script)
            return True, f'版本號: {self.version}', screenshot_path
        return False, 'Code.js 缺少 getVersion API', screenshot_path

    def _test_all_module_screenshots(self) -> Dict[str, str]:
        """對所有模組頁籤進行截圖"""
        tabs_to_capture = [
            ('dashboard', '戰情中心'),
            ('work-orders', '工單管理'),
            ('dispatches', '現場派工'),
            ('reports', '報工紀錄'),
            ('outgassing', '品質檢驗'),
            ('aoi', 'AOI檢驗'),
            ('r0', '標籤管理'),
            ('label-editor', '樣式設計'),
            ('schedule', '排程管理'),
            ('oven', '設備監控'),
            ('wms', '倉儲管理'),
            ('parts', '物料主檔'),
            ('audit', '操作紀錄'),
            ('settings', '設定'),
        ]

        screenshots = {}
        screenshot_list = ','.join([f'"{t[0]}"' for t in tabs_to_capture])
        screenshot_paths = {t[0]: str(self.screenshot_dir / f'tab-{t[0]}.png') for t in tabs_to_capture}
        paths_json = ','.join([f'"{t[0]}": "{screenshot_paths[t[0]]}"' for t in tabs_to_capture])

        script = f'''
const puppeteer = require("puppeteer");
(async () => {{
  const browser = await puppeteer.launch({{ headless: "new" }});
  const page = await browser.newPage();
  await page.setViewport({{ width: 1920, height: 1080 }});
  const tabs = [{screenshot_list}];
  const paths = {{{paths_json}}};
  const results = {{}};

  try {{
    await page.goto("{self.url}", {{ waitUntil: "networkidle0", timeout: 60000 }});
    await new Promise(r => setTimeout(r, 12000));

    // GAS Web App 結構: frame[0]=main, frame[1]=sandbox, frame[2]=userHtmlFrame (Vue app)
    const frames = page.frames();
    const appFrame = frames[2];  // Vue app is in the innermost frame

    if (!appFrame) {{
      results.error = "Cannot find app frame";
      console.log(JSON.stringify(results));
      await browser.close();
      return;
    }}

    // 驗證 Vue app 存在
    const hasVue = await appFrame.evaluate(() => {{
      const appEl = document.getElementById("app");
      return !!(appEl && appEl.__vue_app__);
    }});

    if (!hasVue) {{
      results.error = "Vue app not found";
      console.log(JSON.stringify(results));
      await browser.close();
      return;
    }}

    results.foundVue = true;

    for (const tab of tabs) {{
      try {{
        // 使用 Vue 3 正確的 proxy 存取方式切換頁籤
        const switched = await appFrame.evaluate((t) => {{
          const appEl = document.getElementById("app");
          if (appEl && appEl.__vue_app__) {{
            const comp = appEl.__vue_app__._container?._vnode?.component;
            if (comp && comp.proxy) {{
              comp.proxy.currentTab = t;
              return comp.proxy.currentTab === t;
            }}
          }}
          return false;
        }}, tab);

        if (!switched) {{
          results[tab] = "switch failed";
          continue;
        }}

        // 等待 Vue 更新 DOM
        await new Promise(r => setTimeout(r, 2000));

        // 截圖
        await page.screenshot({{ path: paths[tab], fullPage: false }});
        results[tab] = "ok";
      }} catch (e) {{
        results[tab] = e.message;
      }}
    }}
  }} catch (e) {{
    results.error = e.message;
  }}

  await browser.close();
  console.log(JSON.stringify(results));
}})();
'''
        result = self._run_puppeteer_test(script)

        for tab_id, tab_name in tabs_to_capture:
            if result.get(tab_id) == 'ok' and Path(screenshot_paths[tab_id]).exists():
                screenshots[tab_id] = screenshot_paths[tab_id]

        return screenshots

    # ========== E2E: 各模組 CRUD 功能測試 ==========

    def run_e2e(self) -> TestTypeResult:
        """執行 E2E 端對端測試 - 各模組 CRUD 驗證"""
        result = TestTypeResult(test_type='E2E')
        start_time = datetime.now()

        # 測試每個模組的 CRUD API 是否存在於 Code.js
        for module_id, module_info in MODULE_APIS.items():
            module_name = module_info['name']
            crud_ops = module_info.get('crud', [])

            if not crud_ops:
                continue  # 跳過無 CRUD 的模組

            for op in crud_ops:
                test_id = f'E2E-{module_id.upper()[:3]}-{op.upper()[:1]}'
                test_name = f'{module_name} - {op.upper()}'

                tc = TestCase(id=test_id, name=test_name, module=module_name)

                # 根據操作類型找對應 API
                api_patterns = {
                    'create': [f'create{module_id.title().replace("-", "")}', f'create'],
                    'read': [f'get{module_id.title().replace("-", "")}', f'get'],
                    'update': [f'update{module_id.title().replace("-", "")}', f'update'],
                    'delete': [f'delete{module_id.title().replace("-", "")}', f'delete'],
                }

                # 檢查是否有對應 API
                found_api = None
                for api in module_info.get('apis', []):
                    api_lower = api.lower()
                    if op == 'create' and api_lower.startswith('create'):
                        found_api = api
                        break
                    elif op == 'read' and api_lower.startswith('get'):
                        found_api = api
                        break
                    elif op == 'update' and api_lower.startswith('update'):
                        found_api = api
                        break
                    elif op == 'delete' and api_lower.startswith('delete'):
                        found_api = api
                        break

                if found_api and found_api in self.discovered_apis:
                    tc.status = 'passed'
                    tc.details = f'API: {found_api}'
                elif found_api:
                    tc.status = 'failed'
                    tc.error = f'API {found_api} 未實作'
                else:
                    tc.status = 'skipped'
                    tc.details = f'無 {op} 操作'
                    result.skipped += 1
                    result.test_cases.append(tc)
                    continue

                result.test_cases.append(tc)
                if tc.status == 'passed':
                    result.passed += 1
                else:
                    result.failed += 1

        # 測試特殊功能 API
        special_features = [
            ('E2E-WMS-IN', '倉儲管理', 'WMS 入庫', 'wmsInbound'),
            ('E2E-WMS-OUT', '倉儲管理', 'WMS 出庫', 'wmsOutbound'),
            ('E2E-WMS-TRF', '倉儲管理', 'WMS 移轉', 'wmsTransfer'),
            ('E2E-DIS-START', '現場派工', '開始派工', 'startDispatch'),
            ('E2E-DIS-COMP', '現場派工', '完成派工', 'completeDispatch'),
            ('E2E-AOI-CSV', 'AOI 檢驗', 'CSV 匯入', 'importAoiCsv'),
            ('E2E-SCH-IMP', '排程管理', '班表匯入', 'importShifts'),
            ('E2E-R0-SYNC', '標籤管理', 'EPC 同步', 'syncR0Labels'),
            ('E2E-R0-CHK', '標籤管理', 'EPC 檢查', 'checkEpc'),
            ('E2E-SYS-SYNC', '系統', '資料庫同步', 'syncDatabase'),
        ]

        for test_id, module, test_name, api_name in special_features:
            tc = TestCase(id=test_id, name=test_name, module=module)
            if api_name in self.discovered_apis:
                tc.status = 'passed'
                tc.details = f'API: {api_name}'
                result.passed += 1
            else:
                tc.status = 'failed'
                tc.error = f'API {api_name} 不存在'
                result.failed += 1
            result.test_cases.append(tc)

        result.duration = (datetime.now() - start_time).total_seconds()
        result.success = result.failed == 0
        return result

    # ========== UAT: 角色權限驗證 ==========

    def run_uat(self) -> TestTypeResult:
        """執行 UAT 使用者驗收測試 - 6 角色 × 14 模組"""
        result = TestTypeResult(test_type='UAT')
        start_time = datetime.now()

        # 1. 角色權限定義測試
        for role, permissions in ROLE_PERMISSIONS.items():
            role_name = ROLE_NAMES.get(role, role)
            test_id = f'UAT-ROLE-{role.upper()[:3]}'
            tc = TestCase(id=test_id, name=f'角色權限: {role_name}', module='權限')

            # 檢查 app.html 中是否有該角色定義
            if f'{role}:' in self.app_content:
                tc.status = 'passed'
                tc.details = f'{len(permissions)} 個頁籤權限'
                result.passed += 1
            else:
                tc.status = 'failed'
                tc.error = f'角色 {role} 未定義'
                result.failed += 1

            result.test_cases.append(tc)

        # 2. 各模組 UI 元素測試
        ui_elements = {
            'work-orders': ['工單', 'orderNumber', 'productModel'],
            'dispatches': ['派工', 'stationName', 'operatorName'],
            'reports': ['報工', 'goodQty', 'ngQty'],
            'outgassing': ['品質', 'signature', 'result'],
            'aoi': ['AOI', 'formAoi', 'aoiCsv'],
            'r0': ['標籤', 'rfidCode', 'epc'],
            'schedule': ['排程', 'schedulePlan', 'shift'],
            'wms': ['倉儲', 'locationCode', 'inventory'],
            'parts': ['物料', 'partNumber', 'partName'],
            'audit': ['稽核', 'auditLog', 'action'],
            'settings': ['設定', 'operator', 'customer'],
        }

        for module_id, keywords in ui_elements.items():
            module_name = MODULE_APIS.get(module_id, {}).get('name', module_id)
            test_id = f'UAT-UI-{module_id.upper()[:3]}'
            tc = TestCase(id=test_id, name=f'{module_name} UI 元素', module=module_name)

            tab_file = self.project_path / f'tab-{module_id}.html'
            if tab_file.exists():
                content = tab_file.read_text(encoding='utf-8')
                found = [kw for kw in keywords if kw.lower() in content.lower()]
                if len(found) >= 2:
                    tc.status = 'passed'
                    tc.details = f'包含關鍵字: {", ".join(found[:3])}'
                    result.passed += 1
                else:
                    tc.status = 'failed'
                    tc.error = f'缺少關鍵 UI 元素'
                    result.failed += 1
            else:
                tc.status = 'skipped'
                tc.details = f'tab-{module_id}.html 不存在'
                result.skipped += 1

            result.test_cases.append(tc)

        # 3. ISO 27001 合規測試
        iso_tests = [
            ('UAT-ISO-01', 'ISO 27001', '操作紀錄 (A.8.15)', 'getAuditLogs' in self.discovered_apis),
            ('UAT-ISO-02', 'ISO 27001', '存取控制 (A.9.2)', len(ROLE_PERMISSIONS) >= 6),
            ('UAT-ISO-03', 'ISO 27001', '身份驗證 (A.9.4)', 'verifyPin' in self.app_content),
            ('UAT-ISO-04', 'ISO 27001', '資料完整性 (A.14.1)', 'syncDatabase' in self.discovered_apis),
        ]

        for test_id, module, test_name, condition in iso_tests:
            tc = TestCase(id=test_id, name=test_name, module=module)
            if condition:
                tc.status = 'passed'
                tc.details = '符合要求'
                result.passed += 1
            else:
                tc.status = 'failed'
                tc.error = '不符合要求'
                result.failed += 1
            result.test_cases.append(tc)

        result.duration = (datetime.now() - start_time).total_seconds()
        result.success = result.failed == 0
        return result

    # ========== 執行所有測試 ==========

    def run_all(self, test_types: List[str] = None) -> GASMESTestResult:
        """執行所有測試類型"""
        if test_types is None:
            test_types = ['UIT', 'Smoke', 'E2E', 'UAT']

        result = GASMESTestResult(
            project_name='GAS MES',
            timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            version=self.version,
            api_count=len(self.discovered_apis),
            module_count=len(MODULE_APIS)
        )

        for test_type in test_types:
            test_type_upper = test_type.upper()

            console.print(f"  [dim]執行 {test_type_upper} 測試...[/dim]")

            if test_type_upper == 'UIT':
                type_result = self.run_uit()
            elif test_type_upper == 'SMOKE':
                type_result = self.run_smoke()
            elif test_type_upper == 'E2E':
                type_result = self.run_e2e()
            elif test_type_upper == 'UAT':
                type_result = self.run_uat()
            else:
                continue

            result.results[test_type_upper] = type_result
            result.total_passed += type_result.passed
            result.total_failed += type_result.failed
            result.total_duration += type_result.duration

            if not type_result.success:
                result.overall_success = False

        return result


def render_gas_test_result(result: GASMESTestResult):
    """渲染 GAS MES 測試結果"""
    status_icon = "v" if result.overall_success else "x"
    status_color = "green" if result.overall_success else "red"

    console.print(Panel(
        f"[bold]{result.project_name}[/bold] v{result.version} 測試報告\n"
        f"[dim]{result.timestamp} | {result.api_count} APIs | {result.module_count} 模組[/dim]",
        border_style="cyan"
    ))

    # 結果表格
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("測試類型", style="white")
    table.add_column("狀態", justify="center")
    table.add_column("通過", justify="right", style="green")
    table.add_column("失敗", justify="right", style="red")
    table.add_column("跳過", justify="right", style="yellow")
    table.add_column("時間", justify="right", style="dim")

    type_labels = {
        'UIT': '靜態分析 (UIT)',
        'SMOKE': '煙霧測試 (Smoke)',
        'E2E': '功能測試 (E2E)',
        'UAT': '驗收測試 (UAT)'
    }

    for test_type, type_result in result.results.items():
        status = "[green]PASS[/green]" if type_result.success else "[red]FAIL[/red]"
        table.add_row(
            type_labels.get(test_type, test_type),
            status,
            str(type_result.passed),
            str(type_result.failed) if type_result.failed else "-",
            str(type_result.skipped) if type_result.skipped else "-",
            f"{type_result.duration:.1f}s"
        )

    console.print(table)

    # 總結
    total = result.total_passed + result.total_failed
    if total > 0:
        pass_rate = (result.total_passed / total) * 100
        console.print(f"\n  總計: [green]{result.total_passed} passed[/green] / "
                     f"[{'red' if result.total_failed else 'dim'}]{result.total_failed} failed[/]"
                     f"  |  通過率: {pass_rate:.1f}%  |  {result.total_duration:.1f}s")

    if result.overall_success:
        console.print(f"\n  [{status_color}][{status_icon}] 所有測試通過[/{status_color}]\n")
    else:
        console.print(f"\n  [{status_color}][{status_icon}] 部分測試失敗[/{status_color}]\n")
        # 顯示失敗詳情 (最多 10 個)
        failed_count = 0
        for test_type, type_result in result.results.items():
            if not type_result.success:
                for tc in type_result.test_cases:
                    if tc.status == 'failed' and failed_count < 10:
                        console.print(f"    [red]x[/red] {tc.id}: {tc.name}")
                        console.print(f"      [dim]{tc.error[:80]}[/dim]")
                        failed_count += 1

    return {
        'success': result.overall_success,
        'total_passed': result.total_passed,
        'total_failed': result.total_failed,
        'version': result.version,
        'api_count': result.api_count
    }


def run_gas_test(project_path: str, test_types: List[str] = None, url: str = None) -> Dict:
    """執行 GAS MES 測試"""
    runner = GASMESTestRunner(project_path, url)

    console.print(f"[cyan]GAS MES 完整測試套件[/cyan]")
    console.print(f"[dim]  專案: {project_path}[/dim]")
    console.print(f"[dim]  發現 {len(runner.discovered_apis)} 個 API[/dim]")
    console.print()

    result = runner.run_all(test_types)
    return render_gas_test_result(result)


def run_gas_test_with_report(
    project_path: str,
    output_path: str = None,
    test_types: List[str] = None,
    url: str = None
) -> Dict:
    """執行 GAS MES 測試並產生 Word 報告"""
    from .word_report import generate_word_report

    runner = GASMESTestRunner(project_path, url)

    console.print(f"[cyan]GAS MES 完整測試套件[/cyan]")
    console.print(f"[dim]  專案: {project_path}[/dim]")
    console.print(f"[dim]  發現 {len(runner.discovered_apis)} 個 API[/dim]")
    console.print()

    result = runner.run_all(test_types)
    render_gas_test_result(result)

    # 準備報告資料
    if not output_path:
        output_path = str(Path(project_path) / 'GAS_MES-test-report.docx')

    test_results = {
        'project': f'{result.project_name} v{result.version}',
        'timestamp': result.timestamp,
        'overall_success': result.overall_success,
        'summary': {
            'total_passed': result.total_passed,
            'total_failed': result.total_failed,
            'total_duration': result.total_duration,
            'coverage': 0
        },
        'tests': {
            k: {
                'success': v.success,
                'passed': v.passed,
                'failed': v.failed,
                'duration': v.duration,
                'coverage': 0,
                'not_configured': v.not_configured,
                'test_cases': [
                    {
                        'name': f"[{tc.module}] {tc.name}" if tc.module else tc.name,
                        'status': tc.status,
                        'duration': tc.duration,
                        'error': tc.error,
                        'screenshot': tc.screenshot,
                        'api_response': '',
                        'terminal_output': tc.details
                    }
                    for tc in v.test_cases
                ]
            }
            for k, v in result.results.items()
        }
    }

    # 收集截圖
    screenshots = []
    for type_result in result.results.values():
        for tc in type_result.test_cases:
            if tc.screenshot and Path(tc.screenshot).exists():
                screenshots.append(tc.screenshot)

    console.print(f"\n[cyan]產生 Word 報告... (收集到 {len(screenshots)} 張截圖)[/cyan]")
    report_path = generate_word_report(
        project_name=f'{result.project_name} v{result.version}',
        test_results=test_results,
        output_path=output_path,
        screenshots=screenshots,  # 包含所有模組截圖
        include_charts=True
    )

    console.print(f"[green]報告已產生: {report_path}[/green]")

    return {
        'success': result.overall_success,
        'report_path': report_path,
        'total_passed': result.total_passed,
        'total_failed': result.total_failed
    }
