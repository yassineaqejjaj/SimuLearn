"""Contrat de sortie de l'évaluateur (validé avec Pydantic)."""
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class EvidenceIn(BaseModel):
    message_id: str
    speaker: Literal["learner", "character"] | None = None
    quote: str = Field(min_length=1, max_length=600)


class CompetencyResult(BaseModel):
    competency_id: str
    observable: bool
    score: int | None = Field(default=None, ge=1, le=5)
    confidence: float = Field(default=0.0, ge=0, le=1)
    justification: str = ""
    evidence: list[EvidenceIn] = []
    strengths: list[str] = []
    improvements: list[str] = []
    recommendation: str = ""

    @model_validator(mode="after")
    def _coherent(self):
        if not self.observable and self.score is not None:
            raise ValueError("score doit être null si le critère n'est pas observable")
        if self.observable and self.score is None:
            raise ValueError("score requis si le critère est observable")
        return self


class OverallFeedback(BaseModel):
    summary: str
    strengths: list[str] = []
    improvements: list[str] = []
    next_steps: list[str] = []


class EvaluationOutput(BaseModel):
    competencies: list[CompetencyResult]
    overall_feedback: OverallFeedback


def tool_schema() -> dict:
    return EvaluationOutput.model_json_schema()
