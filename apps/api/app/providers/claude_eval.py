"""Évaluation pédagogique avec Claude (sortie structurée via un outil forcé)."""
import json

import anthropic

from app.config import Settings
from app.providers.base import EvaluationRequest, EvaluationResponse, ProviderError, ProviderNotConfigured

TOOL_NAME = "submit_evaluation"


class ClaudeEvaluationProvider:
    name = "claude"

    def __init__(self, settings: Settings):
        self.s = settings

    async def evaluate(self, request: EvaluationRequest) -> EvaluationResponse:
        if missing := self.s.missing_for_evaluation():
            raise ProviderNotConfigured(missing)
        client = anthropic.AsyncAnthropic(api_key=self.s.anthropic_api_key)
        model = self.s.anthropic_evaluation_model
        try:
            resp = await client.messages.create(
                model=model,
                max_tokens=6000,
                system=request.system,
                messages=[{"role": "user", "content": json.dumps(request.payload, ensure_ascii=False)}],
                tools=[{"name": TOOL_NAME, "description": "Soumet l'évaluation structurée.", "input_schema": request.output_schema}],
                tool_choice={"type": "tool", "name": TOOL_NAME},
            )
        except anthropic.APIError as exc:
            raise ProviderError(f"Erreur API Anthropic : {type(exc).__name__}") from exc
        block = next((b for b in resp.content if getattr(b, "type", "") == "tool_use" and b.name == TOOL_NAME), None)
        if block is None:
            raise ProviderError("Réponse Claude sans sortie structurée.")
        u = resp.usage
        usage = {
            "input_tokens": u.input_tokens,
            "output_tokens": u.output_tokens,
            "cache_read_input_tokens": getattr(u, "cache_read_input_tokens", 0) or 0,
            "cache_creation_input_tokens": getattr(u, "cache_creation_input_tokens", 0) or 0,
        }
        return EvaluationResponse(data=dict(block.input), model=model, usage=usage)
