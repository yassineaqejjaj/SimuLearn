import uuid
from types import SimpleNamespace

import pytest
from sqlalchemy import select

from app import models as m
from app.config import get_settings
from app.db import session_scope
from app.evaluation_service import run_evaluation
from app.providers.base import EvaluationResponse, ProviderError
from app.providers.claude_eval import ClaudeEvaluationProvider

KEYS = ["welcome_quality", "active_listening", "empathy", "clarity", "conflict_handling", "professionalism", "conclusion"]


def make_session(complete=True, learner=True):
    with session_scope() as db:
        sv, org = db.scalar(select(m.ScenarioVersion)), db.scalar(select(m.Organization))
        u = m.User(email=f"{uuid.uuid4().hex[:6]}@t.test")
        db.add(u)
        db.flush()
        s = m.SimulationSession(id=uuid.uuid4(), organization_id=org.id, user_id=u.id, scenario_version_id=sv.id, provider="mock",
                                max_duration_seconds=900, status="COMPLETED", transcript_complete=complete)
        db.add(s)
        db.flush()
        ids = {}
        rows = [("character", "Ça fait une heure que j'attends !", 0, 3000)]
        if learner:
            rows += [("learner", "Je comprends que cette attente vous inquiète, monsieur Laurent.", 3500, 6000)]
        for i, (sp, tx, a, b) in enumerate(rows):
            msg = m.ConversationMessage(id=uuid.uuid4(), session_id=s.id, speaker=sp, text=tx, start_ms=a, end_ms=b)
            db.add(msg)
            ids[i] = str(msg.id)
        db.commit()
        return s.id, ids


def good(ids, **over):
    comps = [{"competency_id": k, "observable": False, "score": None} for k in KEYS]
    comps[2] = {"competency_id": "empathy", "observable": True, "score": 4, "confidence": 0.8, "justification": "ok",
                "evidence": [{"message_id": ids[1], "speaker": "learner", "quote": "Je comprends que cette attente vous inquiète"}]}
    data = {"competencies": comps, "overall_feedback": {"summary": "Bien."}}
    data.update(over)
    return data


class Fake:
    name = "fake"

    def __init__(self, *responses):
        self.responses, self.calls = list(responses), []

    async def evaluate(self, req):
        self.calls.append(req)
        r = self.responses.pop(0)
        if isinstance(r, Exception):
            raise r
        return EvaluationResponse(data=r, model="claude-sonnet-5-5", usage={"input_tokens": 1000, "output_tokens": 500})


async def run(provider, **kw):
    sid, ids = make_session(**kw)
    with session_scope() as db:
        ev = await run_evaluation(db, provider, sid)
        scores = {s.competency_key: s for s in ev.scores}
        return ev, scores, ids, sid


async def test_valid_evaluation_with_not_observable_and_cost(db_ready):
    sid, ids = make_session()
    fake = Fake(good(ids))
    with session_scope() as db:
        ev = await run_evaluation(db, fake, sid)
        sc = {s.competency_key: s for s in ev.scores}
        assert ev.status == "completed" and sc["empathy"].score == 4 and sc["empathy"].evidence[0].start_ms == 3500
        assert sc["clarity"].score is None and sc["clarity"].status == "not_observable"
        assert db.scalar(select(m.UsageMetric).where(m.UsageMetric.kind == "evaluation")).quantities["input_tokens"] == 1000
    assert fake.calls[0].payload["messages"][0]["message_id"] == ids[0]


async def test_invented_quote_removes_score_and_warns(db_ready):
    sid, ids = make_session()
    bad = good(ids)
    bad["competencies"][2]["evidence"][0]["quote"] = "Je vous garantis que vous passerez dans cinq minutes"
    with session_scope() as db:
        ev = await run_evaluation(db, Fake(bad), sid)
        sc = {s.competency_key: s for s in ev.scores}
        assert sc["empathy"].score is None and sc["empathy"].status == "not_observable"
        assert ev.status == "completed_with_warnings" and any("preuve_rejetee:empathy" in w for w in ev.warnings)
        assert not sc["empathy"].evidence


async def test_wrong_speaker_or_unknown_message_rejected(db_ready):
    sid, ids = make_session()
    d1, d2 = good(ids), good(ids)
    d1["competencies"][2]["evidence"][0]["speaker"] = "character"
    d2["competencies"][2]["evidence"][0]["message_id"] = str(uuid.uuid4())
    for d, reason in ((d1, "locuteur_incorrect"), (d2, "message_inconnu")):
        with session_scope() as db:
            ev = await run_evaluation(db, Fake(d), sid)
            assert any(reason in w for w in ev.warnings)


