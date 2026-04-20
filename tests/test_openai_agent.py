import unittest

from agentic_camera_calibration.openai_agent import _build_request_body, _extract_output_text


def _payload() -> dict:
    return {
        "system_prompt": "You are a calibration recovery controller.",
        "controller_state": {
            "run_id": "run_01",
            "scenario": "S1_overexposed",
            "retry_index": 0,
            "reason_codes": ["overexposure", "low_corner_count"],
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
            "model": "gpt-5-mini",
            "reasoning_effort": "minimal",
            "max_output_tokens": 180,
            "timeout_seconds": 45,
            "prompt_cache_key": "accal-controller-v1",
            "prompt_cache_retention": "24h",
        },
    }


class OpenAIAgentTests(unittest.TestCase):
    def test_build_request_body_includes_low_cost_settings(self) -> None:
        body = _build_request_body(_payload())
        self.assertEqual(body["model"], "gpt-5-mini")
        self.assertEqual(body["max_output_tokens"], 180)
        self.assertEqual(body["reasoning"]["effort"], "minimal")
        self.assertEqual(body["prompt_cache_key"], "accal-controller-v1")
        self.assertEqual(body["prompt_cache_retention"], "24h")
        self.assertEqual(body["metadata"]["scenario"], "S1_overexposed")

    def test_extract_output_text_prefers_top_level_output_text(self) -> None:
        text = _extract_output_text({"output_text": '{"diagnosis":"ok","actions":[],"confidence":0.5,"declare_unrecoverable":false}'})
        self.assertIn('"diagnosis":"ok"', text)

    def test_extract_output_text_falls_back_to_output_content(self) -> None:
        response_payload = {
            "output": [
                {
                    "content": [
                        {
                            "type": "output_text",
                            "text": '{"diagnosis":"ok","actions":[],"confidence":0.5,"declare_unrecoverable":false}',
                        }
                    ]
                }
            ]
        }
        text = _extract_output_text(response_payload)
        self.assertIn('"confidence":0.5', text)


if __name__ == "__main__":
    unittest.main()
