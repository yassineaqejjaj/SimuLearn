"""Schéma métier SimuLearn. Portable PostgreSQL (prod) / SQLite (tests)."""
import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


class Role(str, enum.Enum):
    learner = "learner"
    trainer = "trainer"
    admin = "admin"


class SessionStatus(str, enum.Enum):
    CREATED = "CREATED"
    CONNECTING = "CONNECTING"
    READY = "READY"
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    ENDING = "ENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class PKMixin:
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Organization(PKMixin, Base):
    __tablename__ = "organizations"
    name: Mapped[str] = mapped_column(String(200))
    monthly_session_quota: Mapped[int] = mapped_column(Integer, default=500)


class User(PKMixin, Base):
    __tablename__ = "users"
    external_id: Mapped[str | None] = mapped_column(String(200), unique=True)  # Keycloak sub
    email: Mapped[str] = mapped_column(String(320), unique=True)
    display_name: Mapped[str] = mapped_column(String(200), default="")


class Membership(PKMixin, Base):
    __tablename__ = "memberships"
    __table_args__ = (UniqueConstraint("user_id", "organization_id"),)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    role: Mapped[str] = mapped_column(String(20), default=Role.learner.value)


class Group(PKMixin, Base):
    __tablename__ = "groups"
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    name: Mapped[str] = mapped_column(String(200))


class GroupMember(PKMixin, Base):
    __tablename__ = "group_members"
    __table_args__ = (UniqueConstraint("group_id", "user_id"),)
    group_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("groups.id"), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)


class CompetencyFramework(PKMixin, Base):
    """Grille d'évaluation versionnée. Une version publiée est immuable."""
    __tablename__ = "competency_frameworks"
    __table_args__ = (UniqueConstraint("organization_id", "key", "version"),)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    key: Mapped[str] = mapped_column(String(100))
    version: Mapped[int] = mapped_column(Integer, default=1)
    title: Mapped[str] = mapped_column(String(200))
    scale_min: Mapped[int] = mapped_column(Integer, default=1)
    scale_max: Mapped[int] = mapped_column(Integer, default=5)
    competencies: Mapped[list["Competency"]] = relationship(order_by="Competency.position", lazy="selectin")


class Competency(PKMixin, Base):
    __tablename__ = "competencies"
    __table_args__ = (UniqueConstraint("framework_id", "key"),)
    framework_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("competency_frameworks.id"), index=True)
    key: Mapped[str] = mapped_column(String(100))
    label: Mapped[str] = mapped_column(String(200))
    position: Mapped[int] = mapped_column(Integer, default=0)
    criteria: Mapped[list["EvaluationCriterion"]] = relationship(lazy="selectin")


class EvaluationCriterion(PKMixin, Base):
    __tablename__ = "evaluation_criteria"
    competency_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("competencies.id"), index=True)
    score_level: Mapped[int] = mapped_column(Integer)
    description: Mapped[str] = mapped_column(Text)


class Scenario(PKMixin, Base):
    __tablename__ = "scenarios"
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    slug: Mapped[str] = mapped_column(String(100))
    __table_args__ = (UniqueConstraint("organization_id", "slug"),)


class ScenarioVersion(PKMixin, Base):
    """Contenu complet figé du scénario. Les sessions pointent ici, jamais sur le dernier état."""
    __tablename__ = "scenario_versions"
    __table_args__ = (UniqueConstraint("scenario_id", "version"),)
    scenario_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("scenarios.id"), index=True)
    framework_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("competency_frameworks.id"))
    version: Mapped[int] = mapped_column(Integer, default=1)
    published: Mapped[bool] = mapped_column(Boolean, default=False)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    target_profession: Mapped[str] = mapped_column(String(100))
    category: Mapped[str] = mapped_column(String(100), default="Communication patient", server_default="Communication patient")
    difficulty: Mapped[str] = mapped_column(String(30))
    recommended_minutes: Mapped[int] = mapped_column(Integer, default=10)
    context: Mapped[str] = mapped_column(Text)
    learner_role: Mapped[str] = mapped_column(Text)
    objectives: Mapped[list] = mapped_column(JSON)  # visibles par l'apprenant
    behavior_rules: Mapped[list] = mapped_column(JSON)
    possible_events: Mapped[list] = mapped_column(JSON)
    end_conditions: Mapped[dict] = mapped_column(JSON)
    emotion_rules: Mapped[dict] = mapped_column(JSON)
    character: Mapped["Character"] = relationship(uselist=False, lazy="selectin")


