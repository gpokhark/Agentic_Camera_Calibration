from __future__ import annotations

import json
import sys
from urllib import error, request


DEFAULT_BASE_URL = "http://localhost:1234/v1"

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
        "model": settings.get("model", "local-model"),
        "max_tokens": int(settings.get("max_output_tokens", 256)),
        "temperature": 0,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }


def _extract_output_text(response_payload: dict) -> str:
    choices = response_payload.get("choices", [])
    if choices:
        content = choices[0].get("message", {}).get("content", "").strip()
        if content:
            return content
    raise RuntimeError(f"LM Studio response did not contain text output: {json.dumps(response_payload)[:500]}")


def _post_json(body: dict, base_url: str, timeout_seconds: int) -> dict:
    url = base_url.rstrip("/") + "/chat/completions"
    req = request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"LM Studio HTTP {exc.code}: {detail}") from exc
    except error.URLError as exc:
        raise RuntimeError(
            f"LM Studio request failed: {exc}. "
            "Ensure LM Studio is running with the local server enabled."
        ) from exc


def main() -> None:
    raw = sys.stdin.read()
    payload = json.loads(raw)
    settings = payload.get("agent_settings", {})
    timeout_seconds = int(settings.get("timeout_seconds", 60))
    base_url = settings.get("base_url", DEFAULT_BASE_URL)
    body = _build_request_body(payload)
    response_payload = _post_json(body, base_url=base_url, timeout_seconds=timeout_seconds)
    output_text = _extract_output_text(response_payload)
    decision = json.loads(output_text)
    sys.stdout.write(json.dumps(decision))
    sys.stdout.flush()


if __name__ == "__main__":
    main()
