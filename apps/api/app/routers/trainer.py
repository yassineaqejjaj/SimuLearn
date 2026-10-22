import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import models as m
from app.auth import Principal, require_trainer
from app.config import get_settings
from app.db import get_db
from app.routers.simulations import _audit
from app.serializers import evaluation_public, session_public

router = APIRouter(prefix="/api/trainer", tags=["trainer"])
VOICE_CANDIDATES = [
    {"name": "sillage", "verified": False}, {"name": "brise", "verified": False}, {"name": "marin", "verified": True},
]  # `verified` = documenté ; la disponibilité des voix françaises est à tester sur le compte API


class ReviewIn(BaseModel):
    competency_key: str | None = None
    corrected_score: int | None = Field(default=None, ge=1, le=5)
    comment: str = Field(default="", max_length=2000)
    status: str | None = Field(default=None, pattern="^(pending|reviewed|corrected)$")


class CharacterIn(BaseModel):
    name: str
    age: int = Field(ge=1, le=120)
    role: str
    personality: list[str]
    background: str
    initial_attitude: str
    known_facts: list[str]
    withheld_facts: list[str] = []
    conversational_goal: str
    voice: str
    initial_state: dict


class ScenarioIn(BaseModel):
    title: str
    description: str
    target_profession: str = "Étudiant infirmier"
    category: str = Field(default="Communication patient", min_length=1, max_length=100)
    difficulty: str = "Intermédiaire"
    recommended_minutes: int = Field(default=10, ge=1, le=60)
    context: str
    learner_role: str
    objectives: list[str] = Field(min_length=1)
    behavior_rules: list[str]
    possible_events: list[dict] = []
    end_conditions: dict = {}
    emotion_rules: dict
    framework_id: uuid.UUID
    character: CharacterIn
    publish: bool = True


def _create_version(db: Session, scenario: m.Scenario, body: ScenarioIn, version: int) -> m.ScenarioVersion:
    fields = body.model_dump(exclude={"character", "publish", "framework_id"})
    sv = m.ScenarioVersion(scenario_id=scenario.id, framework_id=body.framework_id, version=version, published=body.publish, **fields)
    db.add(sv)
    db.flush()
    db.add(m.Character(scenario_version_id=sv.id, **body.character.model_dump()))
    return sv


@router.get("/voices")
def voices(_: Principal = Depends(require_trainer)):
    return {"default": get_settings().openai_live_voice, "candidates": VOICE_CANDIDATES}


@router.get("/dashboard")
def dashboard(p: Principal = Depends(require_trainer), db: Session = Depends(get_db)):
    org = p.organization_id
    n_learners = db.scalar(select(func.count()).select_from(m.Membership).where(m.Membership.organization_id == org, m.Membership.role == "learner"))
    n_sessions = db.scalar(select(func.count()).select_from(m.SimulationSession).where(m.SimulationSession.organization_id == org))
    pending = db.scalar(select(func.count()).select_from(m.Evaluation).join(m.SimulationSession).where(
        m.SimulationSession.organization_id == org, m.Evaluation.trainer_review_status == "pending"))
    return {"learners": n_learners, "sessions": n_sessions, "evaluations_to_review": pending}


@router.get("/groups")
def groups(p: Principal = Depends(require_trainer), db: Session = Depends(get_db)):
    return [{"id": str(g.id), "name": g.name, "members": db.scalar(select(func.count()).select_from(m.GroupMember).where(m.GroupMember.group_id == g.id))}
            for g in db.scalars(select(m.Group).where(m.Group.organization_id == p.organization_id))]


@router.get("/learners")
def learners(p: Principal = Depends(require_trainer), db: Session = Depends(get_db)):
    rows = db.execute(select(m.User, m.Membership.role).join(m.Membership).where(m.Membership.organization_id == p.organization_id))
    return [{"id": str(u.id), "email": u.email, "name": u.display_name, "role": r} for u, r in rows]


@router.get("/sessions")
def sessions(p: Principal = Depends(require_trainer), db: Session = Depends(get_db)):
    rows = db.scalars(select(m.SimulationSession).where(m.SimulationSession.organization_id == p.organization_id)
                      .order_by(m.SimulationSession.created_at.desc()).limit(200))
    out = []
    for s in rows:
        ev = db.scalar(select(m.Evaluation).where(m.Evaluation.session_id == s.id).order_by(m.Evaluation.created_at.desc()))
        u = db.get(m.User, s.user_id)
        out.append({**session_public(s), "learner": u.email, "evaluation_id": str(ev.id) if ev else None,
                    "review_status": ev.trainer_review_status if ev else None})
    return out


