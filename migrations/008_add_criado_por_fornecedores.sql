-- Migration 008: Adiciona criado_por e tabela de atribuição de fornecedores

-- Adicionar coluna criado_por_id em fornecedores
ALTER TABLE fornecedores ADD COLUMN IF NOT EXISTS criado_por_id INTEGER;
ALTER TABLE fornecedores ADD CONSTRAINT fk_fornecedor_criado_por FOREIGN KEY (criado_por_id) REFERENCES usuarios(id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS idx_fornecedor_criado_por ON fornecedores(criado_por_id);

-- Criar tabela de atribuição de fornecedores a funcionários
CREATE TABLE IF NOT EXISTS fornecedor_funcionario_atribuicao (
    id SERIAL PRIMARY KEY,
    fornecedor_id INTEGER NOT NULL REFERENCES fornecedores(id) ON DELETE CASCADE,
    funcionario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    data_atribuicao TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    atribuido_por_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    CONSTRAINT uq_fornecedor_funcionario UNIQUE (fornecedor_id, funcionario_id)
);

CREATE INDEX IF NOT EXISTS idx_fornec_func_fornecedor ON fornecedor_funcionario_atribuicao(fornecedor_id);
CREATE INDEX IF NOT EXISTS idx_fornec_func_funcionario ON fornecedor_funcionario_atribuicao(funcionario_id);
