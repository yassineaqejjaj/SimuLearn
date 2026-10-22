# Base de données

Schéma dans `apps/api/app/models.py`, migration `alembic/versions/0001_initial_schema.py`. UUID partout, clés étrangères, index sur (user, date), (session, start_ms).

Entités : organizations, users, memberships, groups, group_members, competency_frameworks → competencies → evaluation_criteria, scenarios → scenario_versions → characters, simulation_sessions, character_states (journal émotionnel), conversation_fragments (brut) → conversation_messages (regroupé), simulation_events, evaluations → evaluation_scores → evaluation_evidence, trainer_reviews, usage_metrics, audit_logs.

Règles clés
- Une session pointe vers une `scenario_version` ; une évaluation vers un `competency_framework` (version). Modifier un scénario crée une **nouvelle version**. Rien n'est reconstruit depuis la dernière version.
- `evaluations.raw_output` = sortie initiale de Claude, jamais modifiée ; corrections dans `trainer_reviews`.
- Isolation : chaque requête filtre par `organization_id` du principal ; hors organisation → 404.
- Les grilles publiées devraient être immuables : **non appliqué par la base** (convention applicative ; pas d'API de modification de grille dans le MVP).
- Testé sur SQLite ; PostgreSQL non testé (types portables `Uuid`, `JSON`). Utiliser `JSONB` plus tard si besoin de requêtes JSON.
