"""Test fixtures."""
import pytest
from api.app.db import Base, engine, SessionLocal


@pytest.fixture(autouse=True)
def clean_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
