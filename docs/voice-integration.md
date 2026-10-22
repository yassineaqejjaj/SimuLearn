# Intégration GPT-Live

Sources lues le 2026-10-22 : guides `live`, `live-conversations`, `live-delegation`, `voice-webrtc?api=live`, `voice-server-controls?api=live`, page modèle `gpt-live-1`.

## Ce qui est implémenté d'après la doc
- Création : `POST {base}/v1/live/sessions` avec `{"session": {model, instructions, audio:{output:{voice}}, delegation:{type:"client"}}, "transport": {type:"webrtc", sdp}}` → 201 `{session:{id}, transport:{sdp}}`.
- Navigateur : data channel `oai-events` créé avant l'offre ; pas de `session.start` ; attente de `session.started`.
- Serveur : sideband `wss://api.openai.com/v1/live/sessions/{id}/attach` (Bearer). Événements traités : `session.started`, `session.input_transcript.delta`, `session.output_transcript.delta`, `session.usage.updated` (cumulatif : dernière valeur retenue), `session.delegation.created`, `session.closed`, `error`.
- Commandes envoyées : `session.close`, `session.thinking.append` (contexte émotionnel silencieux, `delegation_id: null`), réponse de délégation avec le même `delegation_id`.
- Fin : `session.close` puis attente de `session.closed` (10 s) ; sinon transcription marquée incomplète.

## Points NON vérifiés (à tester avec une clé)
1. Header(s) additionnel(s) éventuels pour `/v1/live/sessions` et le sideband (la doc lue n'en cite pas).
2. Voix françaises `sillage` / `brise` : **absentes de la doc lue** (la voix par défaut documentée est `marin`). La voix est configurable (`OPENAI_LIVE_VOICE`, champ du personnage) ; l'API refusera une voix inconnue (erreur `ProviderError` explicite).
3. Qualité du français et du jeu de rôle de `gpt-live-1` ; respect des consignes anti-divulgation.
4. Interruptions : la doc lue ne décrit pas d'événement d'interruption ni de troncature audio. Le serveur détecte une prise de parole qui chevauche la parole du patient d'après les `start_ms/end_ms` des transcripts, la marque (`interruption`, message patient « incertain ») mais **ne contrôle pas la lecture audio** (côté client/service). « Ne pas conserver comme entendus des propos non joués » n'est donc que signalé à l'évaluateur, pas garanti.
5. Latences : mesurées (connexion, réaction après tour, interruptions) mais jamais observées sur le vrai service.
6. Un fragment de transcript n'a pas d'identifiant de tour : le regroupement par locuteur + écart de 1,5 s est une heuristique.
7. Le détecteur d'émotion lit les mots-clés de la transcription (qui peut être fausse) ; c'est volontairement simple.

## Délégation Claude pendant la conversation
`ENABLE_CLAUDE_LIVE_DELEGATION` existe mais l'appel Claude en direct n'est pas implémenté ; le moteur fonctionne sans.
