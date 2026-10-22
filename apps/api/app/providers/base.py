"""Interfaces fournisseurs. Le métier ne dépend d'aucun SDK."""
from dataclasses import dataclass
from typing import Any, AsyncIterator, Protocol


class ProviderNotConfigured(RuntimeError):
    def __init__(self, missing: list[str]):
        self.missing = missing
        super().__init__("Configuration manquante : " + ", ".join(missing))


class ProviderError(RuntimeError):
    pass


@dataclass
class VoiceSessionConfig:
    model: str
    voice: str
    instructions: str
    delegation: str = "client"


@dataclass
class VoiceStart:
    provider_session_id: str
    answer_sdp: str | None  # None pour un fournisseur sans WebRTC (mock)


class VoiceConnection(Protocol):
    """Canal serveur vers une session vocale en cours (événements entrants + commandes)."""

    def events(self) -> AsyncIterator[dict[str, Any]]: ...
    async def send(self, event: dict[str, Any]) -> None: ...
    async def close(self) -> None: ...


class VoiceSimulationProvider(Protocol):
    name: str

    async def start_session(self, config: VoiceSessionConfig, client_offer_sdp: str | None) -> VoiceStart: ...
    async def attach(self, provider_session_id: str) -> VoiceConnection: ...


@dataclass
class EvaluationRequest:
    system: str
    payload: dict[str, Any]
    output_schema: dict[str, Any]


@dataclass
class EvaluationResponse:
    data: dict[str, Any]
    model: str
    usage: dict[str, int]


class EvaluationProvider(Protocol):
    name: str

    async def evaluate(self, request: EvaluationRequest) -> EvaluationResponse: ...
