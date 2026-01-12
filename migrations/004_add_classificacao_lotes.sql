-- Migração 004: Adicionar funcionalidades de classificação de lotes (leve, médio, pesado)
-- Data: 2025-11-10
-- Descrição: Adiciona tabela para vincular classificações de lotes por fornecedor

-- Criar tabela para configuração de classificações por fornecedor e tipo de lote
CREATE TABLE IF NOT EXISTS fornecedor_tipo_lote_classificacao (
    id SERIAL PRIMARY KEY,
    fornecedor_id INTEGER NOT NULL REFERENCES fornecedores(id) ON DELETE CASCADE,
    tipo_lote_id INTEGER NOT NULL REFERENCES tipos_lote(id) ON DELETE CASCADE,
    leve_estrelas INTEGER NOT NULL DEFAULT 1 CHECK (leve_estrelas >= 1 AND leve_estrelas <= 5),
    medio_estrelas INTEGER NOT NULL DEFAULT 3 CHECK (medio_estrelas >= 1 AND medio_estrelas <= 5),
    pesado_estrelas INTEGER NOT NULL DEFAULT 5 CHECK (pesado_estrelas >= 1 AND pesado_estrelas <= 5),
    ativo BOOLEAN NOT NULL DEFAULT TRUE,
    data_cadastro TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
    data_atualizacao TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
    CONSTRAINT uq_fornecedor_tipo_classificacao UNIQUE (fornecedor_id, tipo_lote_id)
);

-- Adicionar índices para performance
CREATE INDEX IF NOT EXISTS idx_fornecedor_tipo_class ON fornecedor_tipo_lote_classificacao(fornecedor_id, tipo_lote_id);
CREATE INDEX IF NOT EXISTS idx_fornecedor_class_ativo ON fornecedor_tipo_lote_classificacao(fornecedor_id, ativo);

-- Adicionar campo de classificação aos itens de solicitação (se não existir)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'itens_solicitacao' 
                   AND column_name = 'classificacao') THEN
        ALTER TABLE itens_solicitacao 
        ADD COLUMN classificacao VARCHAR(10) CHECK (classificacao IN ('leve', 'medio', 'pesado'));
    END IF;
END $$;

-- Adicionar campo de classificação aos lotes (se não existir)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'lotes' 
                   AND column_name = 'classificacao_predominante') THEN
        ALTER TABLE lotes 
        ADD COLUMN classificacao_predominante VARCHAR(10) CHECK (classificacao_predominante IN ('leve', 'medio', 'pesado'));
    END IF;
END $$;

-- Adicionar campo de sugestão de IA aos itens de solicitação (se não existir)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'itens_solicitacao' 
                   AND column_name = 'classificacao_sugerida_ia') THEN
        ALTER TABLE itens_solicitacao 
        ADD COLUMN classificacao_sugerida_ia VARCHAR(10) CHECK (classificacao_sugerida_ia IN ('leve', 'medio', 'pesado'));
    END IF;
END $$;

-- Adicionar configuração global de valor base por estrela
INSERT INTO configuracoes (chave, valor, descricao, tipo)
VALUES ('valor_base_por_estrela', '1.00', 'Valor base em reais por estrela para cálculo de preços', 'decimal')
ON CONFLICT (chave) DO NOTHING;

-- Comentários nas tabelas
COMMENT ON TABLE fornecedor_tipo_lote_classificacao IS 'Configuração de estrelas por classificação (leve, médio, pesado) para cada fornecedor e tipo de lote';
COMMENT ON COLUMN fornecedor_tipo_lote_classificacao.leve_estrelas IS 'Número de estrelas (1-5) para classificação leve';
COMMENT ON COLUMN fornecedor_tipo_lote_classificacao.medio_estrelas IS 'Número de estrelas (1-5) para classificação média';
COMMENT ON COLUMN fornecedor_tipo_lote_classificacao.pesado_estrelas IS 'Número de estrelas (1-5) para classificação pesada';
