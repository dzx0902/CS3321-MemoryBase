from app.api.deps import get_database
from app.main import create_app
from fastapi.testclient import TestClient


class FakeDatabase:
    def __init__(self, ok: bool, error: str | None = None) -> None:
        self.ok = ok
        self.error = error

    def ping(self) -> tuple[bool, str | None]:
        return self.ok, self.error

    def health_detail(
        self,
        *,
        workspace: str | None = None,
        agent: str | None = None,
    ) -> dict[str, object]:
        return {
            "schema": {"workspace_count": 1},
            "workspace": {
                "input": workspace,
                "workspace_id": "00000000-0000-0000-0000-000000000201",
                "slug": "cs3321-demo",
                "name": "MemoryBase Demo Workspace",
            }
            if workspace
            else None,
            "agent": {
                "input": agent,
                "agent_id": "00000000-0000-0000-0000-000000000301",
                "name": "retriever-demo",
                "status": "active",
            }
            if agent
            else None,
        }


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


def test_health_detail_returns_database_workspace_and_agent_status() -> None:
    app = create_app()
    app.dependency_overrides[get_database] = lambda: FakeDatabase(True)

    client = TestClient(app)
    response = client.get("/api/health/detail?workspace=cs3321-demo&agent=codex")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["database"] == {"status": "up", "error": None}
    assert payload["schema"]["workspace_count"] == 1
    assert payload["workspace"]["slug"] == "cs3321-demo"
    assert payload["agent"]["status"] == "active"
