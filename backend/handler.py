"""AWS Lambda entry point (API Gateway HTTP API, payload v2)."""
import json

from agent import run


def _resp(status: int, body: dict) -> dict:
    return {"statusCode": status, "headers": {"content-type": "application/json"}, "body": json.dumps(body)}


def lambda_handler(event, context=None, client=None):
    method = event.get("requestContext", {}).get("http", {}).get("method", "POST")
    path = event.get("rawPath", "/decide")
    if method == "GET" and path.endswith("/health"):
        return _resp(200, {"ok": True})
    if method != "POST" or not path.endswith("/decide"):
        return _resp(404, {"error": "not found"})
    try:
        payload = json.loads(event.get("body") or "{}")
        if "facts" not in payload:
            return _resp(400, {"error": "missing 'facts'"})
        return _resp(200, run(payload, client))
    except (ValueError, KeyError, TypeError) as exc:  # malformed input
        return _resp(400, {"error": f"{type(exc).__name__}: {exc}"})