@router.get("/evaluations/{eid}")
def trainer_eval(eid: uuid.UUID, p: Principal = Depends(require_trainer), db: Session = Depends(get_db)):
    ev = db.get(m.Evaluation, eid)
    s = db.get(m.SimulationSession, ev.session_id) if ev else None
    if not ev or s.organization_id != p.organization_id:
        raise HTTPException(404, "Évaluation introuvable.")
    reviews = list(db.scalars(select(m.TrainerReview).where(m.TrainerReview.evaluation_id == ev.id).order_by(m.TrainerReview.created_at)))
    data = evaluation_public(ev, db.get(m.CompetencyFramework, ev.framework_id), reviews)
    data["raw_output"] = ev.raw_output  # visible du formateur uniquement
    return data


@router.post("/evaluations/{eid}/reviews", status_code=201)
def review(eid: uuid.UUID, body: ReviewIn, p: Principal = Depends(require_trainer), db: Session = Depends(get_db)):
    """Ajoute une correction/un commentaire. La sortie initiale de Claude n'est jamais modifiée."""
    ev = db.get(m.Evaluation, eid)
    s = db.get(m.SimulationSession, ev.session_id) if ev else None
    if not ev or s.organization_id != p.organization_id:
        raise HTTPException(404, "Évaluation introuvable.")
    if body.competency_key and body.competency_key not in {x.competency_key for x in ev.scores}:
        raise HTTPException(422, "Compétence inconnue pour cette évaluation.")
    if body.corrected_score is not None and not body.competency_key:
        raise HTTPException(422, "competency_key requis pour corriger un score.")
    r = m.TrainerReview(evaluation_id=ev.id, reviewer_id=p.user.id, competency_key=body.competency_key,
                        corrected_score=body.corrected_score, comment=body.comment)
    db.add(r)
    ev.trainer_review_status = body.status or ("corrected" if body.corrected_score is not None else "reviewed")
    _audit(db, p, "evaluation.review", str(ev.id), {"competency": body.competency_key, "score": body.corrected_score})
    db.commit()
    return {"id": str(r.id), "trainer_review_status": ev.trainer_review_status}


@router.get("/scenarios")
def trainer_scenarios(p: Principal = Depends(require_trainer), db: Session = Depends(get_db)):
    rows = db.execute(select(m.Scenario, m.ScenarioVersion).join(m.ScenarioVersion).where(
        m.Scenario.organization_id == p.organization_id).order_by(m.Scenario.slug, m.ScenarioVersion.version.desc()))
    return [{"scenario_id": str(sc.id), "slug": sc.slug, "version_id": str(sv.id), "version": sv.version,
             "published": sv.published, "title": sv.title} for sc, sv in rows]


@router.get("/frameworks")
def frameworks(p: Principal = Depends(require_trainer), db: Session = Depends(get_db)):
    return [{"id": str(f.id), "key": f.key, "version": f.version, "title": f.title,
             "competencies": [{"key": c.key, "label": c.label} for c in f.competencies]}
            for f in db.scalars(select(m.CompetencyFramework).where(m.CompetencyFramework.organization_id == p.organization_id))]


@router.post("/scenarios", status_code=201)
def create_scenario(body: ScenarioIn, p: Principal = Depends(require_trainer), db: Session = Depends(get_db)):
    fw = db.get(m.CompetencyFramework, body.framework_id)
    if not fw or fw.organization_id != p.organization_id:
        raise HTTPException(422, "Grille inconnue.")
    slug = "-".join(body.title.lower().split())[:80] + "-" + uuid.uuid4().hex[:6]
    sc = m.Scenario(organization_id=p.organization_id, slug=slug)
    db.add(sc)
    db.flush()
    sv = _create_version(db, sc, body, 1)
    _audit(db, p, "scenario.create", str(sc.id))
    db.commit()
    return {"scenario_id": str(sc.id), "version_id": str(sv.id), "version": 1}


@router.put("/scenarios/{scenario_id}")
def update_scenario(scenario_id: uuid.UUID, body: ScenarioIn, p: Principal = Depends(require_trainer), db: Session = Depends(get_db)):
    """Une modification crée une NOUVELLE version : les sessions passées restent liées à l'ancienne."""
    sc = db.get(m.Scenario, scenario_id)
    if not sc or sc.organization_id != p.organization_id:
        raise HTTPException(404, "Scénario introuvable.")
    fw = db.get(m.CompetencyFramework, body.framework_id)
    if not fw or fw.organization_id != p.organization_id:
        raise HTTPException(422, "Grille inconnue.")
    last = db.scalar(select(func.max(m.ScenarioVersion.version)).where(m.ScenarioVersion.scenario_id == sc.id))
    sv = _create_version(db, sc, body, (last or 0) + 1)
    _audit(db, p, "scenario.new_version", str(sc.id), {"version": sv.version})
    db.commit()
    return {"scenario_id": str(sc.id), "version_id": str(sv.id), "version": sv.version}
