from app.emotion import EmotionManager, detect_signals
from app.evidence import StoredMessage, quote_in_text, verify_evidence
from app.transcript import Fragment, group_fragments
from app.seed import SCENARIO, CHARACTER


def test_transcript_groups_by_speaker_and_time_not_arrival_order():
    frags = [Fragment("learner", " vous", 1200, 1500, 3), Fragment("learner", "Bonjour", 1000, 1200, 1),
             Fragment("character", "Enfin.", 4000, 4600, 4)]
    msgs = group_fragments(frags)
    assert [m.speaker for m in msgs] == ["learner", "character"]
    assert msgs[0].text == "Bonjour vous"


def test_transcript_marks_interrupted_and_truncated():
    frags = [Fragment("character", "Je vous explique que", 0, 5000, 1), Fragment("learner", "Excusez-moi", 3000, 4000, 2)]
    msgs = group_fragments(frags, truncated=True)
    assert msgs[0].reliability == "uncertain" and "Interrompu" in msgs[0].note
    assert msgs[-1].reliability == "incomplete"


def test_emotion_progressive_and_bounded():
    em = EmotionManager(rules=SCENARIO["emotion_rules"], state=dict(CHARACTER["initial_state"]))
    em.apply(["empathy"])
    assert em.state["frustration"] == 67 and em.state["emotion"] == "frustrated"  # une bonne réponse ne suffit pas
    for _ in range(20):
        em.apply(["empathy", "credible_next_step"])
    assert em.state["frustration"] == 0 and em.state["trust"] <= 100
    assert em.state["emotion"] == "calmer"
    assert em.history, "les changements majeurs sont journalisés"


def test_emotion_ignores_signals_not_in_scenario_rules():
    em = EmotionManager(rules={"empathy": {"trust": 5}}, state=dict(CHARACTER["initial_state"]))
    em.apply(["curt"])
    assert em.state["frustration"] == 75


def test_signal_detection():
    assert "empathy" in detect_signals("Je comprends que l'attente soit longue")
    assert "curt" in detect_signals("On n'y peut rien")
    assert "jargon" in detect_signals("Il faut une anamnèse")


def test_quote_matching_tolerant_but_strict_on_invented():
    text = "Je comprends que cette attente vous inquiète beaucoup."
    assert quote_in_text("je comprends que cette attente vous inquiete", text)
    assert not quote_in_text("Je vous garantis un passage immédiat", text)
    assert not quote_in_text("oui", "oui bien sûr")  # trop court pour être une preuve


def test_verify_evidence_rejects_wrong_session_speaker_and_unknown():
    msg = StoredMessage("m1", "s1", "learner", "Bonjour monsieur Laurent, je suis étudiant infirmier.", 0, 3000)
    msgs = {"m1": msg}
    assert verify_evidence("s1", "m1", "learner", "je suis étudiant infirmier", msgs).ok
    assert verify_evidence("s2", "m1", "learner", "je suis étudiant infirmier", msgs).reason == "autre_session"
    assert verify_evidence("s1", "m1", "character", "je suis étudiant infirmier", msgs).reason == "locuteur_incorrect"
    assert verify_evidence("s1", "zz", None, "je suis étudiant infirmier", msgs).reason == "message_inconnu"
