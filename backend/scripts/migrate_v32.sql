-- Change 32: encrypt sensitive values in new columns, retain masked legacy columns only.
-- Run through your database migration runner before deploying application code.
ALTER TABLE screening_records ADD COLUMN document_number_encrypted TEXT;
ALTER TABLE screening_records ADD COLUMN holder_name_encrypted TEXT;
ALTER TABLE screening_records ADD COLUMN document_number_hash VARCHAR(64);
ALTER TABLE screening_records ADD COLUMN holder_name_hash VARCHAR(64);
CREATE INDEX ix_screening_records_document_number_hash ON screening_records(document_number_hash);
CREATE INDEX ix_screening_records_holder_name_hash ON screening_records(holder_name_hash);
