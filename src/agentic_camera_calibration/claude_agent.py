from __future__ import annotations

import json
import os
import sys
from urllib import error, request


API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"

SYSTEM_SUFFIX = (
    "Rules: use only allowed actions; prefer 1-2 actions when possible; "
    "prioritize improving image evidence before relaxing geometry; "
    "declare unrecoverable if repeated failures indicate no safe recovery path; "
    "return valid JSON only with keys diagnosis, actions, confidence, declare_unrecoverable."
)


def _build_prompt(payload: dict) -> tuple[str, str]:
    system_prompt = f"{payload.get('system_prompt', '').strip()} {SYSTEM_SUFFIX}".strip()
    controller_state = json.dumps(payload["controller_state"], separators=(",", ":"), sort_keys=True)
    required_schema = json.dumps(payload.get("required_schema", {}), separators=(",", ":"), sort_keys=True)
    user_prompt = (
        "Calibration recovery request.\n"
        f"Controller state: {controller_state}\n"
        f"Required schema: {required_schema}\n"
        "Return exactly one JSON object and no surrounding prose."
    )
    return system_prompt, user_prompt


def _build_request_body(payload: dict) -> dict:
    settings = payload.get("agent_settings", {})
    system_prompt, user_prompt = _build_prompt(payload)
    return {
        "model": settings.get("model", "claude-haiku-4-5-20251001"),
        "max_tokens": int(settings.get("max_output_tokens", 180)),
        "system": system_prompt,
        "messages": [{"role": "user", "content": user_prompt}],
    }


def _extract_output_text(response_payload: dict) -> str:
    for block in response_payload.get("content", []):
        if block.get("type") == "text":
            text = block.get("text", "").strip()
            if text:
                return text
    raise RuntimeError(f"Claude response did not contain text output: {json.dumps(response_payload)[:500]}")


def _post_json(body: dict, timeout_seconds: int) -> dict:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set.")

    req = request.Request(
        API_URL,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": ANTHROPIC_VERSION,
        },
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Anthropic API HTTP {exc.code}: {detail}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"Anthropic API request failed: {exc}") from exc


def main() -> None:
    raw = sys.stdin.read()
    payload = json.loads(raw)
    timeout_seconds = int(payload.get("agent_settings", {}).get("timeout_seconds", 45))
    body = _build_request_body(payload)
    response_payload = _post_json(body, timeout_seconds=timeout_seconds)
    output_text = _extract_output_text(response_payload)
    decision = json.loads(output_text)
    sys.stdout.write(json.dumps(decision))
    sys.stdout.flush()


if __name__ == "__main__":
    main()
