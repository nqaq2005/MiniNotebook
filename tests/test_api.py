from fastapi.testclient import TestClient

from app.server import app


def test_fastapi_endpoints():
    client = TestClient(app)

    # 1. Serve HTML UI
    ui_resp = client.get("/")
    assert ui_resp.status_code == 200
    assert "MiniNotebook" in ui_resp.text

    # 1b. Healthz check
    health_resp = client.get("/healthz")
    assert health_resp.status_code == 200
    assert health_resp.json() == {"status": "ok"}

    # 2. Stats API
    stats_resp = client.get("/api/stats")
    assert stats_resp.status_code == 200
    data = stats_resp.json()
    assert "metrics" in data
    assert "papers" in data
    assert "graph" in data
    from src.config import settings
    assert data["config"]["llm_reasoning_effort"] == settings.llm_reasoning_effort
    assert data["config"]["llm_language"] == getattr(settings, "llm_language", "vi")

    # 3. Ask API (Vietnamese by default or explicit)
    ask_resp = client.post(
        "/api/ask",
        json={
            "question": "What are the main findings of the indexed papers?",
            "search_mode": "hybrid",
            "reasoning_effort": "medium",
            "language": "vi",
        },
    )
    assert ask_resp.status_code == 200
    ask_data = ask_resp.json()
    assert "answer" in ask_data
    assert "citations" in ask_data

    # 4. Ask API (English)
    ask_en = client.post(
        "/api/ask",
        json={
            "question": "Compare the core methodologies",
            "search_mode": "hybrid",
            "language": "en",
            "paper_id_filter": "non_existent_paper_id",
        },
    )
    assert ask_en.status_code == 200
    assert "answer" in ask_en.json()

    # 5. Security: Upload rejection for invalid PDF signature (SEC-05)
    upload_fake = client.post(
        "/api/upload",
        files={"file": ("fake.pdf", b"This is not a real PDF file", "application/pdf")},
    )
    assert upload_fake.status_code == 400
    assert "Invalid PDF" in upload_fake.json()["detail"]
