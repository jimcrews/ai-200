from fastapi.testclient import TestClient

from fastapi_factory.config import Settings
from fastapi_factory.main import create_app


def test_health_uses_injected_settings(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "environment": "test"}


def test_echo_repeats_message(client):
    response = client.post("/echo", json={"message": "hi", "repeat_count": 3})
    assert response.status_code == 200
    assert response.json() == {
        "original": "hi",
        "echoed": "hi hi hi",
        "word_count": 3,
    }


def test_apps_from_factory_do_not_share_state():
    # Two apps, built side by side with different settings
    app_a = create_app(Settings(environment="env-a"))
    app_b = create_app(Settings(environment="env-b"))

    assert app_a is not app_b
    assert app_a.state.settings is not app_b.state.settings

    # Changing one app's state must not leak into the other
    app_a.state.counter = 1
    assert not hasattr(app_b.state, "counter")

    # Each app serves its own settings, even while both are running
    with TestClient(app_a) as client_a, TestClient(app_b) as client_b:
        assert client_a.get("/health").json()["environment"] == "env-a"
        assert client_b.get("/health").json()["environment"] == "env-b"
