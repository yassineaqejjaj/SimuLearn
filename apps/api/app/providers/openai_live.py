"""OpenAI GPT-Live 1 (WebRTC côté navigateur, sideband WebSocket côté serveur).

Endpoints d'après https://developers.openai.com/api/docs/guides/voice-webrtc?api=live :
  POST /v1/live/sessions  body {"session": {...}, "transport": {"type": "webrtc", "sdp": offer}}
  wss  /v1/live/sessions/{id}/attach
La clé API reste côté serveur ; le navigateur n'envoie que son offre SDP.
"""
import asyncio
import json
from typing import Any, AsyncIterator

import httpx
import websockets

from app.config import Settings
from app.providers.base import ProviderError, ProviderNotConfigured, VoiceConnection, VoiceSessionConfig, VoiceStart


class _SidebandConnection:
    def __init__(self, ws):
        self._ws = ws

    async def events(self) -> AsyncIterator[dict[str, Any]]:
        try:
            async for raw in self._ws:
                try:
                    yield json.loads(raw)
                except json.JSONDecodeError:
                    continue
        except websockets.ConnectionClosed:
            return

    async def send(self, event: dict[str, Any]) -> None:
        await self._ws.send(json.dumps(event))

    async def close(self) -> None:
        await self._ws.close()


class OpenAILiveProvider:
    name = "openai_live"

    def __init__(self, settings: Settings):
        self.s = settings

    def _require_key(self) -> None:
        if missing := self.s.missing_for_voice():
            raise ProviderNotConfigured(missing)

    async def start_session(self, config: VoiceSessionConfig, client_offer_sdp: str | None) -> VoiceStart:
        self._require_key()
        if not client_offer_sdp:
            raise ProviderError("Offre SDP WebRTC manquante.")
        body = {
            "session": {
                "model": config.model,
                "instructions": config.instructions,
                "audio": {"output": {"voice": config.voice}},
                "delegation": {"type": config.delegation},
            },
            "transport": {"type": "webrtc", "sdp": client_offer_sdp},
        }
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(
                f"{self.s.openai_base_url}/v1/live/sessions",
                headers={"Authorization": f"Bearer {self.s.openai_api_key}"},
                json=body,
            )
        if resp.status_code != 201:
            # Ne pas relayer le corps brut (peut contenir les instructions) : code et type seulement.
            try:
                err = resp.json().get("error", {})
            except ValueError:
                err = {}
            raise ProviderError(f"GPT-Live a refusé la session (HTTP {resp.status_code}, {err.get('code') or err.get('type') or 'unknown'}).")
        data = resp.json()
        return VoiceStart(provider_session_id=data["session"]["id"], answer_sdp=data["transport"]["sdp"])

    async def attach(self, provider_session_id: str) -> VoiceConnection:
        self._require_key()
        url = self.s.openai_base_url.replace("https://", "wss://").replace("http://", "ws://")
        ws = await websockets.connect(
            f"{url}/v1/live/sessions/{provider_session_id}/attach",
            additional_headers={"Authorization": f"Bearer {self.s.openai_api_key}"},
            max_size=None,
        )
        return _SidebandConnection(ws)
