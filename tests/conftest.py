import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.db import create_demo_users, get_db
from app.main import app


@pytest.fixture
def test_engine():
    eng = create_engine("sqlite://", connect_args={"check_same_thread": False},
                        poolclass=StaticPool)
    SQLModel.metadata.create_all(eng)
    with Session(eng) as db:
        create_demo_users(db)
    yield eng
    eng.dispose()


@pytest.fixture
def login_as(test_engine):
    def _db():
        with Session(test_engine) as db:
            yield db

    app.dependency_overrides[get_db] = _db

    def _client(account=None, password="pass1234"):
        c = TestClient(app)
        if account:
            res = c.post("/api/auth/login", json={"account": account, "password": password})
            assert res.status_code == 200, res.text
        return c

    yield _client
    app.dependency_overrides.clear()


@pytest.fixture
def stu(login_as):
    return login_as("s001")


@pytest.fixture
def teacher(login_as):
    return login_as("t001")
