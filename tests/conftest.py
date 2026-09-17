import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Tests run against a fixed copy of the data so refreshing app/data never breaks them
os.environ["PODCAST_DATA_DIR"] = str(Path(__file__).parent / "fixtures")

from app.main import app  # noqa: E402
from app.store import get_catalogue  # noqa: E402


@pytest.fixture
def client():
    get_catalogue.cache_clear()
    with TestClient(app) as test_client:
        yield test_client
