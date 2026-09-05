"""
SQLAlchemy ORM models for digital audit trails and identity blacklist registries.
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Float, DateTime, JSON, Text, Integer, SmallInteger, Boolean, ForeignKey
from sqlalchemy.orm import relationship

from app.db import Base


class Person(Base):
    """
    Canonical person / identity entity.
    Groups multiple documents and face embeddings under one resolved individual.
    """
    __tablename__ = "persons"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    primary_name = Column(String(200), nullable=True, index=True)
    primary_name_hash = Column(String(64), nullable=True, index=True)
    date_of_birth = Column(String(20), nullable=True, index=True)
    nationality = Column(String(50), nullable=True)
    gender = Column(String(10), nullable=True)
    verification_status = Column(String(20), nullable=False, default="UNVERIFIED", index=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    documents = relationship("Document", back_populates="person")
    screenings = relationship("ScreeningRecord", back_populates="person")

    def to_dict(self):
        return {
            "id": self.id,
            "primary_name": self.primary_name,
            "date_of_birth": self.date_of_birth,
            "nationality": self.nationality,
            "gender": self.gender,
            "verification_status": self.verification_status,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class Document(Base):
    """
    Persistent document entity representing a physical or digital identity document.
    Enables repeat screenings of the same document and cross-document validation.
    """
    __tablename__ = "documents"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    person_id = Column(String(36), ForeignKey("persons.id"), nullable=True, index=True)
    document_type = Column(String(50), nullable=False, index=True)
    document_number = Column(String(100), nullable=True, index=True)
    document_number_encrypted = Column(Text, nullable=True)
    document_number_hash = Column(String(64), nullable=True, index=True)
    issuing_country = Column(String(50), nullable=True)
    issue_date = Column(String(20), nullable=True)
    expiry_date = Column(String(20), nullable=True)
    verification_status = Column(String(20), nullable=False, default="UNVERIFIED", index=True)
    primary_image_hash = Column(String(64), nullable=True, index=True)
    evidence_file_path = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    person = relationship("Person", back_populates="documents")
    screenings = relationship("ScreeningRecord", back_populates="document")

    def to_dict(self):
        return {
            "id": self.id,
            "person_id": self.person_id,
            "document_type": self.document_type,
            "document_number": self.document_number,
            "issuing_country": self.issuing_country,
            "issue_date": self.issue_date,
            "expiry_date": self.expiry_date,
            "verification_status": self.verification_status,
            "primary_image_hash": self.primary_image_hash,
            "evidence_file_path": self.evidence_file_path,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class ScreeningRecord(Base):
    """
    Persistent audit record for every document screening analysis.
    Satisfies SIH requirement: 'Create a digital trail for investigations and intelligence analysis.'
    """
    __tablename__ = "screening_records"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String(36), ForeignKey("documents.id"), nullable=True, index=True)
    person_id = Column(String(36), ForeignKey("persons.id"), nullable=True, index=True)
    evidence_file_path = Column(String(500), nullable=True)

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

    document = relationship("Document", back_populates="screenings")
    person = relationship("Person", back_populates="screenings")
    cross_comparisons = relationship("CrossDocumentComparison", back_populates="screening")

    def to_dict(self):
        return {
            "id": self.id,
            "document_id": self.document_id,
            "person_id": self.person_id,
            "evidence_file_path": self.evidence_file_path,
            "document_type": self.document_type,
            "document_number": self.document_number,
            "document_number_hash": self.document_number_hash,
            "document_number_encrypted": self.document_number_encrypted,
            "holder_name": self.holder_name,
            "holder_name_hash": self.holder_name_hash,
            "holder_name_encrypted": self.holder_name_encrypted,
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


class CrossDocumentComparison(Base):
    """
    Stores field-level comparison results between the current document and trusted historical records.
    Provides structured explainable evidence for cross-document consistency checks.
    """
    __tablename__ = "cross_document_comparisons"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    screening_id = Column(String(36), ForeignKey("screening_records.id"), nullable=False, index=True)
    person_id = Column(String(36), ForeignKey("persons.id"), nullable=True, index=True)
    current_document_id = Column(String(36), ForeignKey("documents.id"), nullable=False, index=True)
    trusted_document_id = Column(String(36), ForeignKey("documents.id"), nullable=False, index=True)

    field_name = Column(String(50), nullable=False, index=True)
    current_value = Column(String(255), nullable=True)
    trusted_value = Column(String(255), nullable=True)
    current_confidence = Column(Float, nullable=True)
    trusted_confidence = Column(Float, nullable=True)
    is_match = Column(Boolean, nullable=False, index=True)
    severity = Column(String(20), nullable=False, default="MEDIUM")
    reason = Column(String(255), nullable=True)
    risk_points_assigned = Column(Float, nullable=False, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    screening = relationship("ScreeningRecord", back_populates="cross_comparisons")

    def to_dict(self):
        return {
            "id": self.id,
            "screening_id": self.screening_id,
            "person_id": self.person_id,
            "current_document_id": self.current_document_id,
            "trusted_document_id": self.trusted_document_id,
            "field_name": self.field_name,
            "current_value": self.current_value,
            "trusted_value": self.trusted_value,
            "current_confidence": self.current_confidence,
            "trusted_confidence": self.trusted_confidence,
            "is_match": self.is_match,
            "severity": self.severity,
            "reason": self.reason,
            "risk_points_assigned": self.risk_points_assigned,
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


class User(Base):
    """
    User account for screening officers, investigators, and system administrators.
    Passwords are encrypted/hashed using salted bcrypt.
    """
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(200), nullable=True)
    role = Column(String(30), nullable=False, default="officer", index=True)  # 'officer', 'investigator', 'admin'
    badge_number = Column(String(50), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    last_login_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "full_name": self.full_name,
            "role": self.role,
            "badge_number": self.badge_number,
            "is_active": self.is_active,
            "last_login_at": self.last_login_at.isoformat() if self.last_login_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class UserLoginSession(Base):
    """
    Audit log of officer and investigator terminal logins.
    Tracks authentication timestamp, terminal IP, badge, and screening activity.
    """
    __tablename__ = "user_login_sessions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), nullable=False, index=True)
    username = Column(String(100), nullable=False, index=True)
    full_name = Column(String(200), nullable=True)
    role = Column(String(30), nullable=False, default="officer")
    badge_number = Column(String(50), nullable=True)
    login_timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    terminal_ip = Column(String(45), nullable=True, default="127.0.0.1")
    terminal_device = Column(String(200), nullable=True, default="Govt Screening Station #1")
    auth_method = Column(String(50), default="SALTED_BCRYPT_JWT")
    session_status = Column(String(20), default="ACTIVE")
    screenings_conducted = Column(Integer, default=0)
    token_preview = Column(String(100), nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "username": self.username,
            "full_name": self.full_name,
            "role": self.role,
            "badge_number": self.badge_number,
            "login_timestamp": self.login_timestamp.isoformat() if self.login_timestamp else None,
            "terminal_ip": self.terminal_ip,
            "terminal_device": self.terminal_device,
            "auth_method": self.auth_method,
            "session_status": self.session_status,
            "screenings_conducted": self.screenings_conducted,
            "token_preview": self.token_preview,
        }


class AdminLoginSession(Base):
    """
    High-security audit log for System Administrators and Directorate log-ins.
    Stores clearance level, MFA verification, and authorized security privileges.
    """
    __tablename__ = "admin_login_sessions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    admin_id = Column(String(36), nullable=False, index=True)
    username = Column(String(100), nullable=False, index=True)
    full_name = Column(String(200), nullable=True)
    role = Column(String(30), nullable=False, default="admin")
    badge_number = Column(String(50), nullable=True)
    login_timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    terminal_ip = Column(String(45), nullable=True, default="10.0.4.1 (Bureau Secure Subnet)")
    security_clearance = Column(String(50), default="LEVEL_5_DIRECTORATE")
    mfa_status = Column(String(50), default="VERIFIED_PKI_HARDWARE_KEY")
    authorized_actions = Column(String(255), default="USER_MGMT, SYSTEM_AUDIT, KEY_ROTATION, BLACKLIST_OVERRIDE")
    auth_method = Column(String(50), default="SALTED_BCRYPT_JWT_MFA")
    session_status = Column(String(20), default="ACTIVE")
    token_preview = Column(String(100), nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "admin_id": self.admin_id,
            "username": self.username,
            "full_name": self.full_name,
            "role": self.role,
            "badge_number": self.badge_number,
            "login_timestamp": self.login_timestamp.isoformat() if self.login_timestamp else None,
            "terminal_ip": self.terminal_ip,
            "security_clearance": self.security_clearance,
            "mfa_status": self.mfa_status,
            "authorized_actions": self.authorized_actions,
            "auth_method": self.auth_method,
            "session_status": self.session_status,
            "token_preview": self.token_preview,
        }