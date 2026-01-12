-- Migração 003: Adicionar classificação em tipos_lote e criar tabela tipo_lote_preco_estrelas
-- Data: 2025-11-10
-- Descrição: Adiciona campo de classificação (leve/media/pesada) em tipos_lote
--            e cria nova tabela para armazenar preços padrão por estrela (1-5)

BEGIN;

-- 1. Adicionar campo classificacao na tabela tipos_lote (se não existir)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'tipos_lote' AND column_name = 'classificacao'
    ) THEN
        ALTER TABLE tipos_lote ADD COLUMN classificacao VARCHAR(10) DEFAULT 'media' NOT NULL;
        
        -- Adicionar constraint para validar valores permitidos
        ALTER TABLE tipos_lote ADD CONSTRAINT chk_classificacao 
        CHECK (classificacao IN ('leve', 'media', 'pesada'));
        
        RAISE NOTICE 'Campo classificacao adicionado com sucesso em tipos_lote';
    ELSE
        RAISE NOTICE 'Campo classificacao já existe em tipos_lote';
    END IF;
END $$;

-- 2. Criar tabela tipo_lote_preco_estrelas (se não existir)
CREATE TABLE IF NOT EXISTS tipo_lote_preco_estrelas (
    id SERIAL PRIMARY KEY,
    tipo_lote_id INTEGER NOT NULL,
    estrelas INTEGER NOT NULL CHECK (estrelas >= 1 AND estrelas <= 5),
    preco_por_kg DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    ativo BOOLEAN NOT NULL DEFAULT TRUE,
    data_cadastro TIMESTAMP NOT NULL DEFAULT NOW(),
    data_atualizacao TIMESTAMP NOT NULL DEFAULT NOW(),
    
    -- Foreign keys
    CONSTRAINT fk_tipo_lote_preco_tipo_lote 
        FOREIGN KEY (tipo_lote_id) 
        REFERENCES tipos_lote(id) 
        ON DELETE CASCADE,
    
    -- Unique constraint: cada tipo_lote pode ter apenas um preço por estrela
    CONSTRAINT uq_tipo_lote_estrelas UNIQUE (tipo_lote_id, estrelas)
);

-- 3. Criar índice para melhorar performance de consultas
CREATE INDEX IF NOT EXISTS idx_tipo_lote_estrelas 
ON tipo_lote_preco_estrelas(tipo_lote_id, estrelas);

-- 4. Adicionar comentários nas tabelas para documentação
COMMENT ON TABLE tipo_lote_preco_estrelas IS 'Armazena preços padrão por estrela (1-5) para cada tipo de lote';
COMMENT ON COLUMN tipos_lote.classificacao IS 'Classificação do tipo de lote: leve, media ou pesada';
COMMENT ON COLUMN tipo_lote_preco_estrelas.estrelas IS 'Nível de qualidade de 1 a 5 estrelas';
COMMENT ON COLUMN tipo_lote_preco_estrelas.preco_por_kg IS 'Preço padrão por kg para este tipo de lote e estrela';

COMMIT;

-- Log de sucesso
DO $$
BEGIN
    RAISE NOTICE '✓ Migração 003 concluída com sucesso!';
    RAISE NOTICE '  - Campo classificacao adicionado em tipos_lote';
    RAISE NOTICE '  - Tabela tipo_lote_preco_estrelas criada';
    RAISE NOTICE '  - Índices e constraints configurados';
END $$;
