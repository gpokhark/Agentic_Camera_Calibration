from __future__ import annotations

import json
import os
import sys
from urllib import error, request


API_URL = "https://api.openai.com/v1/responses"

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
    body = {
        "model": settings.get("model", "gpt-5-mini"),
        "input": [
            {
                "role": "system",
                "content": [{"type": "input_text", "text": system_prompt}],
            },
            {
                "role": "user",
                "content": [{"type": "input_text", "text": user_prompt}],
            },
        ],
        "max_output_tokens": int(settings.get("max_output_tokens", 180)),
        "prompt_cache_key": settings.get("prompt_cache_key", "accal-controller-v1"),
        "prompt_cache_retention": settings.get("prompt_cache_retention", "24h"),
        "metadata": {
            "app": "agentic_camera_calibration",
            "scenario": str(payload["controller_state"].get("scenario", "")),
            "retry_index": str(payload["controller_state"].get("retry_index", "")),
        },
    }

    reasoning_effort = settings.get("reasoning_effort")
    if reasoning_effort:
        body["reasoning"] = {"effort": reasoning_effort}
    return body


def _extract_output_text(response_payload: dict) -> str:
    if response_payload.get("output_text"):
        return str(response_payload["output_text"]).strip()

    texts: list[str] = []
    for item in response_payload.get("output", []):
        for content in item.get("content", []):
            text_value = content.get("text")
            if isinstance(text_value, str) and text_value.strip():
                texts.append(text_value.strip())
    if texts:
        return "\n".join(texts)
    raise RuntimeError(f"OpenAI response did not contain text output: {json.dumps(response_payload)[:500]}")


def _post_json(body: dict, timeout_seconds: int) -> dict:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set.")

    req = request.Request(
        API_URL,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"OpenAI API HTTP {exc.code}: {detail}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"OpenAI API request failed: {exc}") from exc


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
