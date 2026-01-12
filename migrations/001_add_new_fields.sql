-- Migração para adicionar novos campos e tabelas ao sistema MRX

-- Criar tabela de vendedores
CREATE TABLE IF NOT EXISTS vendedores (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    email VARCHAR(120) UNIQUE,
    telefone VARCHAR(20),
    cpf VARCHAR(14) UNIQUE,
    data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    ativo BOOLEAN DEFAULT TRUE NOT NULL
);

-- Adicionar novos campos à tabela empresas
ALTER TABLE empresas ADD COLUMN IF NOT EXISTS nome_social VARCHAR(200);
ALTER TABLE empresas ADD COLUMN IF NOT EXISTS cpf VARCHAR(14);
ALTER TABLE empresas ADD COLUMN IF NOT EXISTS endereco_coleta VARCHAR(300);
ALTER TABLE empresas ADD COLUMN IF NOT EXISTS endereco_emissao VARCHAR(300);
ALTER TABLE empresas ADD COLUMN IF NOT EXISTS rua VARCHAR(200);
ALTER TABLE empresas ADD COLUMN IF NOT EXISTS numero VARCHAR(20);
ALTER TABLE empresas ADD COLUMN IF NOT EXISTS cidade VARCHAR(100);
ALTER TABLE empresas ADD COLUMN IF NOT EXISTS cep VARCHAR(10);
ALTER TABLE empresas ADD COLUMN IF NOT EXISTS estado VARCHAR(2);
ALTER TABLE empresas ADD COLUMN IF NOT EXISTS email VARCHAR(120);
ALTER TABLE empresas ADD COLUMN IF NOT EXISTS vendedor_id INTEGER REFERENCES vendedores(id);
ALTER TABLE empresas ADD COLUMN IF NOT EXISTS conta_bancaria VARCHAR(50);
ALTER TABLE empresas ADD COLUMN IF NOT EXISTS agencia VARCHAR(20);
ALTER TABLE empresas ADD COLUMN IF NOT EXISTS chave_pix VARCHAR(100);
ALTER TABLE empresas ADD COLUMN IF NOT EXISTS banco VARCHAR(100);
ALTER TABLE empresas ADD COLUMN IF NOT EXISTS condicao_pagamento VARCHAR(20) DEFAULT 'avista';
ALTER TABLE empresas ADD COLUMN IF NOT EXISTS forma_pagamento VARCHAR(20) DEFAULT 'pix';
ALTER TABLE empresas ADD COLUMN IF NOT EXISTS data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

-- Criar tabela de solicitações
CREATE TABLE IF NOT EXISTS solicitacoes (
    id SERIAL PRIMARY KEY,
    funcionario_id INTEGER NOT NULL REFERENCES usuarios(id),
    empresa_id INTEGER NOT NULL REFERENCES empresas(id),
    status VARCHAR(20) DEFAULT 'pendente' NOT NULL,
    observacoes TEXT,
    data_envio TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    data_confirmacao TIMESTAMP
);

-- Adicionar novos campos à tabela placas
ALTER TABLE placas ADD COLUMN IF NOT EXISTS tag VARCHAR(50) UNIQUE;
ALTER TABLE placas ADD COLUMN IF NOT EXISTS solicitacao_id INTEGER REFERENCES solicitacoes(id);
ALTER TABLE placas ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'em_analise';
ALTER TABLE placas ADD COLUMN IF NOT EXISTS data_compra TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE placas ADD COLUMN IF NOT EXISTS data_aprovacao TIMESTAMP;

-- Gerar tags únicas para placas existentes
UPDATE placas SET tag = UPPER(SUBSTRING(MD5(RANDOM()::TEXT) FROM 1 FOR 8)) WHERE tag IS NULL;

-- Criar tabela de entradas
CREATE TABLE IF NOT EXISTS entradas (
    id SERIAL PRIMARY KEY,
    solicitacao_id INTEGER NOT NULL REFERENCES solicitacoes(id),
    admin_id INTEGER REFERENCES usuarios(id),
    status VARCHAR(20) DEFAULT 'pendente' NOT NULL,
    data_entrada TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    data_processamento TIMESTAMP,
    observacoes TEXT
);

-- Criar índices para melhor performance
CREATE INDEX IF NOT EXISTS idx_empresas_vendedor ON empresas(vendedor_id);
CREATE INDEX IF NOT EXISTS idx_solicitacoes_funcionario ON solicitacoes(funcionario_id);
CREATE INDEX IF NOT EXISTS idx_solicitacoes_empresa ON solicitacoes(empresa_id);
CREATE INDEX IF NOT EXISTS idx_solicitacoes_status ON solicitacoes(status);
CREATE INDEX IF NOT EXISTS idx_placas_solicitacao ON placas(solicitacao_id);
CREATE INDEX IF NOT EXISTS idx_placas_tag ON placas(tag);
CREATE INDEX IF NOT EXISTS idx_placas_status ON placas(status);
CREATE INDEX IF NOT EXISTS idx_entradas_solicitacao ON entradas(solicitacao_id);
CREATE INDEX IF NOT EXISTS idx_entradas_status ON entradas(status);
