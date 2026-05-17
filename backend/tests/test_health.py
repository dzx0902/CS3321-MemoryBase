from app.api.deps import get_database
from app.main import create_app
from fastapi.testclient import TestClient


class FakeDatabase:
    def __init__(self, ok: bool, error: str | None = None) -> None:
        self.ok = ok
        self.error = error

    def ping(self) -> tuple[bool, str | None]:
        return self.ok, self.error


def test_health_check_ok() -> None:
    app = create_app()
    app.dependency_overrides[get_database] = lambda: FakeDatabase(True)

    client = TestClient(app)
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "MemoryBase API",
        "database": {"status": "up", "error": None},
    }


def test_health_check_returns_503_when_database_is_down() -> None:
    app = create_app()
    app.dependency_overrides[get_database] = lambda: FakeDatabase(False, "connection refused")

    client = TestClient(app)
    response = client.get("/api/health")

    assert response.status_code == 503
    assert response.json()["status"] == "degraded"
    assert response.json()["database"]["status"] == "down"
