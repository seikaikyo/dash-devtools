"""
UptimeRobot 監控管理

透過 UptimeRobot API 管理 Render 服務的 keep-alive 監控。
免費方案：50 個 monitor、5 分鐘間隔、HEAD 請求。

環境變數：UPTIMEROBOT_API_KEY
"""

import os
import requests


API_URL = "https://api.uptimerobot.com/v2"
DEFAULT_INTERVAL = 300  # 5 分鐘 (免費方案最小值)
MONITOR_TYPE_HTTP = 1
RENDER_HEALTH_SUFFIX = "/health"

# UptimeRobot monitor status codes
STATUS_MAP = {
    0: "暫停",
    1: "尚未檢查",
    2: "正常",
    8: "似乎異常",
    9: "異常",
}


def _get_api_key() -> str:
    """取得 API Key"""
    key = os.environ.get("UPTIMEROBOT_API_KEY", "")
    if not key:
        raise RuntimeError(
            "未設定 UPTIMEROBOT_API_KEY 環境變數\n"
            "請到 UptimeRobot Dashboard → Integrations & API → 建立 API Key\n"
            "然後加入 ~/.env: export UPTIMEROBOT_API_KEY=your_key"
        )
    return key


def _post(endpoint: str, data: dict | None = None) -> dict:
    """呼叫 UptimeRobot API"""
    payload = {"api_key": _get_api_key(), "format": "json"}
    if data:
        payload.update(data)
    resp = requests.post(f"{API_URL}/{endpoint}", data=payload, timeout=10)
    resp.raise_for_status()
    result = resp.json()
    if result.get("stat") != "ok":
        error = result.get("error", {})
        msg = error.get("message", str(error)) if isinstance(error, dict) else str(error)
        raise RuntimeError(f"UptimeRobot API 錯誤: {msg}")
    return result


def list_monitors() -> list[dict]:
    """列出所有 monitor"""
    result = _post("getMonitors")
    monitors = result.get("monitors", [])
    return [
        {
            "id": m["id"],
            "name": m["friendly_name"],
            "url": m["url"],
            "status": STATUS_MAP.get(m["status"], f"未知({m['status']})"),
            "status_code": m["status"],
            "interval": m.get("interval", 0),
        }
        for m in monitors
    ]


def add_monitor(service_name: str, url: str | None = None) -> dict:
    """新增 Render 服務監控

    Args:
        service_name: Render 服務名稱 (如 sukuyodo-backend)
        url: 自訂 URL，預設為 https://{service_name}.onrender.com/health
    """
    if not url:
        url = f"https://{service_name}.onrender.com{RENDER_HEALTH_SUFFIX}"

    # 檢查是否已存在
    existing = list_monitors()
    for m in existing:
        if m["url"] == url:
            return {"success": False, "error": f"已存在相同 URL 的 monitor: {m['name']}"}

    result = _post("newMonitor", {
        "friendly_name": service_name,
        "url": url,
        "type": MONITOR_TYPE_HTTP,
        "interval": DEFAULT_INTERVAL,
    })

    monitor_id = result.get("monitor", {}).get("id", "N/A")
    return {"success": True, "id": monitor_id, "name": service_name, "url": url}


def remove_monitor(service_name: str) -> dict:
    """移除監控

    Args:
        service_name: monitor 名稱或 ID
    """
    existing = list_monitors()

    target = None
    for m in existing:
        if m["name"] == service_name or str(m["id"]) == service_name:
            target = m
            break

    if not target:
        return {"success": False, "error": f"找不到 monitor: {service_name}"}

    _post("deleteMonitor", {"id": target["id"]})
    return {"success": True, "name": target["name"], "url": target["url"]}
