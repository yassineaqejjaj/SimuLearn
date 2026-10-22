from app import models as m


def scenario_public(sv: m.ScenarioVersion, fw: m.CompetencyFramework | None = None) -> dict:
    """Vue apprenant : jamais de règles de comportement, faits cachés ni états internes."""
    c = sv.character
    return {
        "id": str(sv.id), "scenario_id": str(sv.scenario_id), "version": sv.version, "title": sv.title,
        "description": sv.description, "target_profession": sv.target_profession, "category": sv.category, "difficulty": sv.difficulty,
        "recommended_minutes": sv.recommended_minutes, "context": sv.context, "learner_role": sv.learner_role,
        "objectives": sv.objectives, "character": {"name": c.name, "role": c.role, "age": c.age},
        "competencies": [x.label for x in fw.competencies] if fw else [],
    }


def session_public(s: m.SimulationSession) -> dict:
    return {
        "id": str(s.id), "scenario_version_id": str(s.scenario_version_id), "scenario_id": str(s.scenario_version.scenario_id), "scenario_title": s.scenario_version.title,
        "status": s.status, "provider": s.provider, "created_at": s.created_at.isoformat(),
        "started_at": s.started_at.isoformat() if s.started_at else None,
        "ended_at": s.ended_at.isoformat() if s.ended_at else None, "end_reason": s.end_reason,
        "max_duration_seconds": s.max_duration_seconds, "transcript_complete": s.transcript_complete,
    }


def evaluation_public(ev: m.Evaluation, framework: m.CompetencyFramework, reviews: list[m.TrainerReview]) -> dict:
    labels = {c.key: c.label for c in framework.competencies}
    corrections = {r.competency_key: r for r in reviews if r.competency_key}
    return {
        "id": str(ev.id), "session_id": str(ev.session_id), "status": ev.status, "provider": ev.provider, "model": ev.model,
        "framework": {"id": str(framework.id), "key": framework.key, "version": framework.version},
        "warnings": ev.warnings, "error": ev.error, "attempts": ev.attempts, "trainer_review_status": ev.trainer_review_status,
        "overall_feedback": ev.overall_feedback, "disclaimer": "Retour de formation, pas une certification.",
        "competencies": [{
            "competency_id": s.competency_key, "label": labels.get(s.competency_key, s.competency_key),
            "score": s.score, "status": s.status, "observable": s.status == "scored", "confidence": s.confidence,
            "justification": s.justification, "strengths": s.strengths, "improvements": s.improvements,
            "recommendation": s.recommendation,
            "evidence": [{"message_id": str(e.message_id), "quote": e.quote, "start_ms": e.start_ms, "end_ms": e.end_ms}
                         for e in s.evidence],
            "trainer_correction": ({"score": corrections[s.competency_key].corrected_score,
                                    "comment": corrections[s.competency_key].comment}
                                   if s.competency_key in corrections else None),
        } for s in sorted(ev.scores, key=lambda x: list(labels).index(x.competency_key) if x.competency_key in labels else 99)],
        "trainer_comments": [{"comment": r.comment, "created_at": r.created_at.isoformat()} for r in reviews if not r.competency_key],
    }
