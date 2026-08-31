-- Apply when upgrading an existing deployment that predates Changes 14-16.
ALTER TABLE blacklisted_documents ADD COLUMN document_type VARCHAR(30);
ALTER TABLE blacklisted_documents ADD COLUMN severity VARCHAR(20) DEFAULT 'medium';
ALTER TABLE blacklisted_documents ADD COLUMN status VARCHAR(20) DEFAULT 'active';
