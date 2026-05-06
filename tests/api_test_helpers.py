def make_client():
    from fastapi.testclient import TestClient

    from backend.api.server import app
    return TestClient(app)
