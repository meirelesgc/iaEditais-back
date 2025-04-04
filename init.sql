CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE TABLE IF NOT EXISTS typifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    source UUID[],
    created_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp
);
CREATE TABLE IF NOT EXISTS sources (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    has_file BOOLEAN DEFAULT FALSE,
    created_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp
);
CREATE TABLE IF NOT EXISTS taxonomies (
    typification_id UUID REFERENCES typifications(id) ON DELETE CASCADE,
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(255) NOT NULL,
    description TEXT,
    source UUID[],
    created_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp
);
CREATE TABLE IF NOT EXISTS branches  (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    taxonomy_id UUID REFERENCES taxonomies(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    description TEXT,
    created_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp
);
CREATE TABLE IF NOT EXISTS docs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    typification UUID[],
    created_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp
);
CREATE TABLE IF NOT EXISTS releases(
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    doc_id UUID REFERENCES docs(id) ON DELETE CASCADE,
    taxonomy JSONB NOT NULL,
    created_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP
);