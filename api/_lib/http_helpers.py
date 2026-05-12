"""
HTTP helpers shared by all serverless handlers.
"""
import json
import os
from urllib.parse import urlparse, parse_qs


def require_api_key(handler) -> bool:
    expected = os.environ.get("API_KEY")
    if not expected:
        return False
    auth = handler.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return False
    return auth[len("Bearer "):].strip() == expected.strip()


def respond(handler, status: int, body):
    handler.send_response(status)
    if isinstance(body, str):
        handler.send_header("Content-Type", "text/plain; charset=utf-8")
        payload = body.encode("utf-8")
    else:
        handler.send_header("Content-Type", "application/json")
        payload = json.dumps(body, default=str).encode("utf-8")
    handler.send_header("Content-Length", str(len(payload)))
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
    handler.end_headers()
    handler.wfile.write(payload)


def read_json_body(handler) -> dict:
    length = int(handler.headers.get("Content-Length", "0") or 0)
    if length == 0:
        return {}
    raw = handler.rfile.read(length)
    try:
        return json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError:
        return {}


def read_query(handler) -> dict:
    parsed = urlparse(handler.path)
    qs = parse_qs(parsed.query)
    return {k: (v[0] if v else "") for k, v in qs.items()}
