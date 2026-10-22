import asyncio
import time
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import models as m
from app.auth import Principal, current_principal
from app.config import Settings, get_settings
from app.db import get_db, session_scope
from app.deps import get_evaluation_provider, get_voice_provider
from app.evaluation_service import run_evaluation
from app.prompts import build_character_instructions
from app.providers.base import ProviderError, ProviderNotConfigured, VoiceSessionConfig
from app.runtime import SessionRuntime, get_runtime
from app.serializers import evaluation_public, session_public

router = APIRouter(prefix="/api/simulations", tags=["simulations"])
ACTIVE = (m.SessionStatus.CREATED.value, m.SessionStatus.CONNECTING.value, m.SessionStatus.READY.value,
          m.SessionStatus.ACTIVE.value, m.SessionStatus.PAUSED.value, m.SessionStatus.ENDING.value)


class CreateIn(BaseModel):
    scenario_version_id: uuid.UUID


class ConnectIn(BaseModel):
    sdp: str | None = Field(default=None, max_length=100_000)


class ClientEventIn(BaseModel):
    type: str = Field(pattern=r"^client\.(mic_muted|mic_unmuted|connection_state|ice_state|error)$")
    detail: dict = {}


class MockTurnIn(BaseModel):
    text: str = Field(min_length=1, max_length=2000)


def _own_session(db: Session, sid: uuid.UUID, p: Principal) -> m.SimulationSession:
    s = db.get(m.SimulationSession, sid)
    if s is None or s.organization_id != p.organization_id or (s.user_id != p.user.id and not p.is_trainer):
        raise HTTPException(404, "Session introuvable.")  # 404 : ne révèle pas l'existence
    return s


def _audit(db: Session, p: Principal, action: str, target: str, detail: dict | None = None) -> None:
    db.add(m.AuditLog(organization_id=p.organization_id, actor_id=p.user.id, action=action, target=target, detail=detail or {}))


async def evaluate_in_background(session_id: uuid.UUID) -> None:
    with session_scope() as db:
        await run_evaluation(db, get_evaluation_provider(), session_id)


@router.post("", status_code=201)
def create(body: CreateIn, p: Principal = Depends(current_principal), db: Session = Depends(get_db),
           settings: Settings = Depends(get_settings)):
    sv = db.get(m.ScenarioVersion, body.scenario_version_id)
    scenario = db.get(m.Scenario, sv.scenario_id) if sv else None
    if not sv or scenario.organization_id != p.organization_id or not sv.published:
        raise HTTPException(404, "Scénario introuvable.")
    # Sessions abandonnées : on les referme avant de compter (évite de bloquer l'utilisateur).
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=settings.simulation_max_duration_minutes * 60 + 120)
    for stale in db.scalars(select(m.SimulationSession).where(
            m.SimulationSession.user_id == p.user.id, m.SimulationSession.status.in_(ACTIVE),
            m.SimulationSession.created_at < cutoff)):
        stale.status, stale.end_reason = m.SessionStatus.FAILED.value, "abandoned"
    db.flush()
    running = db.scalar(select(func.count()).select_from(m.SimulationSession).where(
        m.SimulationSession.user_id == p.user.id, m.SimulationSession.status.in_(ACTIVE)))
    if running >= settings.simulation_max_concurrent_per_user:
        raise HTTPException(429, "Une simulation est déjà en cours. Terminez-la avant d'en démarrer une autre.")
    month = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    org = db.get(m.Organization, p.organization_id)
    used = db.scalar(select(func.count()).select_from(m.SimulationSession).where(
        m.SimulationSession.organization_id == p.organization_id, m.SimulationSession.created_at >= month))
    if used >= min(org.monthly_session_quota, settings.org_monthly_session_quota):
        raise HTTPException(429, "Quota mensuel de simulations de l'établissement atteint.")
    s = m.SimulationSession(id=uuid.uuid4(), organization_id=p.organization_id, user_id=p.user.id, scenario_version_id=sv.id,
                            provider=settings.voice_provider, max_duration_seconds=settings.simulation_max_duration_minutes * 60)
    db.add(s)
    db.add(m.CharacterState(session_id=s.id, state=sv.character.initial_state, cause="initial", offset_ms=0))
    _audit(db, p, "simulation.create", str(s.id))
    db.commit()
    return session_public(s)


