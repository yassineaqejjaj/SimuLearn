# Architecture

Next.js (apps/web) → FastAPI (apps/api) → PostgreSQL. GPT-Live : le navigateur parle en WebRTC directement à OpenAI ; FastAPI ne voit jamais l'audio. Claude n'est appelé qu'à l'évaluation finale.

```
navigateur ──SDP offer──▶ FastAPI ──POST /v1/live/sessions──▶ OpenAI
navigateur ◀──SDP answer── FastAPI
navigateur ◀═══ WebRTC audio + data channel ═══▶ OpenAI
FastAPI ◀── sideband wss /v1/live/sessions/{id}/attach (transcripts, usage, delegation) ── OpenAI
```

## Modules (apps/api/app)
- `models.py` schéma · `seed.py` grille v1 + scénario Marc Laurent · `prompts.py` prompt généré depuis la base
- `emotion.py` état interne (règles déterministes, bornées, journalisées) · `transcript.py` regroupement des fragments
- `providers/` interfaces (`base.py`), `openai_live.py`, `claude_eval.py`, `mock.py`, `mock_eval.py`
- `runtime.py` consomme les événements d'une session vocale, tient l'état métier et finalise
- `evaluation_service.py` + `evidence.py` évaluation, validation Pydantic, vérification déterministe des preuves
- `routers/` scenarios, simulations, evaluations (comparaison), trainer, privacy

## Choix et limites assumés
- **Source de vérité = SimuLearn.** Transcripts et scores viennent du sideband serveur, jamais du navigateur (qui ne peut poster que des événements d'interface `client.*`).
- **Un seul worker API** : le runtime vocal garde ses connexions en mémoire. Si le processus redémarre, la session est refermée `runtime_lost` et marquée transcript incomplet. Passer à plusieurs workers demande un état partagé (Valkey) : non fait.
- Pas de SeaweedFS (aucun audio conservé), pas de Prometheus (logs structurés `structlog` seulement), Valkey déployé mais non utilisé.
- Pilotage pédagogique Claude (fonction B) et assistance scénarios (C) : **non implémentés**. Les délégations GPT-Live reçoivent une réponse neutre (`thinking.append`, même `delegation_id`).
- `ElevenLabsClaudeVoiceProvider` : non implémenté (comme demandé). L'interface `VoiceSimulationProvider` est prête.
- Gestion des groupes (création/affectation) : lecture seule dans l'UI formateur.
