-- Migration 005: Add Classification-Based Pricing System
-- This migration adds the new TipoLotePrecoClassificacao table and snapshot fields

-- Create the new tipo_lote_preco_classificacoes table
CREATE TABLE IF NOT EXISTS tipo_lote_preco_classificacoes (
    id SERIAL PRIMARY KEY,
    tipo_lote_id INTEGER NOT NULL REFERENCES tipos_lote(id) ON DELETE CASCADE,
    classificacao VARCHAR(10) NOT NULL CHECK (classificacao IN ('leve', 'medio', 'pesado')),
    preco_por_kg FLOAT NOT NULL DEFAULT 0.0 CHECK (preco_por_kg >= 0),
    ativo BOOLEAN NOT NULL DEFAULT TRUE,
    data_cadastro TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    data_atualizacao TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_tipo_lote_classificacao UNIQUE (tipo_lote_id, classificacao)
);

-- Create indexes for the new table
CREATE INDEX IF NOT EXISTS idx_tipo_lote_classificacao ON tipo_lote_preco_classificacoes(tipo_lote_id, classificacao);

-- Add snapshot fields to itens_solicitacao table
ALTER TABLE itens_solicitacao ADD COLUMN IF NOT EXISTS preco_por_kg_snapshot FLOAT;
ALTER TABLE itens_solicitacao ADD COLUMN IF NOT EXISTS estrelas_snapshot INTEGER;

-- Migrate existing data from tipo_lote_preco_estrelas to tipo_lote_preco_classificacoes
-- We'll create default prices for each classification based on existing star-based prices
-- This is a data migration that maps star levels to classifications:
-- Stars 1-2 -> leve, Stars 3 -> medio, Stars 4-5 -> pesado
INSERT INTO tipo_lote_preco_classificacoes (tipo_lote_id, classificacao, preco_por_kg, ativo)
SELECT DISTINCT
    tipo_lote_id,
    'leve' as classificacao,
    COALESCE(
        (SELECT AVG(preco_por_kg) FROM tipo_lote_preco_estrelas 
         WHERE tipo_lote_id = tl.tipo_lote_id AND estrelas IN (1, 2) AND ativo = TRUE),
        0.0
    ) as preco_por_kg,
    TRUE as ativo
FROM tipo_lote_preco_estrelas tl
WHERE NOT EXISTS (
    SELECT 1 FROM tipo_lote_preco_classificacoes 
    WHERE tipo_lote_id = tl.tipo_lote_id AND classificacao = 'leve'
)
UNION
SELECT DISTINCT
    tipo_lote_id,
    'medio' as classificacao,
    COALESCE(
        (SELECT preco_por_kg FROM tipo_lote_preco_estrelas 
         WHERE tipo_lote_id = tl.tipo_lote_id AND estrelas = 3 AND ativo = TRUE LIMIT 1),
        0.0
    ) as preco_por_kg,
    TRUE as ativo
FROM tipo_lote_preco_estrelas tl
WHERE NOT EXISTS (
    SELECT 1 FROM tipo_lote_preco_classificacoes 
    WHERE tipo_lote_id = tl.tipo_lote_id AND classificacao = 'medio'
)
UNION
SELECT DISTINCT
    tipo_lote_id,
    'pesado' as classificacao,
    COALESCE(
        (SELECT AVG(preco_por_kg) FROM tipo_lote_preco_estrelas 
         WHERE tipo_lote_id = tl.tipo_lote_id AND estrelas IN (4, 5) AND ativo = TRUE),
        0.0
    ) as preco_por_kg,
    TRUE as ativo
FROM tipo_lote_preco_estrelas tl
WHERE NOT EXISTS (
    SELECT 1 FROM tipo_lote_preco_classificacoes 
    WHERE tipo_lote_id = tl.tipo_lote_id AND classificacao = 'pesado'
);

-- Update existing itens_solicitacao records to populate snapshot fields
-- based on their existing values
UPDATE itens_solicitacao
SET 
    estrelas_snapshot = estrelas_final,
    preco_por_kg_snapshot = CASE 
        WHEN valor_calculado > 0 AND peso_kg > 0 THEN valor_calculado / peso_kg
        ELSE 0
    END
WHERE estrelas_snapshot IS NULL OR preco_por_kg_snapshot IS NULL;