@router.post("/{sid}/connect")
async def connect(sid: uuid.UUID, body: ConnectIn, p: Principal = Depends(current_principal), db: Session = Depends(get_db),
                  settings: Settings = Depends(get_settings), voice=Depends(get_voice_provider)):
    """Reçoit l'offre SDP du navigateur, crée la session GPT-Live côté serveur, renvoie la réponse SDP."""
    s = _own_session(db, sid, p)
    if s.user_id != p.user.id or s.status != m.SessionStatus.CREATED.value:
        raise HTTPException(409, "Session déjà connectée ou terminée.")
    sv = s.scenario_version
    state = sv.character.initial_state
    cfg = VoiceSessionConfig(model=settings.openai_live_model, voice=sv.character.voice or settings.openai_live_voice,
                             instructions=build_character_instructions(sv, state))
    s.status = m.SessionStatus.CONNECTING.value
    db.commit()
    try:
        start = await voice.start_session(cfg, body.sdp)
        conn = await voice.attach(start.provider_session_id)
    except ProviderNotConfigured as exc:
        s.status, s.end_reason = m.SessionStatus.FAILED.value, "provider_not_configured"
        db.commit()
        raise HTTPException(503, f"{exc}. Renseignez la variable dans .env, ou utilisez VOICE_PROVIDER=mock (développement).")
    except Exception as exc:  # noqa: BLE001
        s.status, s.end_reason = m.SessionStatus.FAILED.value, "provider_error"
        db.add(m.SimulationEvent(session_id=s.id, type="provider.start_failed", payload={"error": type(exc).__name__}))
        db.commit()
        raise HTTPException(502, str(exc) if isinstance(exc, ProviderError) else "Échec de connexion au moteur vocal.")
    s.provider_session_id = start.provider_session_id
    db.commit()
    SessionRuntime(s.id, conn, settings, sv.emotion_rules, state, s.max_duration_seconds, on_finalized=evaluate_in_background).start()
    return {"session_id": str(s.id), "sdp": start.answer_sdp, "provider": voice.name, "max_duration_seconds": s.max_duration_seconds}


@router.post("/{sid}/client-events", status_code=204)
def client_event(sid: uuid.UUID, body: ClientEventIn, p: Principal = Depends(current_principal), db: Session = Depends(get_db)):
    """Événements d'interface (micro coupé...). Non autorisés à modifier transcription ni scores."""
    s = _own_session(db, sid, p)
    db.add(m.SimulationEvent(session_id=s.id, type=body.type, payload={k: v for k, v in list(body.detail.items())[:5]}))
    db.commit()


@router.post("/{sid}/end")
async def end(sid: uuid.UUID, p: Principal = Depends(current_principal), db: Session = Depends(get_db)):
    s = _own_session(db, sid, p)
    rt = get_runtime(s.id)
    if rt is not None:
        await rt.end("manual")
    elif s.status in ACTIVE:  # runtime perdu (redémarrage serveur) : on referme proprement
        s.status, s.end_reason, s.transcript_complete = m.SessionStatus.FAILED.value, "runtime_lost", False
        db.commit()
    _audit(db, p, "simulation.end", str(s.id), {"reason": "manual"})
    db.commit()
    db.refresh(s)
    return session_public(s)


@router.get("")
def history(p: Principal = Depends(current_principal), db: Session = Depends(get_db)):
    """Pas de note globale : chaque compétence est évaluée séparément."""
    from app.routers.evaluations import effective_scores
    rows = db.scalars(select(m.SimulationSession).where(m.SimulationSession.user_id == p.user.id)
                      .order_by(m.SimulationSession.created_at.desc()).limit(100))
    out = []
    for s in rows:
        ev = db.scalar(select(m.Evaluation).where(m.Evaluation.session_id == s.id).order_by(m.Evaluation.created_at.desc()))
        comps, dur = [], None
        if ev and ev.status in ("completed", "completed_with_warnings"):
            fw = db.get(m.CompetencyFramework, ev.framework_id)
            eff = effective_scores(db, ev)
            comps = [{"id": c.key, "label": c.label, "score": eff.get(c.key)} for c in fw.competencies]
        if s.ended_at and s.started_at:
            dur = int((s.ended_at - s.started_at).total_seconds())
        out.append({**session_public(s), "evaluation_id": str(ev.id) if ev else None, "evaluation_status": ev.status if ev else None,
                    "review_status": ev.trainer_review_status if ev else None,
                    "framework_id": str(ev.framework_id) if ev else None, "duration_s": dur, "competencies": comps})
    return out


@router.get("/{sid}")
def get_session(sid: uuid.UUID, p: Principal = Depends(current_principal), db: Session = Depends(get_db)):
    s = _own_session(db, sid, p)
    return session_public(s)


