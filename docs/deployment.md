# Déploiement

`docker compose up --build` après `cp .env.example .env` et renseignement de : `POSTGRES_PASSWORD`, `KEYCLOAK_ADMIN_PASSWORD`, clés OpenAI/Anthropic, Keycloak. Non lancé dans l'environnement de build.

- Créer dans Keycloak (realm `simulearn`, importé) les utilisateurs et leurs rôles `learner`/`trainer`/`admin`. Le compte doit exister dans la table `users` (même e-mail) avec une `membership` : pas d'auto-provisionnement en mode Keycloak (par choix : un étudiant inconnu n'entre pas dans un établissement).
- Un seul worker API (voir architecture). Migrations : `alembic upgrade head` au démarrage du conteneur.
- Planifier `purge_expired` (cron). Placer un reverse proxy TLS devant web/api.
- Ports : l'API écoute 8000 ; changer `API_PORT` / `NEXT_PUBLIC_API_URL` si occupé.
