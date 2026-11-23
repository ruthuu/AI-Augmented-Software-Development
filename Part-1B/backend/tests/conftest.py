from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.main import app, get_llm_client
from tests.support import FakeLLMClient


@pytest.fixture
def fake_llm() -> FakeLLMClient:
    return FakeLLMClient()


@pytest.fixture
def client(fake_llm: FakeLLMClient) -> Iterator[TestClient]:
    app.dependency_overrides[get_llm_client] = lambda: fake_llm
    yield TestClient(app)
    app.dependency_overrides.clear()
