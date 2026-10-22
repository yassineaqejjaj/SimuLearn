import os
import tempfile

_tmp = tempfile.mkdtemp()
os.environ.update({
    "DATABASE_URL": f"sqlite+pysqlite:///{_tmp}/test.db", "AUTH_DEV_MODE": "true", "VOICE_PROVIDER": "mock",
    "EVALUATION_PROVIDER": "mock", "APP_ENV": "test", "SIMULATION_MAX_CONCURRENT_PER_USER": "1",
})

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.db import Base, get_engine, session_scope  # noqa: E402
from app.main import app  # noqa: E402
from app.seed import seed_demo  # noqa: E402


@pytest.fixture()
def db_ready():
    engine = get_engine()
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with session_scope() as db:
        seed_demo(db)


@pytest.fixture()
def client(db_ready):
    with TestClient(app) as c:
        yield c


def auth(email="eleve@ifsi.test", role="learner"):
    return {"Authorization": f"Bearer dev:{email}:{role}"}
