"""SMS gateways: how replies leave the server and how incoming SMS arrive.

  simulator  replies are only stored; the simulator web page shows them.
  android    an Android phone with a SIM running the open-source "SMS Gateway
             for Android" app (docs.sms-gate.app). Incoming SMS arrive as a
             webhook (event sms:received); replies go out through the app's API
             (cloud relay by default, or the phone's local server).
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import sys
import urllib.request


class Gateway:
    kind = "base"

    def send(self, phone: str, text: str) -> None:
        raise NotImplementedError


class SimulatorGateway(Gateway):
    kind = "simulator"

    def send(self, phone: str, text: str) -> None:
        pass


class SmsGateGateway(Gateway):
    kind = "android"

    def __init__(self, base_url: str, username: str, password: str, timeout_s: float = 20):
        self.base_url = base_url.rstrip("/")
        self.auth = base64.b64encode(f"{username}:{password}".encode()).decode()
        self.timeout_s = timeout_s

    def send(self, phone: str, text: str) -> None:
        body = json.dumps({"textMessage": {"text": text}, "phoneNumbers": [phone]}).encode()
        req = urllib.request.Request(f"{self.base_url}/messages", data=body, method="POST", headers={
            "Content-Type": "application/json", "Authorization": f"Basic {self.auth}"})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
                resp.read()
        except Exception as exc:  # the reply is already logged; a failed send must not stop the worker
            print(f"[gateway] send to {phone} failed: {exc}", file=sys.stderr)


def from_env() -> Gateway:
    kind = os.environ.get("SMS_GATEWAY", "simulator")
    if kind == "android":
        return SmsGateGateway(os.environ.get("SMSGATE_URL", "https://api.sms-gate.app/3rdparty/v1"),
                              os.environ["SMSGATE_USER"], os.environ["SMSGATE_PASSWORD"])
    return SimulatorGateway()


def parse_smsgate_webhook(body: dict) -> tuple[str | None, str, str] | None:
    """Return (gateway_id, sender phone, text) for an sms:received event, else None."""
    if body.get("event") != "sms:received":
        return None
    p = body.get("payload") or {}
    sender = p.get("sender") or p.get("phoneNumber")
    if not sender or p.get("message") is None:
        return None
    return (p.get("messageId") or body.get("id")), sender, p["message"]


def verify_signature(key: str, raw_body: bytes, timestamp: str, signature: str) -> bool:
    expected = hmac.new(key.encode(), raw_body + timestamp.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature or "")
