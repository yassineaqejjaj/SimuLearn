"""Fournisseur de DÉVELOPPEMENT. N'utilise aucune API distante, aucun audio.

Sert à tester le métier (états, transcription, évaluation) sans clé. Le navigateur n'a pas
de flux vocal en mode mock : l'interface propose une saisie texte clairement étiquetée.
"""
import asyncio
from typing import Any, AsyncIterator

from app.providers.base import VoiceConnection, VoiceSessionConfig, VoiceStart


class MockConnection:
    def __init__(self):
        self.inbox: asyncio.Queue[dict | None] = asyncio.Queue()
        self.sent: list[dict] = []
        self.usage_seconds = 0

    async def events(self) -> AsyncIterator[dict[str, Any]]:
        while (ev := await self.inbox.get()) is not None:
            yield ev

    async def send(self, event: dict[str, Any]) -> None:
        self.sent.append(event)
        if event.get("type") == "session.close":
            await self.inbox.put({"type": "session.closed", "reason": "close_requested", "usage": {"seconds": self.usage_seconds}})

    async def close(self) -> None:
        await self.inbox.put(None)

    def push(self, event: dict[str, Any]) -> None:
        if event.get("type") == "session.usage.updated":
            self.usage_seconds = event["usage"]["seconds"]
        self.inbox.put_nowait(event)


class MockVoiceProvider:
    name = "mock"

    def __init__(self):
        self.connections: dict[str, MockConnection] = {}
        self._n = 0

    async def start_session(self, config: VoiceSessionConfig, client_offer_sdp: str | None) -> VoiceStart:
        self._n += 1
        sid = f"mock_{self._n}"
        self.connections[sid] = MockConnection()
        return VoiceStart(provider_session_id=sid, answer_sdp=None)

    async def attach(self, provider_session_id: str) -> VoiceConnection:
        conn = self.connections[provider_session_id]
        conn.push({"type": "session.started"})
        return conn
