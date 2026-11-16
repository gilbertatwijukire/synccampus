import os, tempfile
_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp.name}"
os.environ["ESCALATION_CHECK_SECONDS"] = "99999"

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import Base, engine, SessionLocal
from app.seed import seed


@pytest.fixture()
def client():
    Base.metadata.drop_all(engine); Base.metadata.create_all(engine)
    with SessionLocal() as db:
        seed(db)
    with TestClient(app) as c:
        yield c


def login(client, email):
    r = client.post("/api/auth/login", data={"username": email, "password": "ChangeMe123!"})
    assert r.status_code == 200, r.text
    return {"Authorization": "Bearer " + r.json()["access_token"]}
