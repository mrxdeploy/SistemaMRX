-- Migração 002: Adicionar estruturas restantes do sistema
-- Tabelas: funcionarios, fornecedores, compras, classificacoes, configuracoes
-- Data: 2025-01-07

-- Tabela de Funcionários
CREATE TABLE IF NOT EXISTS funcionarios (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    cpf VARCHAR(14) UNIQUE NOT NULL,
    telefone VARCHAR(20),
    cargo VARCHAR(100),
    empresa_id INTEGER REFERENCES empresas(id) ON DELETE SET NULL,
    vendedor_id INTEGER REFERENCES vendedores(id) ON DELETE SET NULL,
    data_cadastro TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ativo BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE INDEX IF NOT EXISTS idx_funcionarios_empresa ON funcionarios(empresa_id);
CREATE INDEX IF NOT EXISTS idx_funcionarios_vendedor ON funcionarios(vendedor_id);
CREATE INDEX IF NOT EXISTS idx_funcionarios_cpf ON funcionarios(cpf);
CREATE INDEX IF NOT EXISTS idx_funcionarios_ativo ON funcionarios(ativo);

-- Tabela de Fornecedores
CREATE TABLE IF NOT EXISTS fornecedores (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(200) NOT NULL,
    nome_social VARCHAR(200),
    cnpj VARCHAR(18) UNIQUE,
    cpf VARCHAR(14) UNIQUE,
    endereco_coleta VARCHAR(300),
    endereco_emissao VARCHAR(300),
    telefone VARCHAR(20),
    email VARCHAR(120),
    conta_bancaria VARCHAR(50),
    agencia VARCHAR(20),
    chave_pix VARCHAR(100),
    banco VARCHAR(100),
    condicao_pagamento VARCHAR(50),
    forma_pagamento VARCHAR(50),
    observacoes TEXT,
    data_cadastro TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ativo BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE INDEX IF NOT EXISTS idx_fornecedores_cnpj ON fornecedores(cnpj);
CREATE INDEX IF NOT EXISTS idx_fornecedores_cpf ON fornecedores(cpf);
CREATE INDEX IF NOT EXISTS idx_fornecedores_ativo ON fornecedores(ativo);
CREATE INDEX IF NOT EXISTS idx_fornecedores_nome ON fornecedores(nome);

-- Tabela de Compras/Despesas
CREATE TABLE IF NOT EXISTS compras (
    id SERIAL PRIMARY KEY,
    fornecedor_id INTEGER NOT NULL REFERENCES fornecedores(id) ON DELETE CASCADE,
    solicitacao_id INTEGER REFERENCES solicitacoes(id) ON DELETE SET NULL,
    material VARCHAR(200) NOT NULL,
    tipo VARCHAR(20) NOT NULL DEFAULT 'compra',
    valor FLOAT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pendente',
    comprovante_url VARCHAR(500),
    observacoes TEXT,
    data_compra TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    data_pagamento TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_compras_fornecedor ON compras(fornecedor_id);
CREATE INDEX IF NOT EXISTS idx_compras_solicitacao ON compras(solicitacao_id);
CREATE INDEX IF NOT EXISTS idx_compras_tipo ON compras(tipo);
CREATE INDEX IF NOT EXISTS idx_compras_status ON compras(status);
CREATE INDEX IF NOT EXISTS idx_compras_data ON compras(data_compra);

-- Tabela de Classificações de Lote
CREATE TABLE IF NOT EXISTS classificacoes (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(100) UNIQUE NOT NULL,
    tipo_lote VARCHAR(20) NOT NULL,
    peso_minimo FLOAT DEFAULT 0.0,
    peso_maximo FLOAT DEFAULT 999999.0,
    observacoes TEXT,
    data_cadastro TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_classificacoes_tipo_lote ON classificacoes(tipo_lote);
CREATE INDEX IF NOT EXISTS idx_classificacoes_nome ON classificacoes(nome);

-- Tabela de Configurações do Sistema
CREATE TABLE IF NOT EXISTS configuracoes (
    id SERIAL PRIMARY KEY,
    chave VARCHAR(100) UNIQUE NOT NULL,
    valor TEXT NOT NULL,
    descricao VARCHAR(200),
    tipo VARCHAR(50) DEFAULT 'texto',
    data_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_configuracoes_chave ON configuracoes(chave);
CREATE INDEX IF NOT EXISTS idx_configuracoes_tipo ON configuracoes(tipo);

-- Inserir configurações padrão
INSERT INTO configuracoes (chave, valor, descricao, tipo) VALUES
    ('sistema_nome', 'MRX Systems', 'Nome do sistema', 'texto'),
    ('peso_leve_max', '50', 'Peso máximo para classificação leve (kg)', 'numero'),
    ('peso_media_max', '100', 'Peso máximo para classificação média (kg)', 'numero'),
    ('email_notificacao', 'admin@sistema.com', 'Email para notificações do sistema', 'email')
ON CONFLICT (chave) DO NOTHING;

-- Inserir classificações padrão
INSERT INTO classificacoes (nome, tipo_lote, peso_minimo, peso_maximo, observacoes) VALUES
    ('Lote Leve Pequeno', 'leve', 0, 25, 'Lotes de placas leves até 25kg'),
    ('Lote Leve Grande', 'leve', 25, 50, 'Lotes de placas leves de 25kg a 50kg'),
    ('Lote Médio Pequeno', 'media', 50, 75, 'Lotes de placas médias de 50kg a 75kg'),
    ('Lote Médio Grande', 'media', 75, 100, 'Lotes de placas médias de 75kg a 100kg'),
    ('Lote Pesado Pequeno', 'pesada', 100, 150, 'Lotes de placas pesadas de 100kg a 150kg'),
    ('Lote Pesado Grande', 'pesada', 150, 999999, 'Lotes de placas pesadas acima de 150kg')
ON CONFLICT (nome) DO NOTHING;

-- Comentários para documentação
COMMENT ON TABLE funcionarios IS 'Cadastro de funcionários vinculados a empresas e vendedores';
COMMENT ON TABLE fornecedores IS 'Cadastro completo de fornecedores com dados bancários e endereços';
COMMENT ON TABLE compras IS 'Registro de compras e despesas vinculadas a fornecedores';
COMMENT ON TABLE classificacoes IS 'Classificação automática de lotes por peso e tipo';
COMMENT ON TABLE configuracoes IS 'Parâmetros e configurações gerais do sistema';

-- Mensagem final
SELECT 'Migração 002 executada com sucesso!' AS status;
