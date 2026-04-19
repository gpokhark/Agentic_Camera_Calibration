import unittest

from agentic_camera_calibration.lm_studio_agent import _build_request_body, _extract_output_text


def _payload(base_url: str = "http://localhost:1234/v1") -> dict:
    return {
        "system_prompt": "You are a calibration recovery controller.",
        "controller_state": {
            "run_id": "run_01",
            "scenario": "S3_pose_deviation",
            "retry_index": 0,
            "reason_codes": ["pose_out_of_range"],
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
            "model": "local-model",
            "max_output_tokens": 256,
            "timeout_seconds": 60,
            "base_url": base_url,
        },
    }


class LMStudioAgentTests(unittest.TestCase):
    def test_build_request_body_uses_chat_completions_format(self) -> None:
        body = _build_request_body(_payload())
        self.assertIn("messages", body)
        roles = [m["role"] for m in body["messages"]]
        self.assertEqual(roles, ["system", "user"])

    def test_build_request_body_sets_temperature_zero(self) -> None:
        body = _build_request_body(_payload())
        self.assertEqual(body["temperature"], 0)

    def test_build_request_body_embeds_system_suffix(self) -> None:
        body = _build_request_body(_payload())
        system_content = body["messages"][0]["content"]
        self.assertIn("declare_unrecoverable", system_content)

    def test_build_request_body_embeds_controller_state_in_user_message(self) -> None:
        body = _build_request_body(_payload())
        user_content = body["messages"][1]["content"]
        self.assertIn("S3_pose_deviation", user_content)
        self.assertIn("pose_out_of_range", user_content)

    def test_extract_output_text_returns_choice_content(self) -> None:
        response = {
            "choices": [
                {"message": {"content": '{"diagnosis":"ok","actions":[],"confidence":0.7,"declare_unrecoverable":false}'}}
            ]
        }
        text = _extract_output_text(response)
        self.assertIn('"diagnosis":"ok"', text)

    def test_extract_output_text_raises_on_empty_choices(self) -> None:
        with self.assertRaises(RuntimeError):
            _extract_output_text({"choices": []})

    def test_extract_output_text_raises_on_missing_choices(self) -> None:
        with self.assertRaises(RuntimeError):
            _extract_output_text({})


if __name__ == "__main__":
    unittest.main()
