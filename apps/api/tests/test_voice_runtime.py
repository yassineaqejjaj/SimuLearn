"""Runtime vocal piloté par des événements scriptés au format documenté GPT-Live (pas d'appel réseau)."""
import asyncio
import uuid

import httpx
import pytest
from sqlalchemy import select

from app import models as m
from app.config import get_settings
from app.db import session_scope
from app.providers.base import ProviderError, ProviderNotConfigured, VoiceSessionConfig
from app.providers.mock import MockConnection
from app.providers.openai_live import OpenAILiveProvider
from app.runtime import SessionRuntime
from app.seed import CHARACTER, SCENARIO


def _make_session():
    with session_scope() as db:
        sv = db.scalar(select(m.ScenarioVersion))
        org = db.scalar(select(m.Organization))
        u = m.User(email=f"{uuid.uuid4().hex[:6]}@t.test")
        db.add(u)
        db.flush()
        s = m.SimulationSession(id=uuid.uuid4(), organization_id=org.id, user_id=u.id, scenario_version_id=sv.id,
                                provider="mock", max_duration_seconds=900, status="CONNECTING")
        db.add(s)
        db.commit()
        return s.id


def _delta(kind, text, a, b):
    return {"type": f"session.{kind}_transcript.delta", "delta": text, "start_ms": a, "end_ms": b}


async def _run(events, *, max_duration=900, finalize_by_close=True):
    sid = _make_session()
    conn = MockConnection()
    done = []

    async def on_final(i):
        done.append(i)

    rt = SessionRuntime(sid, conn, get_settings(), SCENARIO["emotion_rules"], dict(CHARACTER["initial_state"]), max_duration, on_final)
    rt.start()
    for ev in events:
        conn.push(ev)
    await asyncio.sleep(0.2)
    if finalize_by_close:
        await rt.end("manual")
    else:
        await conn.close()  # coupure sans session.closed
        await asyncio.wait_for(rt.finalized.wait(), 3)
    await asyncio.sleep(0.1)
    return sid, rt, conn, done


def _load(sid):
    with session_scope() as db:
        s = db.get(m.SimulationSession, sid)
        msgs = list(db.scalars(select(m.ConversationMessage).where(m.ConversationMessage.session_id == sid).order_by(m.ConversationMessage.start_ms)))
        ev = list(db.scalars(select(m.SimulationEvent).where(m.SimulationEvent.session_id == sid)))
        st = list(db.scalars(select(m.CharacterState).where(m.CharacterState.session_id == sid)))
        return s, msgs, ev, st


async def test_events_become_transcript_states_and_metrics(db_ready):
    events = [{"type": "session.started"},
              _delta("input", "Bonjour monsieur, ", 500, 1500), _delta("input", "je suis étudiant infirmier.", 1500, 3000),
              _delta("output", "Enfin quelqu'un !", 3600, 5000),
              _delta("input", "Je comprends que l'attente soit longue.", 5200, 7000),
              _delta("output", "Oui, c'est long.", 7500, 8500),
              {"type": "session.usage.updated", "usage": {"seconds": 12}},
              {"type": "session.usage.updated", "usage": {"seconds": 15}}]
    sid, rt, conn, done = await _run(events)
    s, msgs, ev, st = _load(sid)
    assert s.status == "COMPLETED" and s.end_reason == "manual" and done == [sid]
    assert [(x.speaker, x.text) for x in msgs][0] == ("learner", "Bonjour monsieur, je suis étudiant infirmier.")
    assert s.voice_seconds == 15  # cumulatif : dernière valeur, pas 27
    assert s.latency_metrics["reaction_ms_samples"] == 2 and s.latency_metrics["reaction_ms_avg"] is not None
    assert any(e["type"] == "session.thinking.append" and e["delegation_id"] is None for e in conn.sent)
    assert any(e["type"] == "session.close" for e in conn.sent)
    assert len(st) >= 1


async def test_interruption_recorded_and_character_marked_uncertain(db_ready):
    events = [{"type": "session.started"}, _delta("output", "Je voudrais vous expliquer que depuis une heure", 1000, 6000),
              _delta("input", "Excusez-moi, un instant", 3000, 4500), _delta("input", "d'accord", 7000, 7500)]
    sid, rt, conn, _ = await _run(events)
    s, msgs, ev, _ = _load(sid)
    assert any(e.type == "interruption" for e in ev) and s.latency_metrics["interruptions"] == 1
    assert next(x for x in msgs if x.speaker == "character").reliability == "uncertain"