async def test_retry_after_invalid_json_then_success(db_ready):
    sid, ids = make_session()
    broken = {"competencies": [{"competency_id": "empathy", "observable": True, "score": None}], "overall_feedback": {"summary": "x"}}
    fake = Fake(broken, ProviderError("boom"), good(ids))
    with session_scope() as db:
        ev = await run_evaluation(db, fake, sid)
        assert ev.status == "completed" and ev.attempts == 3
    assert "previous_attempt_error" in fake.calls[1].payload  # l'erreur est renvoyée pour corriger


async def test_all_attempts_fail_is_reported_not_silent(db_ready):
    sid, _ = make_session()
    with session_scope() as db:
        ev = await run_evaluation(db, Fake(ProviderError("a"), ProviderError("b"), ProviderError("c")), sid)
        assert ev.status == "failed" and ev.error and ev.attempts == 3 and not ev.scores


async def test_partial_response_flags_missing_competencies(db_ready):
    sid, ids = make_session()
    partial = good(ids)
    partial["competencies"] = partial["competencies"][:3]
    with session_scope() as db:
        ev = await run_evaluation(db, Fake(partial), sid)
        assert sum("competence_absente" in w for w in ev.warnings) == 4
        assert len(ev.scores) == 7  # toutes les compétences existent, les absentes sont not_observable


async def test_no_learner_speech_skips_claude(db_ready):
    sid, _ = make_session(learner=False)
    fake = Fake()
    with session_scope() as db:
        ev = await run_evaluation(db, fake, sid)
        assert ev.status == "failed" and fake.calls == []


async def test_incomplete_transcript_is_flagged(db_ready):
    sid, ids = make_session(complete=False)
    fake = Fake(good(ids))
    with session_scope() as db:
        ev = await run_evaluation(db, fake, sid)
        assert "transcript_incomplete" in ev.warnings and fake.calls[0].payload["transcript_limits"]


def test_score_must_be_null_when_not_observable():
    from pydantic import ValidationError
    from app.evaluation_schema import CompetencyResult
    with pytest.raises(ValidationError):
        CompetencyResult(competency_id="x", observable=False, score=3)
    with pytest.raises(ValidationError):
        CompetencyResult(competency_id="x", observable=True, score=6)


def test_pricing_unknown_rate_gives_none_not_invented_cost():
    from app import pricing
    assert pricing.llm_cost_usd("claude-sonnet-5-5", {"input_tokens": 1000, "output_tokens": 10}) is None
    assert pricing.voice_cost_usd(60) == 0.05  # tarif lu dans config/pricing.json


async def test_claude_provider_uses_forced_tool_and_reads_usage(monkeypatch):
    import anthropic
    captured = {}

    class FakeMessages:
        async def create(self, **kw):
            captured.update(kw)
            return SimpleNamespace(content=[SimpleNamespace(type="tool_use", name="submit_evaluation", input={"ok": 1})],
                                   usage=SimpleNamespace(input_tokens=11, output_tokens=7, cache_read_input_tokens=3))

    monkeypatch.setattr(anthropic, "AsyncAnthropic", lambda **kw: SimpleNamespace(messages=FakeMessages()))
    s = get_settings().model_copy(update={"anthropic_api_key": "k"})
    from app.providers.base import EvaluationRequest
    r = await ClaudeEvaluationProvider(s).evaluate(EvaluationRequest("sys", {"a": 1}, {"type": "object"}))
    assert captured["model"] == "claude-sonnet-5-5" and captured["tool_choice"] == {"type": "tool", "name": "submit_evaluation"}
    assert r.data == {"ok": 1} and r.usage["input_tokens"] == 11 and r.usage["cache_read_input_tokens"] == 3


async def test_claude_provider_missing_key_explicit():
    from app.providers.base import EvaluationRequest, ProviderNotConfigured
    s = get_settings().model_copy(update={"anthropic_api_key": ""})
    with pytest.raises(ProviderNotConfigured, match="ANTHROPIC_API_KEY"):
        await ClaudeEvaluationProvider(s).evaluate(EvaluationRequest("s", {}, {}))
