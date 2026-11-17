import os
import sys
import tempfile
from pathlib import Path

_tmp = tempfile.mkdtemp(prefix="asesor_test_")
os.environ.update({
    "DATABASE_URL": f"sqlite:///{_tmp}/test.db", "SECRET_KEY": "clave-de-pruebas", "ENTORNO": "pruebas",
    "ADMIN_EMAIL": "admin@test.co", "ADMIN_PASSWORD": "Admin12345", "IA_PROVEEDOR": "simulado",
    "SEED_DEMO": "false", "REGISTRO_ABIERTO": "true", "FRONTEND_DIST": f"{_tmp}/sin_frontend",
    "GEMINI_API_KEY": "", "OPENAI_API_KEY": "", "ANTHROPIC_API_KEY": "",
})
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture(scope="session")
def cliente():
    from app.main import app
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session")
def admin(cliente):
    r = cliente.post("/api/auth/login", json={"email": "admin@test.co", "password": "Admin12345"})
    assert r.status_code == 200, r.text
    return {"Authorization": "Bearer " + r.json()["token"]}


def rubrica_ejemplo():
    from app.seed_datos import LABS
    return LABS[0]["rubrica"]
