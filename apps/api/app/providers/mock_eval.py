"""Évaluateur de DÉVELOPPEMENT : heuristique déterministe, PAS une évaluation Claude.

Les citations sont de vrais extraits de la transcription afin d'exercer le pipeline de vérification.
"""
from app.emotion import detect_signals
from app.providers.base import EvaluationRequest, EvaluationResponse


class MockEvaluationProvider:
    name = "mock"

    async def evaluate(self, request: EvaluationRequest) -> EvaluationResponse:
        learner = [m for m in request.payload["messages"] if m["speaker"] == "learner"]
        signals = [(m, detect_signals(m["text"])) for m in learner]

        def pick(sig: str):
            return next((m for m, s in signals if sig in s), None)

        comps = []
        for c in request.payload["framework"]["competencies"]:
            key = c["key"]
            sig = {"empathy": "empathy", "active_listening": "rephrase", "conflict_handling": "credible_next_step",
                   "conclusion": "credible_next_step"}.get(key)
            m = pick(sig) if sig else (learner[0] if learner else None)
            if m is None or not learner:
                comps.append({"competency_id": key, "observable": False, "score": None})
                continue
            comps.append({
                "competency_id": key, "observable": True, "score": 4 if sig else 3, "confidence": 0.5,
                "justification": "[MOCK] Heuristique par mots-clés, non pédagogique.",
                "evidence": [{"message_id": m["message_id"], "speaker": "learner", "quote": m["text"][:120]}],
                "strengths": ["[MOCK]"], "improvements": ["[MOCK]"], "recommendation": "[MOCK] Rejouer avec un vrai évaluateur.",
            })
        return EvaluationResponse(
            data={"competencies": comps, "overall_feedback": {"summary": "[MOCK] Évaluation de développement, non fiable.",
                                                                "strengths": [], "improvements": [], "next_steps": []}},
            model="mock", usage={"input_tokens": 0, "output_tokens": 0})
