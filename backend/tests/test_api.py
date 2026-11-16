from datetime import timedelta
from app.database import SessionLocal
from app.models import Concern, now
from .conftest import login


def submit(client, **over):
    body = dict(title="Wi-Fi not working in Block B library", description="No internet for students in the Block B library since morning",
                category_id=6, campus="City Campus", location="Block B", urgency=3, students_affected=10, is_public=True)
    body.update(over)
    r = client.post("/api/concerns", json=body)
    assert r.status_code == 201, r.text
    return r.json()


def test_full_workflow(client):
    c1 = submit(client)
    # reworded report in same category -> linked as related, priority rises
    c2 = submit(client, title="Internet down in Block B", description="Wifi is not working for everyone in Block B", location="Block B")
    assert c2["similar_reports_found"] == 1

    pres = login(client, "president@saagi.local")
    queue = client.get("/api/leader/queue", headers=pres).json()
    assert len(queue) == 2 and all(q["related_reports"] == 1 for q in queue)
    top = queue[0]
    assert top["recommended"]["name"] == "R. Okello"           # ICT minister is the area owner

    # assign (accept recommendation) -> not an override
    a = client.post(f"/api/leader/concerns/{top['id']}/assign", json={"delegate_id": top["recommended"]["delegate_id"]}, headers=pres).json()
    assert a["was_overridden"] is False

    # delegate works on it
    okello = login(client, "okello@saagi.local")
    mine = client.get("/api/delegate/concerns", headers=okello).json()
    assert len(mine) == 1
    client.post(f"/api/delegate/concerns/{top['id']}/update", json={"message": "Checking the router", "visibility": "private", "status": "in_progress"}, headers=okello)
    client.post(f"/api/delegate/concerns/{top['id']}/update", json={"message": "Fixed", "visibility": "private", "status": "resolved"}, headers=okello)

    # student tracks with reference + code, then confirms
    tr = client.post("/api/track", json={"reference": c1["reference"], "access_code": c1["access_code"]})
    assert tr.status_code == 200
    ref_of_top = next(c for c in (c1, c2) if client.post("/api/track", json={"reference": c["reference"], "access_code": c["access_code"]}).json()["status"] == "resolved")
    r = client.post("/api/track/confirm", json={"reference": ref_of_top["reference"], "access_code": ref_of_top["access_code"], "resolved": True})
    assert r.json()["status"] == "closed"

    stats = client.get("/api/leader/analytics", headers=pres).json()
    assert stats["total"] == 2 and stats["avg_first_response_hrs"] is not None


def test_wrong_code_and_lockout(client):
    c = submit(client)
    for _ in range(5):
        assert client.post("/api/track", json={"reference": c["reference"], "access_code": "WRONG"}).status_code == 404
    assert client.post("/api/track", json={"reference": c["reference"], "access_code": c["access_code"]}).status_code == 429


def test_access_control(client):
    assert client.get("/api/leader/queue").status_code == 401
    okello = login(client, "okello@saagi.local")
    assert client.get("/api/leader/queue", headers=okello).status_code == 403   # delegates cannot see the full queue


def test_sensitive_category_forced_private_and_not_in_public_feed(client):
    cats = client.get("/api/categories").json()
    sens = next(c for c in cats if c["is_sensitive"])
    r = submit(client, category_id=sens["id"], title="Harassment by staff member", description="A staff member keeps making me uncomfortable", is_public=True)
    assert r["is_public"] is False
    assert all("Harassment" not in x["title"] for x in client.get("/api/public/concerns").json())


def test_escalation_after_time_limit(client):
    submit(client, category_id=8, urgency=4, safety_flag=True, title="Broken lab door lock Block A", description="The lock on the lab door is broken and anyone can walk in")
    with SessionLocal() as db:
        c = db.query(Concern).first()
        c.created_at = now() - timedelta(hours=7)          # Critical limit is 6h
        db.commit()
    pres = login(client, "president@saagi.local")
    fired = client.post("/api/leader/run-escalation", headers=pres).json()
    assert fired and fired[0]["type"] == "escalation"
    assert client.post("/api/leader/run-escalation", headers=pres).json() == []   # fires only once
    q = client.get("/api/leader/queue", headers=pres).json()
    assert q[0]["is_overdue"] is True


def test_override_recorded_and_handover(client):
    c = submit(client)
    pres = login(client, "president@saagi.local")
    cid = client.get("/api/leader/queue", headers=pres).json()[0]["id"]
    lubega = next(w for w in client.get("/api/leader/workload", headers=pres).json() if w["name"] == "D. Lubega")
    a = client.post(f"/api/leader/concerns/{cid}/assign", json={"delegate_id": lubega["delegate_id"]}, headers=pres).json()
    assert a["was_overridden"] is True
    h = client.post("/api/leader/handover?term=2026/27", headers=pres).json()
    assert h["count"] == 1 and h["open_concerns"][0]["assigned_to"] == "D. Lubega"


def test_public_stats_and_cabinet_expose_no_private_data(client):
    submit(client)
    cats = client.get("/api/categories").json()
    sens = next(c for c in cats if c["is_sensitive"])
    submit(client, category_id=sens["id"], title="Harassment by a staff member", description="A staff member keeps making me uncomfortable")
    s = client.get("/api/public/stats").json()
    assert s["total"] == 2 and s["open"] == 2
    assert all("Harassment" not in name for name, _ in s["top_categories"])      # sensitive categories hidden
    cab = client.get("/api/cabinet").json()
    assert cab[0]["is_president"] is True and len(cab) == 6                        # president + 5 delegates; admin not listed
    assert all("email" not in c for c in cab)


def test_admin_cannot_open_complaints(client):
    submit(client)
    admin = login(client, "admin@saagi.local")
    assert client.get("/api/leader/queue", headers=admin).status_code == 403