@router.get("/{sid}/messages")
def messages(sid: uuid.UUID, p: Principal = Depends(current_principal), db: Session = Depends(get_db)):
    s = _own_session(db, sid, p)
    rows = db.scalars(select(m.ConversationMessage).where(m.ConversationMessage.session_id == s.id).order_by(m.ConversationMessage.start_ms))
    return [{"id": str(x.id), "speaker": x.speaker, "text": x.text, "start_ms": x.start_ms, "end_ms": x.end_ms,
             "reliability": x.reliability, "note": x.reliability_note} for x in rows]


@router.get("/{sid}/evaluation")
def evaluation(sid: uuid.UUID, p: Principal = Depends(current_principal), db: Session = Depends(get_db)):
    s = _own_session(db, sid, p)
    ev = db.scalar(select(m.Evaluation).where(m.Evaluation.session_id == s.id).order_by(m.Evaluation.created_at.desc()))
    if ev is None:
        return {"status": "pending" if s.status not in (m.SessionStatus.FAILED.value,) else "none", "session_status": s.status}
    fw = db.get(m.CompetencyFramework, ev.framework_id)
    reviews = list(db.scalars(select(m.TrainerReview).where(m.TrainerReview.evaluation_id == ev.id).order_by(m.TrainerReview.created_at)))
    return evaluation_public(ev, fw, reviews)


@router.post("/{sid}/evaluate", status_code=202)
def reevaluate(sid: uuid.UUID, bg: BackgroundTasks, p: Principal = Depends(current_principal), db: Session = Depends(get_db)):
    """Relance l'évaluation (après un échec fournisseur). L'ancienne évaluation reste consultable."""
    s = _own_session(db, sid, p)
    if s.status != m.SessionStatus.COMPLETED.value:
        raise HTTPException(409, "La session n'est pas terminée.")
    bg.add_task(evaluate_in_background, s.id)
    return {"status": "started"}


@router.get("/{sid}/costs")
def costs(sid: uuid.UUID, p: Principal = Depends(current_principal), db: Session = Depends(get_db)):
    s = _own_session(db, sid, p)
    rows = list(db.scalars(select(m.UsageMetric).where(m.UsageMetric.session_id == s.id)))
    known = [r.estimated_cost_usd for r in rows if r.estimated_cost_usd is not None]
    errors = [e.payload for e in db.scalars(select(m.SimulationEvent).where(
        m.SimulationEvent.session_id == s.id, m.SimulationEvent.type.like("provider.%error%")))]
    dur = (s.ended_at - s.started_at).total_seconds() if s.ended_at and s.started_at else None
    return {
        "simulation_duration_s": dur, "voice_seconds": s.voice_seconds, "latency_metrics": s.latency_metrics,
        "usage": [{"provider": r.provider, "kind": r.kind, "quantities": r.quantities, "estimated_cost_usd": r.estimated_cost_usd,
                   "pricing_version": r.pricing_version} for r in rows],
        "estimated_total_cost_usd": round(sum(known), 6) if known else None,
        "cost_complete": all(r.estimated_cost_usd is not None for r in rows) if rows else False,
        "provider_errors": errors,
    }


@router.post("/{sid}/mock-turn")
async def mock_turn(sid: uuid.UUID, body: MockTurnIn, p: Principal = Depends(current_principal), db: Session = Depends(get_db),
                    settings: Settings = Depends(get_settings), voice=Depends(get_voice_provider)):
    """DÉVELOPPEMENT UNIQUEMENT (VOICE_PROVIDER=mock) : remplace la voix par du texte saisi."""
    if settings.voice_provider != "mock":
        raise HTTPException(404, "Indisponible.")
    s = _own_session(db, sid, p)
    rt = get_runtime(s.id)
    if rt is None:
        raise HTTPException(409, "Session non active.")
    conn = voice.connections[s.provider_session_id]
    t = max(int((time.monotonic() - rt.t_created) * 1000), getattr(rt, "mock_clock", 0) + 500)  # horloge virtuelle cohérente
    words = body.text
    conn.push({"type": "session.input_transcript.delta", "delta": words, "start_ms": t, "end_ms": t + 400 * max(1, len(words.split()))})
    await asyncio.sleep(0.05)
    state = rt.emotion.state
    line = {"frustrated": "Ça fait plus d'une heure que j'attends, et personne ne m'explique rien !",
            "wary": "Bon... d'accord, mais j'aimerais comprendre ce qui va se passer ensuite.",
            "calmer": "Merci de m'avoir écouté. Ça me rassure un peu."}[state["emotion"]]
    start = t + 400 * max(1, len(words.split())) + 600
    conn.push({"type": "session.output_transcript.delta", "delta": line, "start_ms": start, "end_ms": start + 3000})
    rt.mock_clock = start + 3000
    await asyncio.sleep(0.05)
    return {"character_reply": line}
