"""Parcours vertical avec fournisseurs MOCK : ne prouve PAS l'intégration réelle GPT-Live / Claude."""
import time

from tests.conftest import auth

LEARNER = ["Bonjour monsieur Laurent, je suis étudiant infirmier et je vais m'occuper de vous.",
           "Je comprends que cette attente vous inquiète, vous attendez depuis longtemps sans explication.",
           "L'équipe va vous informer dans quelques minutes de la prochaine étape."]


def _scenario(client, h):
    return client.get("/api/scenarios", headers=h).json()[0]


def play(client, h, turns=LEARNER):
    sv = _scenario(client, h)
    s = client.post("/api/simulations", json={"scenario_version_id": sv["id"]}, headers=h)
    assert s.status_code == 201, s.text
    sid = s.json()["id"]
    c = client.post(f"/api/simulations/{sid}/connect", json={}, headers=h)
    assert c.status_code == 200 and c.json()["sdp"] is None
    for t in turns:
        assert client.post(f"/api/simulations/{sid}/mock-turn", json={"text": t}, headers=h).status_code == 200
    end = client.post(f"/api/simulations/{sid}/end", headers=h)
    assert end.status_code == 200
    return sid


def wait_eval(client, h, sid):
    for _ in range(50):
        r = client.get(f"/api/simulations/{sid}/evaluation", headers=h).json()
        if r.get("competencies"):
            return r
        time.sleep(0.1)
    raise AssertionError(r)


def test_full_path_two_attempts_and_comparison(client):
    h = auth()
    sid1 = play(client, h)
    assert client.get(f"/api/simulations/{sid1}", headers=h).json()["status"] == "COMPLETED"
    msgs = client.get(f"/api/simulations/{sid1}/messages", headers=h).json()
    assert {m["speaker"] for m in msgs} == {"learner", "character"}
    ev1 = wait_eval(client, h, sid1)
    assert ev1["provider"] == "mock" and len(ev1["competencies"]) == 7
    for c in ev1["competencies"]:
        for e in c["evidence"]:  # chaque preuve existe dans la transcription enregistrée
            assert any(m["id"] == e["message_id"] and e["quote"][:30] in m["text"] for m in msgs)
    sid2 = play(client, h, LEARNER[:2])
    ev2 = wait_eval(client, h, sid2)
    cmp = client.get(f"/api/compare?a={ev1['id']}&b={ev2['id']}", headers=h)
    assert cmp.status_code == 200 and len(cmp.json()["competencies"]) == 7
    hist = client.get("/api/simulations", headers=h).json()
    assert len(hist) == 2 and len(hist[0]["competencies"]) == 7 and "average_score" not in hist[0]
    assert hist[0]["scenario_id"] == hist[1]["scenario_id"] and hist[0]["duration_s"] is not None
    me = client.get("/api/me", headers=h).json()
    assert me["email"] == "eleve@ifsi.test" and me["organization"]
    costs = client.get(f"/api/simulations/{sid1}/costs", headers=h).json()
    assert any(u["kind"] == "evaluation" for u in costs["usage"])


def test_second_concurrent_session_rejected(client):
    h = auth()
    sv = _scenario(client, h)
    assert client.post("/api/simulations", json={"scenario_version_id": sv["id"]}, headers=h).status_code == 201
    assert client.post("/api/simulations", json={"scenario_version_id": sv["id"]}, headers=h).status_code == 429


def test_unauthenticated_and_bad_token(client):
    assert client.get("/api/scenarios").status_code == 401
    assert client.get("/api/scenarios", headers={"Authorization": "Bearer garbage"}).status_code in (401, 503)


def test_learner_cannot_see_other_learner_or_trainer_routes(client):
    sid = play(client, auth("a@ifsi.test"))
    assert client.get(f"/api/simulations/{sid}", headers=auth("b@ifsi.test")).status_code == 404
    assert client.get(f"/api/simulations/{sid}/messages", headers=auth("b@ifsi.test")).status_code == 404
    assert client.get("/api/trainer/sessions", headers=auth("b@ifsi.test")).status_code == 403
    assert client.get("/api/trainer/sessions", headers=auth("f@ifsi.test", "trainer")).status_code == 200


