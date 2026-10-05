"""Notification and alert dispatch engine."""
import os
import requests
import json
from datetime import datetime

class AlertDispatcher:
    def __init__(self):
        self.telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")
        self.slack_webhook = os.getenv("SLACK_WEBHOOK_URL")

    def send_daily_alert(self, summary_report: str):
        """Dispatches daily analysis to configured endpoints."""
        if self.telegram_token and self.telegram_chat_id:
            try:
                url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
                payload = {
                    "chat_id": self.telegram_chat_id,
                    "text": summary_report,
                    "parse_mode": "Markdown"
                }
                requests.post(url, json=payload, timeout=10)
            except Exception as e:
                print(f"[AlertDispatcher] Telegram dispatch failed: {e}")

        if self.slack_webhook:
            try:
                requests.post(self.slack_webhook, json={"text": summary_report}, timeout=10)
            except Exception as e:
                print(f"[AlertDispatcher] Slack webhook failed: {e}")