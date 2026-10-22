"""Export et suppression des données de l'utilisateur (RGPD) + purge de rétention."""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app import models as m
from app.auth import Principal, current_principal
from app.config import Settings, get_settings
from app.db import get_db

router = APIRouter(prefix="/api/me", tags=["privacy"])


def delete_session_content(db: Session, session_ids: list) -> None:
    """Supprime transcription, évaluations et états. Conserve les métriques d'usage agrégées (sans contenu)."""
    if not session_ids:
        return
    eval_ids = list(db.scalars(select(m.Evaluation.id).where(m.Evaluation.session_id.in_(session_ids))))
    score_ids = list(db.scalars(select(m.EvaluationScore.id).where(m.EvaluationScore.evaluation_id.in_(eval_ids)))) if eval_ids else []
    if score_ids:
        db.execute(delete(m.EvaluationEvidence).where(m.EvaluationEvidence.score_id.in_(score_ids)))
        db.execute(delete(m.EvaluationScore).where(m.EvaluationScore.id.in_(score_ids)))
    if eval_ids:
        db.execute(delete(m.TrainerReview).where(m.TrainerReview.evaluation_id.in_(eval_ids)))
        db.execute(delete(m.Evaluation).where(m.Evaluation.id.in_(eval_ids)))
    for model in (m.ConversationFragment, m.ConversationMessage, m.CharacterState, m.SimulationEvent):
        db.execute(delete(model).where(model.session_id.in_(session_ids)))


@router.get("")
def me(p: Principal = Depends(current_principal), db: Session = Depends(get_db)):
    org = db.get(m.Organization, p.organization_id)
    return {"email": p.user.email, "display_name": p.user.display_name, "role": p.role, "organization": org.name}


@router.get("/export")
def export_data(p: Principal = Depends(current_principal), db: Session = Depends(get_db)):
    sessions = list(db.scalars(select(m.SimulationSession).where(m.SimulationSession.user_id == p.user.id)))
    out = []
    for s in sessions:
        msgs = db.scalars(select(m.ConversationMessage).where(m.ConversationMessage.session_id == s.id).order_by(m.ConversationMessage.start_ms))
        evs = db.scalars(select(m.Evaluation).where(m.Evaluation.session_id == s.id))
        out.append({"session_id": str(s.id), "created_at": s.created_at.isoformat(), "status": s.status,
                    "messages": [{"speaker": x.speaker, "text": x.text, "start_ms": x.start_ms} for x in msgs],
                    "evaluations": [{"status": e.status, "overall_feedback": e.overall_feedback,
                                     "scores": {x.competency_key: x.score for x in e.scores}} for e in evs]})
    return {"user": {"email": p.user.email, "name": p.user.display_name}, "sessions": out}


@router.delete("/data", status_code=204)
def delete_my_data(p: Principal = Depends(current_principal), db: Session = Depends(get_db)):
    ids = list(db.scalars(select(m.SimulationSession.id).where(m.SimulationSession.user_id == p.user.id)))
    delete_session_content(db, ids)
    db.add(m.AuditLog(organization_id=p.organization_id, actor_id=p.user.id, action="privacy.delete_my_data",
                      detail={"sessions": len(ids)}))
    db.commit()


def purge_expired(db: Session, settings: Settings) -> int:
    """À appeler périodiquement (cron/Valkey) : supprime les contenus plus vieux que la rétention configurée."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=settings.transcript_retention_days)
    ids = list(db.scalars(select(m.SimulationSession.id).where(m.SimulationSession.created_at < cutoff)))
    delete_session_content(db, ids)
    db.commit()
    return len(ids)
