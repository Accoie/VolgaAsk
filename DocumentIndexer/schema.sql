CREATE TABLE IF NOT EXISTS kb_catalog (
    url text PRIMARY KEY, title text NOT NULL, filename text NOT NULL,
    checksum text, available boolean NOT NULL DEFAULT true
);
ALTER TABLE kb_catalog ADD COLUMN IF NOT EXISTS etag text;
CREATE TABLE IF NOT EXISTS kb_documents (
    id uuid PRIMARY KEY, title text NOT NULL, filename text NOT NULL,
    document_date date, checksum text NOT NULL, source text,
    status text NOT NULL CHECK (status IN ('queued','indexing','ready','failed','deleting')),
    error_code text, payload bytea, created_at timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE kb_documents ADD COLUMN IF NOT EXISTS ocr_applied boolean NOT NULL DEFAULT false;
CREATE UNIQUE INDEX IF NOT EXISTS kb_active_checksum ON kb_documents(checksum) WHERE status <> 'failed';
CREATE TABLE IF NOT EXISTS kb_seeds (checksum text PRIMARY KEY);
CREATE TABLE IF NOT EXISTS kb_sync (id boolean PRIMARY KEY DEFAULT true, refreshed timestamptz, error text);
CREATE OR REPLACE FUNCTION kb_notify() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    PERFORM pg_notify('kb_changes', '');
    RETURN NULL;
END $$;
DROP TRIGGER IF EXISTS kb_changes ON kb_documents;
CREATE TRIGGER kb_changes AFTER INSERT OR UPDATE OR DELETE ON kb_documents
FOR EACH STATEMENT EXECUTE FUNCTION kb_notify();
