"""
Email delivery via Resend. Plain text body; subject set by caller.
"""
import os
import requests


def send_email(subject: str, body: str, to: str | None = None) -> dict:
    api_key = os.environ.get("RESEND_API_KEY")
    if not api_key:
        raise RuntimeError("RESEND_API_KEY missing")
    sender = os.environ.get("NOTIFY_EMAIL_FROM", "ads@musicalbasics.com")
    recipient = to or os.environ.get("NOTIFY_EMAIL_TO")
    if not recipient:
        raise RuntimeError("no recipient (NOTIFY_EMAIL_TO not set and no `to` provided)")
    res = requests.post(
        "https://api.resend.com/emails",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "from": sender,
            "to": [recipient],
            "subject": subject,
            "text": body,
        },
        timeout=15,
    )
    res.raise_for_status()
    return res.json()
