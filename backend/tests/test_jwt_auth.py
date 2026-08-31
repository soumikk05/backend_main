from app.auth import create_access_token, decode_access_token

def test_jwt_round_trip():
    token = create_access_token("alice", "auditor")
    assert decode_access_token(token)["role"] == "auditor"
