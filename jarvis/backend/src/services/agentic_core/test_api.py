from fastapi.testclient import TestClient
from backend.src.main import app

client = TestClient(app)

def test_list_agents_api():
    response = client.get("/api/agentic-core/agents")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 3
    names = [a["name"] for a in data]
    assert "coder" in names
    assert "researcher" in names
    assert "code-auditor" in names

def test_list_instances_api():
    response = client.get("/api/agentic-core/instances")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
