import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models as m
from app.auth import Principal, current_principal
from app.db import get_db

router = APIRouter(prefix="/api", tags=["evaluations"])


def _eval_for(db: Session, eid: uuid.UUID, p: Principal) -> m.Evaluation:
    ev = db.get(m.Evaluation, eid)
    s = db.get(m.SimulationSession, ev.session_id) if ev else None
    if not ev or s.organization_id != p.organization_id or (s.user_id != p.user.id and not p.is_trainer):
        raise HTTPException(404, "Évaluation introuvable.")
    return ev


def effective_scores(db: Session, ev: m.Evaluation) -> dict[str, int | None]:
    """Score Claude, remplacé par la correction du formateur s'il existe (la sortie initiale reste intacte)."""
    fixes = {r.competency_key: r.corrected_score for r in db.scalars(
        select(m.TrainerReview).where(m.TrainerReview.evaluation_id == ev.id, m.TrainerReview.competency_key.is_not(None),
                                      m.TrainerReview.corrected_score.is_not(None)).order_by(m.TrainerReview.created_at))}
    return {s.competency_key: fixes.get(s.competency_key, s.score) for s in ev.scores}


def compare_scores(a: dict, b: dict, labels: dict[str, str]) -> list[dict]:
    out = []
    for key, label in labels.items():
        x, y = a.get(key), b.get(key)
        if x is None or y is None:
            verdict, delta = "not_comparable", None
        else:
            delta = y - x
            verdict = "improved" if delta > 0 else "declined" if delta < 0 else "stable"
        out.append({"competency_id": key, "label": label, "before": x, "after": y, "delta": delta, "verdict": verdict})
    return out


@router.get("/compare")
def compare(a: uuid.UUID, b: uuid.UUID, p: Principal = Depends(current_principal), db: Session = Depends(get_db)):
    """Compare deux évaluations d'un même apprenant sur la MÊME version de grille."""
    ea, eb = _eval_for(db, a, p), _eval_for(db, b, p)
    if ea.framework_id != eb.framework_id:
        raise HTTPException(422, "Grilles incompatibles : la comparaison directe des scores est impossible.")
    fw = db.get(m.CompetencyFramework, ea.framework_id)
    labels = {c.key: c.label for c in fw.competencies}
    rows = compare_scores(effective_scores(db, ea), effective_scores(db, eb), labels)
    sa, sb = (db.get(m.SimulationSession, e.session_id) for e in (ea, eb))
    return {
        "framework": {"key": fw.key, "version": fw.version},
        "before": {"evaluation_id": str(ea.id), "session_id": str(sa.id), "date": sa.created_at.isoformat(), "scenario_version": sa.scenario_version.version},
        "after": {"evaluation_id": str(eb.id), "session_id": str(sb.id), "date": sb.created_at.isoformat(), "scenario_version": sb.scenario_version.version},
        "competencies": rows,
        "improved": [r["label"] for r in rows if r["verdict"] == "improved"],
        "to_work_on": [r["label"] for r in rows if r["verdict"] in ("declined", "stable") and (r["after"] or 0) < 4],
        "note": "Les scores ne sont pas comparables si une compétence n'était pas observable dans l'une des tentatives.",
    }
