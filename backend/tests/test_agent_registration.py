from __future__ import annotations


def test_register_agent_uses_workspace_slug_and_is_idempotent(integration_client) -> None:
    first = integration_client.post(
        "/api/agents/register",
        json={"workspace": "cs3321-demo", "name": "codex", "agent_type": "editor"},
    )
    second = integration_client.post(
        "/api/agents/register",
        json={"workspace": "cs3321-demo", "name": "codex", "agent_type": "reviewer"},
    )

    assert first.status_code == 201
    assert second.status_code == 201
    assert second.json()["agent_id"] == first.json()["agent_id"]
    assert second.json()["agent_type"] == "reviewer"


def test_register_agent_rejects_unknown_workspace(integration_client) -> None:
    response = integration_client.post(
        "/api/agents/register",
        json={"workspace": "missing", "name": "codex", "agent_type": "editor"},
    )

    assert response.status_code == 404
