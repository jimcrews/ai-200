from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_root():
    r = client.get("/")
    assert r.status_code == 200
    assert r.json() == {"message": "Hello World"}

def test_health():
    assert client.get("/health").json() == {"status": "alive"}

def test_echo():
    r = client.post("/echo", json={"message": "hi", "repeat_count": 3})
    assert r.json() == {"original": "hi", "echoed": "hi hi hi"}

def test_echo_missing_message():
    assert client.post("/echo", json={}).status_code == 422