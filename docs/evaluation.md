# Évaluation

1. Fin de session → regroupement des fragments en messages (UUID, locuteur, ms, fiabilité).
2. Claude (`claude-sonnet-5-5`, outil `submit_evaluation` forcé, schéma Pydantic) reçoit : version scénario, objectifs, grille + descripteurs, messages, limites de transcription. Aucune donnée d'identité apprenant.
3. Validation Pydantic : `observable=false ⇒ score=null`, score 1–5. Échec → jusqu'à 3 tentatives (l'erreur est renvoyée au modèle) ; sinon statut `failed` visible et relançable. Jamais d'évaluation partielle silencieuse.
4. Vérification déterministe des preuves (`evidence.py`) : message existe, même session, locuteur correct, citation retrouvée (normalisation + tolérance 0,9). Une preuve rejetée est retirée et journalisée dans `warnings` ; un score sans aucune preuve vérifiée est retiré (`not_observable`). Les horodatages viennent de la base, jamais de Claude.
5. Pas de transcription de l'apprenant → pas d'appel Claude. Transcription incomplète → évaluation lancée avec avertissement.
6. Corrections formateur : table à part ; l'affichage apprenant montre la correction, `raw_output` reste intact.
7. Comparaison : uniquement même version de grille (sinon 422) ; compétences non observables = « non comparable ».
8. Le texte des messages est traité comme donnée (instruction système anti-injection) ; cela réduit le risque, ne le supprime pas.

Coûts : tokens enregistrés par appel ; coût en USD seulement si les tarifs de `config/pricing.json` sont renseignés (`null` actuellement pour Claude : le coût est alors « inconnu », pas inventé).
