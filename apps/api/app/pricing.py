"""Estimation des coûts à partir d'une configuration de tarifs versionnée (jamais codée en dur)."""
import json
from functools import lru_cache
from pathlib import Path

from app.config import get_settings


@lru_cache
def load_pricing() -> dict:
    return json.loads(Path(get_settings().pricing_config_path).read_text())


def voice_cost_usd(seconds: float) -> float | None:
    rate = load_pricing().get("openai_live", {}).get("usd_per_minute")
    return None if rate is None else round(seconds / 60 * rate, 6)


def llm_cost_usd(model: str, usage: dict) -> float | None:
    """None si un tarif nécessaire n'est pas renseigné : on n'invente pas de coût."""
    p = load_pricing().get("anthropic", {}).get(model, {})
    inp, out = p.get("usd_per_mtok_input"), p.get("usd_per_mtok_output")
    if inp is None or out is None:
        return None
    cache = p.get("usd_per_mtok_cache_read") or inp
    return round((usage.get("input_tokens", 0) * inp + usage.get("output_tokens", 0) * out
                  + usage.get("cache_read_input_tokens", 0) * cache) / 1_000_000, 6)


def pricing_version() -> str:
    return load_pricing().get("version", "unknown")
