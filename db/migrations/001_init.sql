CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS catalog_metadata (
  catalog_version TEXT PRIMARY KEY,
  provenance JSONB NOT NULL CHECK (jsonb_typeof(provenance) = 'object'),
  seeded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT catalog_metadata_version_semver CHECK (
    catalog_version ~ '^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(-[0-9A-Za-z.-]+)?(\+[0-9A-Za-z.-]+)?$'
  )
);

CREATE TABLE IF NOT EXISTS categories (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL CHECK (length(btrim(name)) > 0),
  description TEXT NOT NULL,
  attribute_definitions JSONB NOT NULL CHECK (
    jsonb_typeof(attribute_definitions) = 'array'
  ),
  CONSTRAINT categories_id_slug CHECK (id ~ '^[a-z0-9]+(-[a-z0-9]+)*$')
);

CREATE TABLE IF NOT EXISTS products (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL CHECK (length(btrim(name)) > 0),
  category_id TEXT NOT NULL REFERENCES categories(id),
  description TEXT NOT NULL CHECK (length(btrim(description)) > 0),
  price_minor INTEGER CHECK (price_minor >= 0),
  price_currency TEXT,
  attributes JSONB NOT NULL CHECK (jsonb_typeof(attributes) = 'object'),
  CONSTRAINT products_id_slug CHECK (id ~ '^[a-z0-9]+(-[a-z0-9]+)*$'),
  CONSTRAINT products_price_presence CHECK (
    (price_minor IS NULL AND price_currency IS NULL)
    OR (
      price_minor IS NOT NULL
      AND price_currency IS NOT NULL
      AND price_currency ~ '^[A-Z]{3}$'
    )
  )
);

CREATE INDEX IF NOT EXISTS products_category_id_idx ON products(category_id);

-- The initial embedding contract uses 1536 dimensions. A future model with a
-- different dimension requires an explicit migration and complete reindex.
CREATE TABLE IF NOT EXISTS product_embeddings (
  product_id TEXT PRIMARY KEY REFERENCES products(id) ON DELETE CASCADE,
  embedding vector(1536) NOT NULL,
  catalog_version TEXT NOT NULL REFERENCES catalog_metadata(catalog_version) ON DELETE CASCADE,
  provider TEXT NOT NULL CHECK (length(btrim(provider)) > 0),
  model_id TEXT NOT NULL CHECK (length(btrim(model_id)) > 0),
  content_digest TEXT NOT NULL CHECK (content_digest ~ '^[0-9a-f]{64}$'),
  dimensions INTEGER NOT NULL CHECK (dimensions > 0),
  indexed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT product_embeddings_dimensions_match CHECK (
    dimensions = vector_dims(embedding)
  )
);
