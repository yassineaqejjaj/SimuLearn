"""Authentification Keycloak (JWT RS256 via JWKS) + mode dev explicite et désactivé par défaut."""
import uuid
from dataclasses import dataclass
from functools import lru_cache

import jwt
from fastapi import Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import models as m
from app.config import Settings, get_settings
from app.db import get_db


@dataclass
class Principal:
    user: m.User
    organization_id: uuid.UUID
    role: str

    @property
    def is_trainer(self) -> bool:
        return self.role in (m.Role.trainer.value, m.Role.admin.value)


@lru_cache
def _jwks(url: str) -> jwt.PyJWKClient:
    return jwt.PyJWKClient(url, cache_keys=True)


def _claims_from_keycloak(token: str, s: Settings) -> dict:
    if not (s.keycloak_url and s.keycloak_realm):
        raise HTTPException(503, "Keycloak non configuré (KEYCLOAK_URL, KEYCLOAK_REALM).")
    try:
        key = _jwks(f"{s.keycloak_issuer}/protocol/openid-connect/certs").get_signing_key_from_jwt(token)
        return jwt.decode(token, key.key, algorithms=["RS256"], issuer=s.keycloak_issuer,
                          options={"verify_aud": False, "require": ["exp", "sub"]})
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Session expirée.")
    except jwt.PyJWTError:
        raise HTTPException(401, "Jeton invalide.")


def _dev_principal(token: str, db: Session) -> Principal:
    """Jeton `dev:<email>[:<role>]`. Lie l'utilisateur à l'organisation de démo."""
    parts = token.split(":")
    email, role = parts[1], (parts[2] if len(parts) > 2 else "learner")
    if role not in {r.value for r in m.Role}:
        raise HTTPException(401, "Rôle dev inconnu.")
    org = db.scalar(select(m.Organization).order_by(m.Organization.created_at))
    if org is None:
        raise HTTPException(503, "Base non initialisée (lancer le seed).")
    # Des requêtes parallèles (première page) peuvent créer le même compte : on relit après conflit.
    for _ in range(3):
        user = db.scalar(select(m.User).where(m.User.email == email))
        ms = db.scalar(select(m.Membership).where(m.Membership.user_id == user.id, m.Membership.organization_id == org.id)) if user else None
        if user and ms:
            break
        try:
            if user is None:
                user = m.User(email=email, display_name=email.split("@")[0].replace(".", " ").title())
                db.add(user)
                db.flush()
            if ms is None:
                ms = m.Membership(user_id=user.id, organization_id=org.id, role=role)
                db.add(ms)
            db.commit()
        except IntegrityError:
            db.rollback()
    else:
        raise HTTPException(503, "Création du compte de développement impossible.")
    return Principal(user, org.id, ms.role)


def current_principal(authorization: str | None = Header(default=None), db: Session = Depends(get_db),
                      settings: Settings = Depends(get_settings)) -> Principal:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "Authentification requise.")
    token = authorization[7:].strip()
    if token.startswith("dev:"):
        if not (settings.auth_dev_mode and settings.app_env != "production"):
            raise HTTPException(401, "Jeton invalide.")
        return _dev_principal(token, db)
    claims = _claims_from_keycloak(token, settings)
    user = db.scalar(select(m.User).where(m.User.external_id == claims["sub"]))
    if user is None:
        email = claims.get("email")
        user = db.scalar(select(m.User).where(m.User.email == email)) if email else None
        if user is None:
            raise HTTPException(403, "Compte non rattaché à un établissement.")
        user.external_id = claims["sub"]
        db.commit()
    ms = db.scalar(select(m.Membership).where(m.Membership.user_id == user.id))
    if ms is None:
        raise HTTPException(403, "Aucune appartenance à un établissement.")
    return Principal(user, ms.organization_id, ms.role)


def require_trainer(p: Principal = Depends(current_principal)) -> Principal:
    if not p.is_trainer:
        raise HTTPException(403, "Réservé aux formateurs.")
    return p
