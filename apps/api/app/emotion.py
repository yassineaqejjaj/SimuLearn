"""État émotionnel interne du personnage. Transitions déterministes, bornées 0..100.

Les valeurs sont des variables de scénario, pas des mesures psychologiques.
Les signaux (`empathy`, `curt`, ...) sont détectés par des règles simples sur la parole
de l'apprenant ; une analyse Claude optionnelle peut proposer des signaux, mais le backend
n'accepte que ceux déclarés dans `emotion_rules` du scénario.
"""
import re
import unicodedata
from dataclasses import dataclass, field

DIMENSIONS = ("frustration", "trust", "anxiety", "cooperation")
MAJOR_CHANGE = 10  # delta cumulé qui justifie une entrée de journal


def _norm(text: str) -> str:
    text = unicodedata.normalize("NFD", text.lower())
    return "".join(c for c in text if unicodedata.category(c) != "Mn")


_PATTERNS = {
    "empathy": r"je comprends|c'est normal|desole|je vois que|ca doit etre|je me doute|j'imagine",
    "rephrase": r"si je comprends bien|vous (etes|avez|craignez|attendez)|ce qui vous inquiete|vous me dites",
    "curt": r"on n'y peut rien|c'est comme ca|calmez-vous|ce n'est pas mon probleme|je n'ai pas le temps|vous n'avez qu'a",
    "credible_next_step": r"(je vais|je vous) (prevenir|informer|annoncer|appeler|demander)|l'equipe va|le medecin (va|passera)|dans quelques minutes|prochaine etape|ensuite",
    "unrealistic_promise": r"je vous garantis|c'est sur que|promis|vous passerez dans (cinq|5|dix|10) minutes|aucun risque|tout ira bien",
    "jargon": r"anamnese|bilan preanesthesique|voie veineuse|pec |iatrogene|bio ?logie|monitoring|protocole",
}
_COMPILED = {k: re.compile(v) for k, v in _PATTERNS.items()}


def detect_signals(learner_text: str) -> list[str]:
    t = _norm(learner_text)
    found = [name for name, rx in _COMPILED.items() if rx.search(t)]
    if len(t.split()) <= 3 and not found and t.strip():
        found.append("curt")
    return found


def label_emotion(state: dict) -> str:
    f, t = state["frustration"], state["trust"]
    if f >= 65:
        return "frustrated"
    if f >= 40 or t < 40:
        return "wary"
    return "calmer"


@dataclass
class EmotionManager:
    rules: dict
    state: dict
    history: list[dict] = field(default_factory=list)

    def apply(self, signals: list[str], offset_ms: int | None = None) -> dict | None:
        """Applique les signaux autorisés. Retourne l'entrée de journal si changement majeur."""
        before = dict(self.state)
        for sig in signals:
            for dim, delta in self.rules.get(sig, {}).items():
                if dim in DIMENSIONS:
                    self.state[dim] = max(0, min(100, self.state[dim] + delta))
        self.state["emotion"] = label_emotion(self.state)
        moved = sum(abs(self.state[d] - before[d]) for d in DIMENSIONS)
        if moved >= MAJOR_CHANGE or self.state["emotion"] != before["emotion"]:
            entry = {"state": dict(self.state), "cause": ",".join(signals) or "none", "offset_ms": offset_ms}
            self.history.append(entry)
            return entry
        return None

    def guidance_line(self) -> str:
        """Instruction courte transmise au moteur vocal (jamais de valeurs numériques)."""
        s = self.state
        mood = {"frustrated": "encore très agacé", "wary": "méfiant mais plus à l'écoute", "calmer": "plus calme"}[s["emotion"]]
        coop = "peu coopératif" if s["cooperation"] < 40 else "plus disposé à coopérer" if s["cooperation"] < 70 else "coopératif"
        return f"Marc est maintenant {mood} et {coop}. Garde un apaisement progressif, pas brutal."
