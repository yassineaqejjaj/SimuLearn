import logging

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.db import get_engine
from app.routers import evaluations, privacy, scenarios, simulations, trainer

structlog.configure(wrapper_class=structlog.make_filtering_bound_logger(logging.INFO))


def create_app() -> FastAPI:
    s = get_settings()
    app = FastAPI(title=f"{s.app_name} API", version="0.1.0")
    app.add_middleware(CORSMiddleware, allow_origins=[s.app_url], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
    for r in (scenarios, simulations, evaluations, trainer, privacy):
        app.include_router(r.router)

    @app.get("/api/health")
    def health():
        """État de configuration explicite : n'indique jamais « connecté » sans clé."""
        return {
            "status": "ok", "env": s.app_env, "voice_provider": s.voice_provider, "evaluation_provider": s.evaluation_provider,
            "missing_config": {"voice": s.missing_for_voice() if s.voice_provider == "openai_live" else [],
                               "evaluation": s.missing_for_evaluation() if s.evaluation_provider == "claude" else []},
            "auth": "dev" if s.auth_dev_mode else "keycloak",
            "warning": "Mode mock actif : aucune API distante n'est utilisée." if "mock" in (s.voice_provider, s.evaluation_provider) else None,
        }

    return app


app = create_app()
