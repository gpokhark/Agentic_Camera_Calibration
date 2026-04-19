import unittest

from agentic_camera_calibration.config import ControllerConfig
from agentic_camera_calibration.controllers.agent_controller import AgentController
from agentic_camera_calibration.models import ControllerState


def _sample_state() -> ControllerState:
    return ControllerState(
        run_id="run_01",
        scenario="S3_pose_deviation",
        retry_index=1,
        frames_total=18,
        frames_active=12,
        frames_reserved_remaining=6,
        mean_brightness=122.3456,
        mean_saturation_ratio=0.02191,
        mean_blur_score=88.1234,
        mean_glare_score=0.04219,
        mean_marker_count=14.2,
        mean_charuco_corner_count=18.9,
        mean_coverage_score=0.28419,
        calibration_success=False,
        reprojection_error=2.34567,
        deviation_result=None,
        reason_codes=["low_marker_coverage", "pose_out_of_range"],
        attempted_actions=[
            {"retry_index": 0, "reason_codes": ["low_marker_coverage"]},
            {"retry_index": 1, "reason_codes": ["low_marker_coverage", "pose_out_of_range"]},
            {"retry_index": 2, "reason_codes": ["low_marker_coverage", "pose_out_of_range"]},
        ],
        allowed_actions=ControllerConfig().allowed_actions,
    )


class AgentControllerTests(unittest.TestCase):
    def test_raises_on_unknown_backend(self) -> None:
        controller = AgentController(ControllerConfig(agent_command=[], agent_backend="unknown"))
        with self.assertRaises(RuntimeError):
            controller._resolved_command()

    def test_resolved_command_openai_backend(self) -> None:
        controller = AgentController(ControllerConfig(agent_command=[], agent_backend="openai"))
        cmd = controller._resolved_command()
        self.assertTrue(any("openai_agent" in part for part in cmd))

    def test_resolved_command_claude_backend(self) -> None:
        controller = AgentController(ControllerConfig(agent_command=[], agent_backend="claude"))
        cmd = controller._resolved_command()
        self.assertTrue(any("claude_agent" in part for part in cmd))

    def test_explicit_agent_command_overrides_backend(self) -> None:
        custom_cmd = ["python", "my_custom_agent.py"]
        controller = AgentController(ControllerConfig(agent_command=custom_cmd, agent_backend="openai"))
        self.assertEqual(controller._resolved_command(), custom_cmd)

    def test_build_payload_uses_claude_model_for_claude_backend(self) -> None:
        config = ControllerConfig(
            agent_backend="claude",
            claude_agent_model="claude-haiku-4-5-20251001",
            agent_model="gpt-5-mini",
        )
        controller = AgentController(config)
        payload = controller._build_payload(_sample_state())
        self.assertEqual(payload["agent_settings"]["model"], "claude-haiku-4-5-20251001")

    def test_build_payload_uses_openai_model_for_openai_backend(self) -> None:
        config = ControllerConfig(
            agent_backend="openai",
            agent_model="gpt-5-mini",
            claude_agent_model="claude-haiku-4-5-20251001",
        )
        controller = AgentController(config)
        payload = controller._build_payload(_sample_state())
        self.assertEqual(payload["agent_settings"]["model"], "gpt-5-mini")

    def test_build_payload_compacts_attempt_history_and_includes_cost_settings(self) -> None:
        config = ControllerConfig(
            agent_command=["python", "-m", "agentic_camera_calibration.openai_agent"],
            agent_history_limit=2,
            agent_model="gpt-5-mini",
            agent_reasoning_effort="minimal",
            agent_max_output_tokens=120,
            agent_timeout_seconds=30,
            agent_prompt_cache_key="accal-test",
            agent_prompt_cache_retention="24h",
        )
        controller = AgentController(config)
        payload = controller._build_payload(_sample_state())

        self.assertEqual(payload["agent_settings"]["model"], "gpt-5-mini")
        self.assertEqual(payload["agent_settings"]["reasoning_effort"], "minimal")
        self.assertEqual(payload["agent_settings"]["max_output_tokens"], 120)
        self.assertEqual(payload["agent_settings"]["timeout_seconds"], 30)
        self.assertEqual(payload["agent_settings"]["prompt_cache_key"], "accal-test")
        self.assertEqual(payload["agent_settings"]["prompt_cache_retention"], "24h")
        self.assertEqual(len(payload["controller_state"]["attempted_actions"]), 2)
        self.assertEqual(payload["controller_state"]["attempted_actions"][0]["retry_index"], 1)
        self.assertEqual(payload["controller_state"]["retry_index"], 1)
        self.assertAlmostEqual(payload["controller_state"]["mean_brightness"], 122.346)
        self.assertAlmostEqual(payload["controller_state"]["mean_saturation_ratio"], 0.0219)


if __name__ == "__main__":
    unittest.main()
