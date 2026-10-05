"""Per-skill reasoning mode overrides the process default without exposing reasoning."""
import pytest
from types import SimpleNamespace

from app.domains.skills import runtime
from app.domains.skills.definitions import default_skill_specification, validate_skill_specification


@pytest.mark.asyncio
@pytest.mark.parametrize("default, override, expected", [(False, None, False), (False, True, True), (True, False, False)])
async def test_gateway_uses_frozen_skill_thinking_policy(monkeypatch, default, override, expected):
    bodies = []

    class Client:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def post(self, url, *, json, headers):
            bodies.append(json)
            return Response()

    class Response:
        def raise_for_status(self):
            pass

        def json(self):
            return {"choices": [{"finish_reason": "stop", "message": {"content": '{"ok": true}',
                "reasoning_content": "private reasoning must not be logged"}}], "usage": {}, "id": "synthetic"}

    monkeypatch.setattr(runtime.httpx, "AsyncClient", Client)
    monkeypatch.setattr(runtime.settings, "DEEPSEEK_THINKING", default)
    monkeypatch.setattr(runtime.settings, "DEEPSEEK_API_KEY", "synthetic-test-key")
    policy = {} if override is None else {"thinking": override}
    if override is True:
        policy["max_tokens"] = 32768
    result = await runtime.DeepSeekGateway().complete(system_prompt="fixture", user_prompt="{}", model_policy=policy)
    assert bodies[0]["thinking"]["type"] == ("enabled" if expected else "disabled")
    assert bodies[0]["max_tokens"] == (32768 if override is True else 8000)
    assert result.trace["thinking_enabled"] is expected
    assert result.content == '{"ok": true}' and "private reasoning" not in str(result.trace)


def test_thinking_policy_rejects_nonboolean_values():
    spec = default_skill_specification()
    spec["model_policy"]["thinking"] = "false"
    with pytest.raises(ValueError, match="skill_model_policy_invalid"):
        validate_skill_specification(spec)


@pytest.mark.parametrize("thinking, tokens, valid", [(True, 32768, True), (False, 32768, False), (True, 32769, False)])
def test_reasoning_budget_is_bounded_and_opt_in(thinking, tokens, valid):
    spec = default_skill_specification()
    spec["model_policy"].update(thinking=thinking, max_tokens=tokens)
    if valid:
        assert validate_skill_specification(spec)["model_policy"]["max_tokens"] == tokens
    else:
        with pytest.raises(ValueError, match="skill_model_policy_invalid"):
            validate_skill_specification(spec)


@pytest.mark.asyncio
@pytest.mark.parametrize("finish_reason, code", [("length", "skill_output_truncated"), ("stop", "skill_provider_response_invalid")])
async def test_empty_provider_body_keeps_finish_reason_and_usage_without_reasoning(monkeypatch, finish_reason, code):
    class Response:
        def raise_for_status(self):
            pass

        def json(self):
            return {"id": "synthetic-empty", "usage": {"prompt_tokens": 100, "completion_tokens": 16000},
                "choices": [{"finish_reason": finish_reason, "message": {"content": "",
                    "reasoning_content": "private reasoning must not be logged"}}]}

    class Client:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def post(self, *args, **kwargs):
            return Response()

    from app.domains.calendar.skill_definitions import default_calendar_skill_specifications
    specification = default_calendar_skill_specifications()[-1][1]
    skill = SimpleNamespace(id=123, version=1, skill_key="calendar.calibration", specification_json=specification)
    monkeypatch.setattr(runtime.httpx, "AsyncClient", Client)
    with pytest.raises(runtime.SkillExecutionError, match=code) as caught:
        await runtime.execute_skill(skill_version=skill, input_data={})
    trace = caught.value.model_trace
    assert trace["finish_reason"] == finish_reason and trace["output_tokens"] == 16000
    assert trace["thinking_enabled"] is True and trace["skill_key"] == "calendar.calibration"
    assert trace["request_id"] == "synthetic-empty" and trace["prompt_sha256"]
    assert caught.value.output_raw == "" and "private reasoning" not in str(trace)
