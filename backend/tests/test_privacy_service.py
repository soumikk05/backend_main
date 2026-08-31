from datetime import datetime, timedelta
from app.services.privacy_service import decrypt_value, encrypt_value, lookup_hash, mask_identifier, mask_name, purge_expired_evidence

def test_sensitive_values_are_encrypted_and_masked():
    encrypted = encrypt_value("A1234567")
    assert encrypted != "A1234567"
    assert decrypt_value(encrypted) == "A1234567"
    assert mask_identifier("A1234567") == "******67"
    assert mask_name("Jane Doe") == "J*** D***"
    assert lookup_hash("a1234567") == lookup_hash("A1234567")

def test_retention_purges_only_expired_evidence(tmp_path):
    old = tmp_path / "case" / "old.jpg"; old.parent.mkdir(); old.write_bytes(b"old")
    new = tmp_path / "case" / "new.jpg"; new.write_bytes(b"new")
    old_time = (datetime.now() - timedelta(days=31)).timestamp()
    import os; os.utime(old, (old_time, old_time))
    assert purge_expired_evidence(str(tmp_path)) == 1
    assert not old.exists() and new.exists()
