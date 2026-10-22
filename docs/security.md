# Sécurité et RGPD (état MVP)

Implémenté : clés API côté serveur uniquement (le navigateur n'envoie qu'une offre SDP) ; contrôle d'accès par organisation et propriétaire sur chaque ressource (404 hors périmètre) ; rôles formateur vérifiés côté serveur ; pas d'audio enregistré (`ENABLE_AUDIO_RECORDING` non implémenté) ; erreurs fournisseur sans corps brut ; journal d'audit des actions sensibles ; export (`GET /api/me/export`) et suppression (`DELETE /api/me/data`) ; purge de rétention `purge_expired` (fonction prête, **à planifier**) ; scénarios fictifs uniquement ; vue apprenant sans règles cachées ; `AUTH_DEV_MODE` refusé si `APP_ENV=production`.

Non fait / à faire avant tout usage réel en établissement de santé
- Revue juridique et sécurité ; AIPD ; contrats/DPA OpenAI et Anthropic ; durées de conservation côté fournisseurs, transferts hors UE, option de zéro rétention : **à vérifier contractuellement**. L'usage de ces fournisseurs ne garantit pas la conformité RGPD.
- Limitation de débit, durcissement CORS/headers, HTTPS/WSS en production (reverse proxy), rotation des secrets.
- Les logs applicatifs ne contiennent pas le texte des conversations (seulement identifiants et codes d'erreur) ; à revalider.
- Information des utilisateurs : mention sur la page de connexion et la fiche scénario ; un texte juridique complet reste à rédiger.
- Isolation par organisation testée sur la couche requête, pas par un test HTTP multi-organisation complet (le mode dev rattache tous les utilisateurs à la première organisation).
