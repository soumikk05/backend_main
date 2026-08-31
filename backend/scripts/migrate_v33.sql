-- SQL Migration: Add document_type and audit_hash_version columns to audit_logs table.
-- Supporting audit v2 hash chaining and backward compatibility.

ALTER TABLE audit_logs ADD COLUMN document_type VARCHAR(50);
ALTER TABLE audit_logs ADD COLUMN audit_hash_version SMALLINT DEFAULT 2;

-- Set existing records to version 1 (legacy payload format)
UPDATE audit_logs SET audit_hash_version = 1;
