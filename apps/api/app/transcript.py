"""Regroupe les fragments (deltas) en messages lisibles.

Un delta n'est pas un tour de parole : le groupement se fait par locuteur et par proximité
temporelle (start_ms/end_ms, non l'ordre d'arrivée).
"""
from dataclasses import dataclass

GAP_MS = 1500


@dataclass
class Fragment:
    speaker: str
    text: str
    start_ms: int
    end_ms: int
    seq: int = 0


@dataclass
class GroupedMessage:
    speaker: str
    text: str
    start_ms: int
    end_ms: int
    reliability: str = "normal"
    note: str | None = None


def group_fragments(fragments: list[Fragment], truncated: bool = False) -> list[GroupedMessage]:
    ordered = sorted(fragments, key=lambda f: (f.start_ms, f.seq))
    messages: list[GroupedMessage] = []
    for f in ordered:
        last = messages[-1] if messages else None
        if last and last.speaker == f.speaker and f.start_ms - last.end_ms <= GAP_MS:
            last.text += f.text  # delta conservés tels quels (espaces inclus)
            last.end_ms = max(last.end_ms, f.end_ms)
        else:
            messages.append(GroupedMessage(f.speaker, f.text, f.start_ms, f.end_ms))
    for i, msg in enumerate(messages):
        msg.text = " ".join(msg.text.split())
        if len(msg.text) < 2:
            msg.reliability, msg.note = "uncertain", "Passage très court ou vide, transcription douteuse."
        nxt = messages[i + 1] if i + 1 < len(messages) else None
        if nxt and msg.speaker == "character" and nxt.speaker == "learner" and nxt.start_ms < msg.end_ms:
            msg.note = "Interrompu par l'apprenant (le texte transcrit peut excéder l'audio entendu)."
            msg.reliability = "uncertain"
    if truncated and messages:
        messages[-1].reliability = "incomplete"
        messages[-1].note = "Session terminée de façon anormale : fin de transcription possiblement perdue."
    return [m for m in messages if m.text]