class Character(PKMixin, Base):
    __tablename__ = "characters"
    scenario_version_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("scenario_versions.id"), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    age: Mapped[int] = mapped_column(Integer)
    role: Mapped[str] = mapped_column(String(200))
    personality: Mapped[list] = mapped_column(JSON)
    background: Mapped[str] = mapped_column(Text)
    initial_attitude: Mapped[str] = mapped_column(Text)
    known_facts: Mapped[list] = mapped_column(JSON)
    withheld_facts: Mapped[list] = mapped_column(JSON)
    conversational_goal: Mapped[str] = mapped_column(Text)
    voice: Mapped[str] = mapped_column(String(50))
    initial_state: Mapped[dict] = mapped_column(JSON)


class SimulationSession(PKMixin, Base):
    __tablename__ = "simulation_sessions"
    __table_args__ = (Index("ix_sessions_user_created", "user_id", "created_at"),)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    scenario_version_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("scenario_versions.id"), index=True)
    status: Mapped[str] = mapped_column(String(20), default=SessionStatus.CREATED.value)
    provider: Mapped[str] = mapped_column(String(50))
    provider_session_id: Mapped[str | None] = mapped_column(String(200))
    end_reason: Mapped[str | None] = mapped_column(String(50))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    max_duration_seconds: Mapped[int] = mapped_column(Integer)
    transcript_complete: Mapped[bool] = mapped_column(Boolean, default=True)
    voice_seconds: Mapped[float | None] = mapped_column(Float)
    provider_usage: Mapped[dict | None] = mapped_column(JSON)
    latency_metrics: Mapped[dict | None] = mapped_column(JSON)
    scenario_version: Mapped[ScenarioVersion] = relationship(lazy="selectin")


class CharacterState(PKMixin, Base):
    """Journal des états émotionnels internes (jamais montrés à l'apprenant)."""
    __tablename__ = "character_states"
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("simulation_sessions.id"), index=True)
    state: Mapped[dict] = mapped_column(JSON)
    cause: Mapped[str] = mapped_column(String(200))
    offset_ms: Mapped[int | None] = mapped_column(Integer)


class ConversationFragment(PKMixin, Base):
    """Fragment brut tel que reçu (delta). Ordonné par start_ms, pas par arrivée."""
    __tablename__ = "conversation_fragments"
    __table_args__ = (Index("ix_fragments_session_start", "session_id", "start_ms"),)
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("simulation_sessions.id"))
    speaker: Mapped[str] = mapped_column(String(20))  # learner | character
    text: Mapped[str] = mapped_column(Text)
    start_ms: Mapped[int] = mapped_column(Integer)
    end_ms: Mapped[int] = mapped_column(Integer)
    seq: Mapped[int] = mapped_column(Integer)


class ConversationMessage(PKMixin, Base):
    """Échange lisible, regroupé à partir des fragments."""
    __tablename__ = "conversation_messages"
    __table_args__ = (Index("ix_messages_session_start", "session_id", "start_ms"),)
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("simulation_sessions.id"))
    speaker: Mapped[str] = mapped_column(String(20))
    text: Mapped[str] = mapped_column(Text)
    start_ms: Mapped[int] = mapped_column(Integer)
    end_ms: Mapped[int] = mapped_column(Integer)
    reliability: Mapped[str] = mapped_column(String(20), default="normal")  # normal | uncertain | incomplete
    reliability_note: Mapped[str | None] = mapped_column(String(300))


