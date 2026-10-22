"""Runtime d'une session vocale : consomme les événements fournisseur (sideband), tient l'état métier.

Les événements traités sont ceux documentés par OpenAI (voir docs/voice-integration.md) :
session.started, session.input_transcript.delta, session.output_transcript.delta,
session.usage.updated, session.delegation.created, session.closed, error.
Aucun état n'est simulé par délai : tout changement d'état provient d'un événement réel.
"""
import asyncio
import time
import uuid
from datetime import datetime, timezone

import structlog
from sqlalchemy import delete, select

from app import models as m
from app import pricing
from app.config import Settings
from app.db import session_scope
from app.emotion import EmotionManager, detect_signals
from app.providers.base import VoiceConnection
from app.transcript import Fragment, group_fragments

log = structlog.get_logger()
TERMINAL = {m.SessionStatus.COMPLETED.value, m.SessionStatus.FAILED.value}
CLOSE_TIMEOUT_S = 10

_registry: dict[uuid.UUID, "SessionRuntime"] = {}


def get_runtime(session_id: uuid.UUID) -> "SessionRuntime | None":
    return _registry.get(session_id)


def _now() -> datetime:
    return datetime.now(timezone.utc)


class SessionRuntime:
    def __init__(self, session_id: uuid.UUID, conn: VoiceConnection, settings: Settings, rules: dict, initial_state: dict,
                 max_duration_s: int, on_finalized=None):
        self.id = session_id
        self.conn = conn
        self.settings = settings
        self.emotion = EmotionManager(rules=rules, state=dict(initial_state))
        self.max_duration_s = max_duration_s
        self.on_finalized = on_finalized
        self.seq = 0
        self.t_created = time.monotonic()
        self.pending_learner = ""
        self.pending_learner_end = 0
        self.last_character_end = 0
        self.last_learner_end = 0
        self.reaction_ms: list[int] = []
        self.interruptions = 0
        self.voice_seconds: float | None = None
        self.finalized = asyncio.Event()
        self._ending = False
        self._tasks: list[asyncio.Task] = []
        self._connect_ms: int | None = None
        self._saw_learner = False

    # ---- cycle de vie -------------------------------------------------
    def start(self) -> None:
        _registry[self.id] = self
        self._tasks = [asyncio.create_task(self._consume()), asyncio.create_task(self._max_duration_timer())]

    async def _consume(self) -> None:
        try:
            async for ev in self.conn.events():
                await self.handle(ev)
                if self.finalized.is_set():
                    return
        except Exception:  # noqa: BLE001 - toute rupture doit finaliser la session
            log.exception("runtime_consume_failed", session_id=str(self.id))
        if not self.finalized.is_set():
            await self.finalize("connection_lost", truncated=True)

    async def _max_duration_timer(self) -> None:
        await asyncio.sleep(self.max_duration_s)
        await self.end("max_duration")

    async def end(self, reason: str) -> None:
        if self.finalized.is_set() or self._ending:
            await self.finalized.wait()
            return
        self._ending = True
        self._set_status(m.SessionStatus.ENDING, reason=reason)
        try:
            await self.conn.send({"type": "session.close", "event_id": f"close_{uuid.uuid4().hex[:8]}"})
            await asyncio.wait_for(self.finalized.wait(), CLOSE_TIMEOUT_S)
        except (asyncio.TimeoutError, Exception):  # noqa: BLE001
            # session.closed non reçu : on le consigne, la transcription est marquée possiblement incomplète
            await self.finalize(reason, truncated=True)
        finally:
            await self._safe_close()

    async def _safe_close(self) -> None:
        try:
            await self.conn.close()
        except Exception:  # noqa: BLE001
            pass

    # ---- gestion des événements ----------------------------------------
    async def handle(self, ev: dict) -> None:
        t = ev.get("type", "")
        if t == "session.started":
            self._connect_ms = int((time.monotonic() - self.t_created) * 1000)
            self._set_status(m.SessionStatus.READY)
            self._event("provider.session_started", {"connect_ms": self._connect_ms})
        elif t == "session.input_transcript.delta":
            await self._on_delta("learner", ev)
        elif t == "session.output_transcript.delta":
            await self._on_delta("character", ev)
        elif t == "session.usage.updated":
            # cumulatif : on retient la dernière valeur, on n'additionne jamais
            self.voice_seconds = float(ev.get("usage", {}).get("seconds", 0))
            await self._check_cost_limit()
        elif t == "session.delegation.created":
            await self._on_delegation(ev)
        elif t == "session.closed":
            reason = ev.get("reason", "unknown")
            sec = ev.get("usage", {}).get("seconds")
            if sec is not None:
                self.voice_seconds = float(sec)
            await self.finalize(reason, truncated=reason == "connection_lost")
        elif t == "error":
            err = ev.get("error", {})
            self._event("provider.error", {"code": err.get("code"), "param": err.get("param")})

    async def _on_delta(self, speaker: str, ev: dict) -> None:
        text = ev.get("delta", "")
        start, end = int(ev.get("start_ms", 0)), int(ev.get("end_ms", 0))
        self.seq += 1
        with session_scope() as db:
            db.add(m.ConversationFragment(session_id=self.id, speaker=speaker, text=text, start_ms=start, end_ms=end, seq=self.seq))
            sess = db.get(m.SimulationSession, self.id)
            if speaker == "learner" and sess.status in (m.SessionStatus.READY.value, m.SessionStatus.CREATED.value,
                                                       m.SessionStatus.CONNECTING.value):
                sess.status, sess.started_at = m.SessionStatus.ACTIVE.value, sess.started_at or _now()
            db.commit()
        if speaker == "learner":
            self._saw_learner = True
            if start < self.last_character_end:  # prise de parole pendant que le patient parle
                self.interruptions += 1
                self._event("interruption", {"learner_start_ms": start, "character_end_ms": self.last_character_end}, start)
            self.pending_learner += text
            self.pending_learner_end = max(self.pending_learner_end, end)
            self.last_learner_end = max(self.last_learner_end, end)
        else:
            if self.pending_learner:
                await self._flush_learner_turn(start)
                if self.last_learner_end:
                    self.reaction_ms.append(max(0, start - self.last_learner_end))
            self.last_character_end = max(self.last_character_end, end)

    async def _flush_learner_turn(self, offset_ms: int) -> None:
        text, self.pending_learner = self.pending_learner, ""
        signals = detect_signals(text)
        if not signals:
            return
        entry = self.emotion.apply(signals, offset_ms)
        if entry:
            with session_scope() as db:
                db.add(m.CharacterState(session_id=self.id, state=entry["state"], cause=entry["cause"], offset_ms=offset_ms))
                db.commit()
            # Contexte silencieux (thinking.append) : n'interrompt pas la parole en cours.
            await self.conn.send({"type": "session.thinking.append", "event_id": f"emo_{uuid.uuid4().hex[:8]}",
                                  "delegation_id": None, "content": self.emotion.guidance_line()})

    async def _on_delegation(self, ev: dict) -> None:
        did = ev.get("delegation", {}).get("id")
        self._event("delegation.created", {"delegation_id": did})
        # Claude n'est pas appelé pendant la conversation sauf activation explicite (non implémentée dans ce MVP).
        await self.conn.send({
            "type": "session.thinking.append", "event_id": f"deleg_{uuid.uuid4().hex[:8]}", "delegation_id": did,
            "content": "Aucune information supplémentaire disponible. Reste Marc, le patient, et réponds avec ce que tu sais.",
        })

    async def _check_cost_limit(self) -> None:
        if self.voice_seconds is None:
            return
        cost = pricing.voice_cost_usd(self.voice_seconds)
        if cost is not None and cost >= self.settings.max_session_estimated_cost_usd and not self._ending:
            asyncio.create_task(self.end("cost_limit"))

    # ---- persistance ----------------------------------------------------
    def _set_status(self, status: m.SessionStatus, reason: str | None = None) -> None:
        with session_scope() as db:
            sess = db.get(m.SimulationSession, self.id)
            if sess.status in TERMINAL:
                return
            sess.status = status.value
            if reason:
                sess.end_reason = reason
            db.commit()

    def _event(self, type_: str, payload: dict, offset_ms: int | None = None) -> None:
        with session_scope() as db:
            db.add(m.SimulationEvent(session_id=self.id, type=type_, payload=payload, offset_ms=offset_ms))
            db.commit()

    async def finalize(self, reason: str, truncated: bool = False) -> None:
        if self.finalized.is_set():
            return
        self.finalized.set()
        if self.pending_learner:
            await self._flush_learner_turn(self.pending_learner_end)
        with session_scope() as db:
            sess = db.get(m.SimulationSession, self.id)
            frags = [Fragment(f.speaker, f.text, f.start_ms, f.end_ms, f.seq) for f in db.scalars(
                select(m.ConversationFragment).where(m.ConversationFragment.session_id == self.id))]
            db.execute(delete(m.ConversationMessage).where(m.ConversationMessage.session_id == self.id))
            for g in group_fragments(frags, truncated):
                db.add(m.ConversationMessage(session_id=self.id, speaker=g.speaker, text=g.text, start_ms=g.start_ms,
                                             end_ms=g.end_ms, reliability=g.reliability, reliability_note=g.note))
            if not (self._ending and sess.end_reason):  # la raison choisie à la demande de fin prime
                sess.end_reason = reason
            sess.ended_at = _now()
            sess.transcript_complete = not truncated
            sess.voice_seconds = self.voice_seconds
            sess.latency_metrics = {
                "connect_ms": self._connect_ms,
                "reaction_ms_avg": int(sum(self.reaction_ms) / len(self.reaction_ms)) if self.reaction_ms else None,
                "reaction_ms_samples": len(self.reaction_ms),
                "interruptions": self.interruptions,
            }
            had_learner = self._saw_learner
            sess.status = (m.SessionStatus.COMPLETED if had_learner or reason != "connection_lost" else m.SessionStatus.FAILED).value
            if self.settings.enable_usage_tracking and self.voice_seconds is not None:
                db.add(m.UsageMetric(session_id=self.id, organization_id=sess.organization_id, provider="openai_live",
                                     kind="voice", quantities={"seconds": self.voice_seconds},
                                     estimated_cost_usd=pricing.voice_cost_usd(self.voice_seconds),
                                     pricing_version=pricing.pricing_version()))
            db.commit()
            status = sess.status
        for t in self._tasks:
            if t is not asyncio.current_task():
                t.cancel()
        _registry.pop(self.id, None)
        if self.on_finalized and status == m.SessionStatus.COMPLETED.value:
            asyncio.create_task(self.on_finalized(self.id))