async def test_delegation_receives_reply_with_same_id_and_no_claude_call(db_ready):
    events = [{"type": "session.started"}, {"type": "session.delegation.created", "delegation": {"id": "item_1", "type": "delegation", "target": "client"}}]
    sid, rt, conn, _ = await _run(events)
    assert any(e["type"] == "session.thinking.append" and e["delegation_id"] == "item_1" for e in conn.sent)


async def test_connection_lost_marks_transcript_incomplete(db_ready):
    events = [{"type": "session.started"}, _delta("input", "Bonjour monsieur Laurent", 500, 2000)]
    sid, rt, conn, done = await _run(events, finalize_by_close=False)
    s, msgs, ev, _ = _load(sid)
    assert s.transcript_complete is False and msgs[-1].reliability == "incomplete"
    assert s.status == "COMPLETED"  # la parole existe : évaluable avec avertissement


async def test_connection_lost_without_speech_fails(db_ready):
    sid, rt, conn, done = await _run([{"type": "session.started"}], finalize_by_close=False)
    assert _load(sid)[0].status == "FAILED" and not done


async def test_max_duration_forces_end(db_ready):
    sid = _make_session()
    conn = MockConnection()
    rt = SessionRuntime(sid, conn, get_settings(), SCENARIO["emotion_rules"], dict(CHARACTER["initial_state"]), 1)
    rt.start()
    conn.push({"type": "session.started"})
    await asyncio.wait_for(rt.finalized.wait(), 5)
    s, *_ = _load(sid)
    assert s.end_reason == "max_duration" and s.status in ("COMPLETED", "FAILED")


async def test_cost_limit_stops_session(db_ready, monkeypatch):
    monkeypatch.setattr(get_settings(), "max_session_estimated_cost_usd", 0.01)
    sid = _make_session()
    conn = MockConnection()
    rt = SessionRuntime(sid, conn, get_settings(), SCENARIO["emotion_rules"], dict(CHARACTER["initial_state"]), 900)
    rt.start()
    conn.push({"type": "session.started"})
    conn.push({"type": "session.usage.updated", "usage": {"seconds": 600}})
    await asyncio.wait_for(rt.finalized.wait(), 5)
    assert _load(sid)[0].end_reason == "cost_limit"


# ---- fournisseur OpenAI : requête HTTP (transport simulé, aucun réseau) -------------------------
def _provider(handler, monkeypatch, key="sk-test"):
    real = httpx.AsyncClient
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kw: real(transport=httpx.MockTransport(handler), **kw))
    s = get_settings().model_copy(update={"openai_api_key": key})
    return OpenAILiveProvider(s)


CFG = VoiceSessionConfig(model="gpt-live-1", voice="sillage", instructions="Tu es Marc.")


async def test_openai_session_request_shape(monkeypatch):
    seen = {}

    def handler(req: httpx.Request):
        import json
        seen.update(url=str(req.url), auth=req.headers["authorization"], body=json.loads(req.content))
        return httpx.Response(201, json={"session": {"id": "live_abc"}, "transport": {"type": "webrtc", "sdp": "ANSWER"}})

    start = await _provider(handler, monkeypatch).start_session(CFG, "OFFER")
    assert seen["url"].endswith("/v1/live/sessions") and seen["auth"] == "Bearer sk-test"
    b = seen["body"]
    assert b["transport"] == {"type": "webrtc", "sdp": "OFFER"}
    assert b["session"]["model"] == "gpt-live-1" and b["session"]["audio"]["output"]["voice"] == "sillage"
    assert b["session"]["delegation"] == {"type": "client"}
    assert (start.provider_session_id, start.answer_sdp) == ("live_abc", "ANSWER")


async def test_openai_error_does_not_leak_body(monkeypatch):
    p = _provider(lambda r: httpx.Response(400, json={"error": {"code": "invalid_voice", "message": "SECRET INSTRUCTIONS"}}), monkeypatch)
    with pytest.raises(ProviderError) as e:
        await p.start_session(CFG, "OFFER")
    assert "invalid_voice" in str(e.value) and "SECRET" not in str(e.value)


async def test_openai_missing_key_is_explicit():
    s = get_settings().model_copy(update={"openai_api_key": ""})
    with pytest.raises(ProviderNotConfigured) as e:
        await OpenAILiveProvider(s).start_session(CFG, "OFFER")
    assert "OPENAI_API_KEY" in str(e.value)
