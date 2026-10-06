import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

NO_KEYS: dict = {}  # empty keys -> demo mode, so tests never call a real API


@pytest.fixture
def seeded_db(tmp_path, monkeypatch):  # A temp database with the sample emails
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    from data.seed import seed

    seed()
    return tmp_path / "test.db"
