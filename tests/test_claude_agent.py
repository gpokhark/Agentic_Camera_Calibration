import unittest

from agentic_camera_calibration.claude_agent import _build_request_body, _extract_output_text


def _payload() -> dict:
    return {
        "system_prompt": "You are a calibration recovery controller.",
        "controller_state": {
            "run_id": "run_01",
            "scenario": "S2_low_light",
            "retry_index": 0,
            "reason_codes": ["low_light", "insufficient_usable_frames"],
            "allowed_actions": [
                "reject_bad_frames",
                "apply_preprocessing",
                "request_additional_views",
                "retry_with_filtered_subset",
                "relax_nominal_prior",
                "declare_unrecoverable",
            ],
        },
        "required_schema": {
            "diagnosis": "string",
            "actions": [{"action": "string", "params": "object"}],
            "confidence": "number[0,1]",
            "declare_unrecoverable": "bool",
        },
        "agent_settings": {
            "model": "claude-haiku-4-5-20251001",
            "max_output_tokens": 180,
            "timeout_seconds": 45,
        },
    }


class ClaudeAgentTests(unittest.TestCase):
    def test_build_request_body_uses_messages_api_format(self) -> None:
        body = _build_request_body(_payload())
        self.assertEqual(body["model"], "claude-haiku-4-5-20251001")
        self.assertEqual(body["max_tokens"], 180)
        self.assertIn("system", body)
        self.assertIsInstance(body["messages"], list)
        self.assertEqual(body["messages"][0]["role"], "user")

    def test_build_request_body_embeds_system_suffix(self) -> None:
        body = _build_request_body(_payload())
        self.assertIn("declare_unrecoverable", body["system"])

    def test_build_request_body_embeds_controller_state_in_user_message(self) -> None:
        body = _build_request_body(_payload())
        user_content = body["messages"][0]["content"]
        self.assertIn("S2_low_light", user_content)
        self.assertIn("low_light", user_content)

    def test_extract_output_text_returns_text_block(self) -> None:
        response = {
            "content": [
                {"type": "text", "text": '{"diagnosis":"ok","actions":[],"confidence":0.8,"declare_unrecoverable":false}'},
            ]
        }
        text = _extract_output_text(response)
        self.assertIn('"diagnosis":"ok"', text)

    def test_extract_output_text_raises_on_empty_content(self) -> None:
        with self.assertRaises(RuntimeError):
            _extract_output_text({"content": []})

    def test_extract_output_text_skips_non_text_blocks(self) -> None:
        response = {
            "content": [
                {"type": "thinking", "thinking": "reasoning here"},
                {"type": "text", "text": '{"diagnosis":"ok","actions":[],"confidence":0.9,"declare_unrecoverable":false}'},
            ]
        }
        text = _extract_output_text(response)
        self.assertIn('"confidence":0.9', text)


if __name__ == "__main__":
    unittest.main()
