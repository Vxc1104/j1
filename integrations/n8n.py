import os
import requests


def trigger_webhook(webhook_name: str, payload: dict = None) -> dict:
    base_url = os.getenv("N8N_WEBHOOK_URL", "http://localhost:5678/webhook")
    url = f"{base_url}/{webhook_name}"
    response = requests.post(url, json=payload or {}, timeout=30)
    if response.status_code == 200:
        try:
            return response.json()
        except Exception:
            return {"status": "ok", "raw": response.text}
    return {"error": f"HTTP {response.status_code}", "detail": response.text}


def get_business_update() -> dict:
    return trigger_webhook("business-update")


def send_notification(message: str, channel: str = "general") -> dict:
    return trigger_webhook("send-notification", {"message": message, "channel": channel})
