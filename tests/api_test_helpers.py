def make_client():
    from fastapi.testclient import TestClient

    from services.api_server import app
    return TestClient(app)
