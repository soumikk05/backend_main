-- SQL Migration: Add date_of_birth column to screening_records table.
-- Enables cross-document identity consistency checks (same document number
-- or holder name previously screened under a conflicting date of birth).
-- Fixes: duplicate-identity check silently ignored DOB conflicts because the
-- column didn't exist, regardless of what registry_service.py compared.

ALTER TABLE screening_records ADD COLUMN date_of_birth VARCHAR(20);