def test_organization_isolation(client):
    from app import models as m
    from app.db import session_scope
    from app.seed import seed_demo  # noqa: F401
    sid = play(client, auth("a@ifsi.test"))
    with session_scope() as db:  # un utilisateur d'une autre organisation
        other = m.Organization(name="Autre")
        db.add(other)
        db.flush()
        u = m.User(email="x@autre.test")
        db.add(u)
        db.flush()
        db.add(m.Membership(user_id=u.id, organization_id=other.id, role="trainer"))
        db.commit()
    # le mode dev rattache à la 1re organisation : on teste donc directement la requête métier
    from fastapi import HTTPException
    from app.auth import Principal
    from app.routers.simulations import _own_session
    import uuid
    with session_scope() as db:
        u = db.query(m.User).filter_by(email="x@autre.test").one()
        org = db.query(m.Membership).filter_by(user_id=u.id).one().organization_id
        try:
            _own_session(db, uuid.UUID(sid), Principal(u, org, "trainer"))
            raise AssertionError("fuite inter-organisation")
        except HTTPException as e:
            assert e.status_code == 404


def test_trainer_review_keeps_claude_output_and_updates_comparison(client):
    h, t = auth("a@ifsi.test"), auth("f@ifsi.test", "trainer")
    sid = play(client, h)
    ev = wait_eval(client, h, sid)
    key = next(c["competency_id"] for c in ev["competencies"] if c["score"])
    r = client.post(f"/api/trainer/evaluations/{ev['id']}/reviews", json={"competency_key": key, "corrected_score": 1, "comment": "Trop sec"}, headers=t)
    assert r.status_code == 201
    after = client.get(f"/api/simulations/{sid}/evaluation", headers=h).json()
    c = next(c for c in after["competencies"] if c["competency_id"] == key)
    original = next(x for x in ev["competencies"] if x["competency_id"] == key)["score"]
    assert c["trainer_correction"]["score"] == 1 and c["score"] == original  # score Claude inchangé, correction à part
    raw = client.get(f"/api/trainer/evaluations/{ev['id']}", headers=t).json()["raw_output"]
    assert raw["competencies"], "la sortie initiale reste intacte"
    assert after["trainer_review_status"] == "corrected"


def test_incompatible_frameworks_not_compared(client):
    from app import models as m
    from app.db import session_scope
    h = auth()
    a, b = wait_eval(client, h, play(client, h)), wait_eval(client, h, play(client, h))
    with session_scope() as db:
        ev = db.get(m.Evaluation, __import__("uuid").UUID(b["id"]))
        fw = m.CompetencyFramework(organization_id=db.get(m.CompetencyFramework, ev.framework_id).organization_id, key="autre", version=2, title="v2")
        db.add(fw)
        db.flush()
        ev.framework_id = fw.id
        db.commit()
    assert client.get(f"/api/compare?a={a['id']}&b={b['id']}", headers=h).status_code == 422


def test_privacy_export_and_delete(client):
    h = auth()
    sid = play(client, h)
    wait_eval(client, h, sid)
    assert client.get("/api/me/export", headers=h).json()["sessions"][0]["messages"]
    assert client.delete("/api/me/data", headers=h).status_code == 204
    assert client.get(f"/api/simulations/{sid}/messages", headers=h).json() == []


def test_learner_view_hides_internal_scenario_data(client):
    sv = _scenario(client, auth())
    assert sv["category"] == "Communication patient"
    blob = str(sv).lower()
    assert "withheld" not in blob and "behavior_rules" not in blob and "frustration" not in blob


def test_scenario_update_creates_new_version(client):
    t = auth("f@ifsi.test", "trainer")
    fw = client.get("/api/trainer/frameworks", headers=t).json()[0]["id"]
    sc = client.get("/api/trainer/scenarios", headers=t).json()[0]
    from app.seed import SCENARIO, CHARACTER
    body = {**{k: v for k, v in SCENARIO.items() if k not in ("slug",)}, "framework_id": fw, "character": CHARACTER, "title": "Titre v2", "category": "Situations difficiles"}
    r = client.put(f"/api/trainer/scenarios/{sc['scenario_id']}", json=body, headers=t)
    assert r.status_code == 200 and r.json()["version"] == 2
    titles = {x["version"]: x["title"] for x in client.get("/api/trainer/scenarios", headers=t).json()}
    assert titles[1] != "Titre v2" and titles[2] == "Titre v2"
    cats = {x["version"]: x for x in client.get("/api/scenarios", headers=auth()).json()}
    assert cats[2]["category"] == "Situations difficiles"  # le catalogue montre la dernière version publiée


def test_parallel_first_requests_do_not_conflict(client):
    """Régression : la 1re page déclenche plusieurs requêtes simultanées pour un nouvel utilisateur."""
    from concurrent.futures import ThreadPoolExecutor
    h = auth("nouveau.venu@ifsi.test")
    paths = ["/api/scenarios", "/api/me", "/api/simulations"] * 3
    with ThreadPoolExecutor(9) as ex:
        codes = list(ex.map(lambda p: client.get(p, headers=h).status_code, paths))
    assert codes == [200] * 9
