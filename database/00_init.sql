-- PostgreSQL extension bootstrap for the MemoryBase course demo.
-- pgcrypto supplies gen_random_uuid() used by all UUID primary keys.
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- pg_trgm supplies trigram similarity and GIN operator classes for fuzzy
-- source/chunk/memory search paths in database/04_indexes.sql.
CREATE EXTENSION IF NOT EXISTS pg_trgm;
