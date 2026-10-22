import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models as m
from app.auth import Principal, current_principal
from app.db import get_db
from app.serializers import scenario_public

router = APIRouter(prefix="/api/scenarios", tags=["scenarios"])


def _latest_published(db: Session, org_id):
    rows = db.scalars(select(m.ScenarioVersion).join(m.Scenario).where(
        m.Scenario.organization_id == org_id, m.ScenarioVersion.published.is_(True)).order_by(m.ScenarioVersion.version.desc()))
    seen, out = set(), []
    for sv in rows:
        if sv.scenario_id not in seen:
            seen.add(sv.scenario_id)
            out.append(sv)
    return out


@router.get("")
def catalog(p: Principal = Depends(current_principal), db: Session = Depends(get_db)):
    return [scenario_public(sv, db.get(m.CompetencyFramework, sv.framework_id)) for sv in _latest_published(db, p.organization_id)]


@router.get("/{version_id}")
def detail(version_id: uuid.UUID, p: Principal = Depends(current_principal), db: Session = Depends(get_db)):
    sv = db.get(m.ScenarioVersion, version_id)
    scenario = db.get(m.Scenario, sv.scenario_id) if sv else None
    if not sv or scenario.organization_id != p.organization_id or not sv.published:
        raise HTTPException(404, "Scénario introuvable.")
    return scenario_public(sv, db.get(m.CompetencyFramework, sv.framework_id))
