-- Migration 007: Adiciona tabelas para relação Fornecedor-TipoLote e configuração de estrelas
-- Data: 2025-11-10

-- Tabela de relação N:N entre Fornecedor e TipoLote
CREATE TABLE IF NOT EXISTS fornecedor_tipo_lote (
    id SERIAL PRIMARY KEY,
    fornecedor_id INTEGER NOT NULL REFERENCES fornecedores(id) ON DELETE CASCADE,
    tipo_lote_id INTEGER NOT NULL REFERENCES tipos_lote(id) ON DELETE CASCADE,
    ativo BOOLEAN NOT NULL DEFAULT TRUE,
    data_cadastro TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_fornecedor_tipo UNIQUE (fornecedor_id, tipo_lote_id)
);

CREATE INDEX IF NOT EXISTS idx_fornecedor_tipo_forn ON fornecedor_tipo_lote(fornecedor_id);
CREATE INDEX IF NOT EXISTS idx_fornecedor_tipo_lote ON fornecedor_tipo_lote(tipo_lote_id);

-- Tabela de configuração de estrelas por classificação para cada fornecedor
CREATE TABLE IF NOT EXISTS fornecedor_classificacao_estrela (
    id SERIAL PRIMARY KEY,
    fornecedor_id INTEGER NOT NULL REFERENCES fornecedores(id) ON DELETE CASCADE,
    classificacao VARCHAR(10) NOT NULL CHECK (classificacao IN ('leve', 'medio', 'pesado')),
    estrelas INTEGER NOT NULL CHECK (estrelas >= 1 AND estrelas <= 5),
    ativo BOOLEAN NOT NULL DEFAULT TRUE,
    data_cadastro TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    data_atualizacao TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_fornecedor_classificacao UNIQUE (fornecedor_id, classificacao)
);

CREATE INDEX IF NOT EXISTS idx_fornecedor_class_forn ON fornecedor_classificacao_estrela(fornecedor_id);

COMMENT ON TABLE fornecedor_tipo_lote IS 'Relação N:N - quais tipos de lote cada fornecedor vende';
COMMENT ON TABLE fornecedor_classificacao_estrela IS 'Configuração de estrelas por classificação para cada fornecedor (ex: leve=2★, médio=3★, pesado=4★)';
