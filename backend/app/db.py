"""
Database configuration and session management for audit trails and screening records.
"""

import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import DATABASE_URL

# Ensure directory for SQLite exists if sqlite is used
if DATABASE_URL.startswith("sqlite"):
    db_path = DATABASE_URL.replace("sqlite:///", "")
    db_dir = os.path.dirname(db_path)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
    engine = create_engine(
        DATABASE_URL, connect_args={"check_same_thread": False}
    )

    from sqlalchemy import event
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
else:
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """Dependency / context helper for database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all database tables and perform lightweight safe migrations."""
    import app.models.database  # noqa: F401
    Base.metadata.create_all(bind=engine)
    # Lightweight forward migration for the prototype's existing SQLite DB.
    # Production deployments should use the SQL migration in scripts/.
    if DATABASE_URL.startswith("sqlite"):
        with engine.begin() as connection:
            # Migration for blacklisted_documents
            columns = {row[1] for row in connection.execute(text("PRAGMA table_info(blacklisted_documents)"))}
            for name, definition in {"document_type": "VARCHAR(30)", "severity": "VARCHAR(20) DEFAULT 'medium'", "status": "VARCHAR(20) DEFAULT 'active'"}.items():
                if name not in columns:
                    connection.execute(text(f"ALTER TABLE blacklisted_documents ADD COLUMN {name} {definition}"))
            
            # Migration for screening_records
            screening_columns = {row[1] for row in connection.execute(text("PRAGMA table_info(screening_records)"))}
            for name, definition in {
                "document_number_encrypted": "TEXT",
                "holder_name_encrypted": "TEXT",
                "document_number_hash": "VARCHAR(64)",
                "holder_name_hash": "VARCHAR(64)",
                "document_id": "VARCHAR(36) REFERENCES documents(id)",
                "person_id": "VARCHAR(36) REFERENCES persons(id)",
                "evidence_file_path": "VARCHAR(500)",
            }.items():
                if name not in screening_columns:
                    connection.execute(text(f"ALTER TABLE screening_records ADD COLUMN {name} {definition}"))
