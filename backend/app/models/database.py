"""
SQLAlchemy ORM models for digital audit trails and identity blacklist registries.
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Float, DateTime, JSON, Text, Integer, SmallInteger

from app.db import Base


class ScreeningRecord(Base):
    """
    Persistent audit record for every document screening analysis.
    Satisfies SIH requirement: 'Create a digital trail for investigations and intelligence analysis.'
    """
    __tablename__ = "screening_records"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_type = Column(String(50), nullable=True, default="UNKNOWN")
    document_number = Column(String(100), nullable=True, index=True)
    holder_name = Column(String(200), nullable=True, index=True)
    date_of_birth = Column(String(20), nullable=True, index=True)
    document_number_encrypted = Column(Text, nullable=True)
    holder_name_encrypted = Column(Text, nullable=True)
    document_number_hash = Column(String(64), nullable=True, index=True)
    holder_name_hash = Column(String(64), nullable=True, index=True)
    image_hash = Column(String(64), nullable=True, index=True)

    extracted_fields = Column(JSON, nullable=True)
    validation_result = Column(JSON, nullable=True)
    tampering_result = Column(JSON, nullable=True)
    face_result = Column(JSON, nullable=True)
    registry_result = Column(JSON, nullable=True)

    risk_score = Column(Float, nullable=False, default=0.0)
    risk_label = Column(String(20), nullable=False, default="LOW")
    flags = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    def to_dict(self):
        return {
            "id": self.id,
            "document_type": self.document_type,
            "document_number": self.document_number,
            "holder_name": self.holder_name,
            "date_of_birth": self.date_of_birth,
            "image_hash": self.image_hash,
            "extracted_fields": self.extracted_fields,
            "validation_result": self.validation_result,
            "tampering_result": self.tampering_result,
            "face_result": self.face_result,
            "registry_result": self.registry_result,
            "risk_score": self.risk_score,
            "risk_label": self.risk_label,
            "flags": self.flags or [],
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class BlacklistedDocument(Base):
    """
    Registry of stolen, lost, or flagged identity and travel documents.
    """
    __tablename__ = "blacklisted_documents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_number = Column(String(100), unique=True, index=True, nullable=False)
    reason = Column(String(255), nullable=False)
    country = Column(String(50), nullable=True)
    document_type = Column(String(30), nullable=True)
    severity = Column(String(20), nullable=False, default="medium")
    status = Column(String(20), nullable=False, default="active")
    added_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "document_number": self.document_number,
            "reason": self.reason,
            "country": self.country,
            "document_type": self.document_type,
            "severity": self.severity,
            "status": self.status,
            "added_at": self.added_at.isoformat() if self.added_at else None,
        }


class FaceEmbedding(Base):
    __tablename__ = "face_embeddings"
    embedding_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    person_id = Column(String(100), nullable=False, index=True)
    embedding_vector = Column(JSON, nullable=False)
    embedding_hash = Column(String(64), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class IdentityCluster(Base):
    __tablename__ = "identity_clusters"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    person_id = Column(String(100), nullable=False, index=True)
    document_number = Column(String(100), nullable=True, index=True)
    holder_name = Column(String(200), nullable=True)
    evidence = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    screening_id = Column(String(36), nullable=False, index=True)
    timestamp = Column(String(40), nullable=False)
    officer = Column(String(100), nullable=True)
    document_hash = Column(String(64), nullable=True)
    document_type = Column(String(50), nullable=True)       # v2: included in hash
    risk = Column(Float, nullable=False, default=0.0)
    risk_score = Column(Float, nullable=False, default=0.0)
    risk_category = Column(String(20), nullable=True)
    decision = Column(String(50), nullable=True)
    modules = Column(JSON, nullable=True)
    processing_time_ms = Column(Float, nullable=True)
    previous_hash = Column(String(64), nullable=False)
    audit_hash = Column(String(64), nullable=False, unique=True, index=True)
    audit_hash_version = Column(SmallInteger, nullable=False, default=2)  # 1=legacy, 2=full
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class ProcessingMetric(Base):
    __tablename__ = "processing_metrics"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    screening_id = Column(String(36), nullable=False, index=True)
    timings = Column(JSON, nullable=False)
    total_ms = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)