"""One-time backfill: encrypt and mask legacy screening-record PII after migrate_v32.sql."""
from app.db import SessionLocal, init_db
from app.models.database import ScreeningRecord
from app.services.privacy_service import encrypt_value, lookup_hash, mask_identifier, mask_name

def main() -> None:
    init_db(); db = SessionLocal(); updated = 0
    try:
        for record in db.query(ScreeningRecord).filter(ScreeningRecord.document_number_encrypted.is_(None)).yield_per(100):
            raw_document, raw_name = record.document_number, record.holder_name
            record.document_number_encrypted, record.holder_name_encrypted = encrypt_value(raw_document), encrypt_value(raw_name)
            record.document_number_hash, record.holder_name_hash = lookup_hash(raw_document), lookup_hash(raw_name)
            record.document_number, record.holder_name = mask_identifier(raw_document), mask_name(raw_name)
            updated += 1
        db.commit(); print(f"Migrated {updated} screening record(s).")
    finally:
        db.close()

if __name__ == "__main__": main()
