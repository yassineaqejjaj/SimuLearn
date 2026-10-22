"""Vérification déterministe des citations produites par l'évaluateur."""
import difflib
import re
import unicodedata
from dataclasses import dataclass
from typing import Mapping


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFD", s.lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return " ".join(re.sub(r"[^\w\s]", " ", s).split())


@dataclass
class StoredMessage:
    id: str
    session_id: str
    speaker: str
    text: str
    start_ms: int
    end_ms: int


@dataclass
class EvidenceCheck:
    ok: bool
    reason: str = ""


def quote_in_text(quote: str, text: str, threshold: float = 0.9) -> bool:
    q, t = _norm(quote), _norm(text)
    if len(q) < 6:  # trop court pour être une preuve
        return False
    if q in t:
        return True
    # tolérance aux micro-différences de transcription : meilleure fenêtre de mots
    qw, tw = q.split(), t.split()
    if len(tw) < len(qw):
        return difflib.SequenceMatcher(None, q, t).ratio() >= threshold
    best = max(
        difflib.SequenceMatcher(None, q, " ".join(tw[i:i + len(qw)])).ratio()
        for i in range(len(tw) - len(qw) + 1)
    )
    return best >= threshold


def verify_evidence(session_id: str, message_id: str, speaker: str | None, quote: str,
                    messages: Mapping[str, StoredMessage]) -> EvidenceCheck:
    msg = messages.get(message_id)
    if msg is None:
        return EvidenceCheck(False, "message_inconnu")
    if msg.session_id != session_id:
        return EvidenceCheck(False, "autre_session")
    if speaker is not None and speaker != msg.speaker:
        return EvidenceCheck(False, "locuteur_incorrect")
    if not quote_in_text(quote, msg.text):
        return EvidenceCheck(False, "citation_absente")
    return EvidenceCheck(True)
