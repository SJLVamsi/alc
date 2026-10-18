import pytest
import os

os.environ["DATABASE_URL"] = "sqlite:///./test.db"

from app.database import engine, Base, SessionLocal


@pytest.fixture(autouse=True)
def db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session(db):
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client():
    from app.main import app
    from fastapi.testclient import TestClient
    with TestClient(app) as c:
        yield c
