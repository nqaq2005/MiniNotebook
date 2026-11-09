from fastapi.testclient import TestClient

from app.server import app


def test_fastapi_endpoints():
    client = TestClient(app)

    # 1. Serve HTML UI
    ui_resp = client.get("/")
    assert ui_resp.status_code == 200
    assert "ScholarRAG" in ui_resp.text

    # 2. Stats API
    stats_resp = client.get("/api/stats")
    assert stats_resp.status_code == 200
    data = stats_resp.json()
    assert "metrics" in data
    assert "papers" in data
    assert "graph" in data

    # 3. Ask API
    ask_resp = client.post(
        "/api/ask",
        json={
            "question": "What are the main findings of the indexed papers?",
            "search_mode": "hybrid",
        },
    )
    assert ask_resp.status_code == 200
    ask_data = ask_resp.json()
    assert "answer" in ask_data
    assert "citations" in ask_data
