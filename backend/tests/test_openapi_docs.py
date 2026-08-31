from fastapi.testclient import TestClient
from app.main import app

def test_openapi_describes_screening_and_error_contracts():
    schema = TestClient(app).get("/openapi.json").json()
    operation = schema["paths"]["/api/risk/assess"]["post"]
    assert operation["summary"] == "Run complete document screening"
    assert "401" in operation["responses"]
    assert "ErrorResponse" in schema["components"]["schemas"]
