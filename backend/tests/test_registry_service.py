"""
Unit tests for Duplicate Identity and Blacklist Registry screening (Module 6).
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.models.database import BlacklistedDocument, ScreeningRecord
from app.services.registry_service import check_blacklist, check_duplicate_identity, screen_registry


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_blacklist_check_hit_and_miss(db_session):
    # Insert blacklisted document
    db_session.add(BlacklistedDocument(document_number="STOLEN999", reason="Lost passport reported to INTERPOL"))
    db_session.commit()

    hit = check_blacklist("STOLEN999", db_session)
    assert hit["is_blacklisted"] is True
    assert "INTERPOL" in hit["reason"]

    miss = check_blacklist("CLEAN123", db_session)
    assert miss["is_blacklisted"] is False


def test_duplicate_identity_detection(db_session):
    # Seed historical screening record
    db_session.add(
        ScreeningRecord(
            document_type="PASSPORT",
            document_number="DOC12345",
            holder_name="ALICE SMITH",
            image_hash="hash_aaa",
            risk_score=10.0,
            risk_label="LOW",
        )
    )
    db_session.commit()

    # Same doc number with different name
    dup_res = check_duplicate_identity("DOC12345", "BOB JONES", "hash_bbb", db_session)
    assert dup_res["is_duplicate"] is True
    assert any("DUPLICATE IDENTITY" in f for f in dup_res["flags"])