class SimulationEvent(PKMixin, Base):
    __tablename__ = "simulation_events"
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("simulation_sessions.id"), index=True)
    type: Mapped[str] = mapped_column(String(80))
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    offset_ms: Mapped[int | None] = mapped_column(Integer)


class Evaluation(PKMixin, Base):
    __tablename__ = "evaluations"
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("simulation_sessions.id"), index=True)
    framework_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("competency_frameworks.id"), index=True)
    status: Mapped[str] = mapped_column(String(30))  # pending | completed | failed | completed_with_warnings
    provider: Mapped[str] = mapped_column(String(50))
    model: Mapped[str] = mapped_column(String(100))
    raw_output: Mapped[dict | None] = mapped_column(JSON)  # sortie initiale de Claude, jamais écrasée
    overall_feedback: Mapped[dict | None] = mapped_column(JSON)
    warnings: Mapped[list] = mapped_column(JSON, default=list)
    error: Mapped[str | None] = mapped_column(Text)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    trainer_review_status: Mapped[str] = mapped_column(String(20), default="pending")
    usage: Mapped[dict | None] = mapped_column(JSON)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    scores: Mapped[list["EvaluationScore"]] = relationship(lazy="selectin")


class EvaluationScore(PKMixin, Base):
    __tablename__ = "evaluation_scores"
    __table_args__ = (UniqueConstraint("evaluation_id", "competency_key"),)
    evaluation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("evaluations.id"), index=True)
    competency_key: Mapped[str] = mapped_column(String(100))
    score: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(30))  # scored | not_observable
    confidence: Mapped[float | None] = mapped_column(Float)
    justification: Mapped[str] = mapped_column(Text, default="")
    strengths: Mapped[list] = mapped_column(JSON, default=list)
    improvements: Mapped[list] = mapped_column(JSON, default=list)
    recommendation: Mapped[str] = mapped_column(Text, default="")
    evidence: Mapped[list["EvaluationEvidence"]] = relationship(lazy="selectin")


class EvaluationEvidence(PKMixin, Base):
    __tablename__ = "evaluation_evidence"
    score_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("evaluation_scores.id"), index=True)
    message_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("conversation_messages.id"))
    quote: Mapped[str] = mapped_column(Text)
    start_ms: Mapped[int] = mapped_column(Integer)
    end_ms: Mapped[int] = mapped_column(Integer)
    verified: Mapped[bool] = mapped_column(Boolean, default=True)


class TrainerReview(PKMixin, Base):
    """Correction du formateur, stockée à part : la sortie Claude reste intacte."""
    __tablename__ = "trainer_reviews"
    evaluation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("evaluations.id"), index=True)
    reviewer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    competency_key: Mapped[str | None] = mapped_column(String(100))
    corrected_score: Mapped[int | None] = mapped_column(Integer)
    comment: Mapped[str] = mapped_column(Text, default="")


class UsageMetric(PKMixin, Base):
    __tablename__ = "usage_metrics"
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("simulation_sessions.id"), index=True)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    provider: Mapped[str] = mapped_column(String(50))
    kind: Mapped[str] = mapped_column(String(50))  # voice | evaluation | guidance
    quantities: Mapped[dict] = mapped_column(JSON)  # seconds / tokens
    estimated_cost_usd: Mapped[float | None] = mapped_column(Float)
    pricing_version: Mapped[str] = mapped_column(String(80))


class AuditLog(PKMixin, Base):
    __tablename__ = "audit_logs"
    organization_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, index=True)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    action: Mapped[str] = mapped_column(String(100))
    target: Mapped[str] = mapped_column(String(200), default="")
    detail: Mapped[dict] = mapped_column(JSON, default=dict)
