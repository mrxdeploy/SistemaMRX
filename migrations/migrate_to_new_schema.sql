-- SCRIPT DE MIGRAÇÃO PARA NOVA ESTRUTURA DO SISTEMA MRX
-- Este script remove completamente a estrutura antiga e cria a nova
-- ATENÇÃO: Este script apaga TODOS OS DADOS! Use apenas em desenvolvimento ou com backup

-- ====================
-- PASSO 1: REMOVER ESTRUTURA ANTIGA
-- ====================

DROP TABLE IF EXISTS classificacoes CASCADE;
DROP TABLE IF EXISTS compras CASCADE;
DROP TABLE IF EXISTS lotes CASCADE;
DROP TABLE IF EXISTS placas CASCADE;
DROP TABLE IF EXISTS entradas CASCADE;
DROP TABLE IF EXISTS precos CASCADE;
DROP TABLE IF EXISTS configuracao_preco_estrelas CASCADE;
DROP TABLE IF EXISTS fornecedor_produto_precos CASCADE;
DROP TABLE IF EXISTS produtos CASCADE;
DROP TABLE IF EXISTS solicitacoes CASCADE;
DROP TABLE IF EXISTS notificacoes CASCADE;
DROP TABLE IF EXISTS configuracoes CASCADE;
DROP TABLE IF EXISTS fornecedores CASCADE;
DROP TABLE IF EXISTS vendedores CASCADE;
DROP TABLE IF EXISTS usuarios CASCADE;

-- ====================
-- PASSO 2: CRIAR NOVA ESTRUTURA
-- ====================

-- Tabela de Usuários
CREATE TABLE usuarios (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    email VARCHAR(120) UNIQUE NOT NULL,
    senha_hash VARCHAR(255) NOT NULL,
    tipo VARCHAR(20) NOT NULL,
    data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    ativo BOOLEAN DEFAULT TRUE NOT NULL
);

-- Tabela de Vendedores
CREATE TABLE vendedores (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    email VARCHAR(120) UNIQUE,
    telefone VARCHAR(20),
    cpf VARCHAR(14) UNIQUE,
    data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    ativo BOOLEAN DEFAULT TRUE NOT NULL
);

-- Tabela de Tipos de Lote (antiga "Produtos")
CREATE TABLE tipos_lote (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(100) UNIQUE NOT NULL,
    descricao VARCHAR(300),
    codigo VARCHAR(20) UNIQUE,
    ativo BOOLEAN DEFAULT TRUE NOT NULL,
    data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    data_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabela de Fornecedores
CREATE TABLE fornecedores (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(200) NOT NULL,
    nome_social VARCHAR(200),
    cnpj VARCHAR(18) UNIQUE,
    cpf VARCHAR(14) UNIQUE,
    rua VARCHAR(200),
    numero VARCHAR(20),
    cidade VARCHAR(100),
    cep VARCHAR(10),
    estado VARCHAR(2),
    bairro VARCHAR(100),
    complemento VARCHAR(200),
    tem_outro_endereco BOOLEAN DEFAULT FALSE,
    outro_rua VARCHAR(200),
    outro_numero VARCHAR(20),
    outro_cidade VARCHAR(100),
    outro_cep VARCHAR(10),
    outro_estado VARCHAR(2),
    outro_bairro VARCHAR(100),
    outro_complemento VARCHAR(200),
    telefone VARCHAR(20),
    email VARCHAR(120),
    vendedor_id INTEGER REFERENCES vendedores(id) ON DELETE SET NULL,
    conta_bancaria VARCHAR(50),
    agencia VARCHAR(20),
    chave_pix VARCHAR(100),
    banco VARCHAR(100),
    condicao_pagamento VARCHAR(50) DEFAULT 'avista',
    forma_pagamento VARCHAR(50) DEFAULT 'pix',
    observacoes TEXT,
    data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    ativo BOOLEAN DEFAULT TRUE NOT NULL
);

-- Tabela de Preços por Fornecedor/Tipo de Lote/Estrelas
CREATE TABLE fornecedor_tipo_lote_precos (
    id SERIAL PRIMARY KEY,
    fornecedor_id INTEGER NOT NULL REFERENCES fornecedores(id) ON DELETE CASCADE,
    tipo_lote_id INTEGER NOT NULL REFERENCES tipos_lote(id) ON DELETE CASCADE,
    estrelas INTEGER NOT NULL CHECK (estrelas >= 1 AND estrelas <= 5),
    preco_por_kg FLOAT NOT NULL DEFAULT 0.0,
    ativo BOOLEAN DEFAULT TRUE NOT NULL,
    data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    data_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_fornecedor_tipo_estrelas UNIQUE (fornecedor_id, tipo_lote_id, estrelas)
);

-- Índice para melhor performance
CREATE INDEX idx_fornecedor_tipo_estrelas ON fornecedor_tipo_lote_precos(fornecedor_id, tipo_lote_id, estrelas);

-- Tabela de Solicitações
CREATE TABLE solicitacoes (
    id SERIAL PRIMARY KEY,
    funcionario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    fornecedor_id INTEGER NOT NULL REFERENCES fornecedores(id) ON DELETE CASCADE,
    tipo_retirada VARCHAR(20) DEFAULT 'buscar' NOT NULL,
    status VARCHAR(20) DEFAULT 'pendente' NOT NULL,
    observacoes TEXT,
    data_envio TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    data_confirmacao TIMESTAMP,
    admin_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL
);

-- Tabela de Itens de Solicitação
CREATE TABLE itens_solicitacao (
    id SERIAL PRIMARY KEY,
    solicitacao_id INTEGER NOT NULL REFERENCES solicitacoes(id) ON DELETE CASCADE,
    tipo_lote_id INTEGER NOT NULL REFERENCES tipos_lote(id) ON DELETE RESTRICT,
    peso_kg FLOAT NOT NULL,
    estrelas_sugeridas_ia INTEGER CHECK (estrelas_sugeridas_ia IS NULL OR (estrelas_sugeridas_ia >= 1 AND estrelas_sugeridas_ia <= 5)),
    estrelas_final INTEGER NOT NULL DEFAULT 3 CHECK (estrelas_final >= 1 AND estrelas_final <= 5),
    valor_calculado FLOAT NOT NULL DEFAULT 0.0,
    imagem_url VARCHAR(500),
    observacoes TEXT,
    data_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    lote_id INTEGER REFERENCES lotes(id) ON DELETE SET NULL
);

-- Tabela de Lotes
CREATE TABLE lotes (
    id SERIAL PRIMARY KEY,
    numero_lote VARCHAR(50) UNIQUE NOT NULL,
    fornecedor_id INTEGER NOT NULL REFERENCES fornecedores(id) ON DELETE RESTRICT,
    tipo_lote_id INTEGER NOT NULL REFERENCES tipos_lote(id) ON DELETE RESTRICT,
    solicitacao_origem_id INTEGER REFERENCES solicitacoes(id) ON DELETE SET NULL,
    peso_total_kg FLOAT NOT NULL DEFAULT 0.0,
    valor_total FLOAT NOT NULL DEFAULT 0.0,
    quantidade_itens INTEGER DEFAULT 0,
    estrelas_media FLOAT,
    status VARCHAR(20) DEFAULT 'aberto' NOT NULL,
    tipo_retirada VARCHAR(20),
    data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    data_fechamento TIMESTAMP,
    data_aprovacao TIMESTAMP,
    observacoes TEXT
);

-- Índices para performance
CREATE INDEX idx_numero_lote ON lotes(numero_lote);
CREATE INDEX idx_fornecedor_tipo_status ON lotes(fornecedor_id, tipo_lote_id, status);

-- Agora podemos adicionar a foreign key de itens_solicitacao para lotes
-- (foi declarada acima mas só pode ser criada após a tabela lotes existir)

-- Tabela de Entradas de Estoque
CREATE TABLE entradas_estoque (
    id SERIAL PRIMARY KEY,
    lote_id INTEGER NOT NULL REFERENCES lotes(id) ON DELETE RESTRICT,
    admin_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    status VARCHAR(20) DEFAULT 'pendente' NOT NULL,
    data_entrada TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    data_processamento TIMESTAMP,
    observacoes TEXT
);

-- Tabela de Notificações
CREATE TABLE notificacoes (
    id SERIAL PRIMARY KEY,
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    titulo VARCHAR(200) NOT NULL,
    mensagem TEXT NOT NULL,
    lida BOOLEAN DEFAULT FALSE NOT NULL,
    data_envio TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- Tabela de Configurações
CREATE TABLE configuracoes (
    id SERIAL PRIMARY KEY,
    chave VARCHAR(100) UNIQUE NOT NULL,
    valor TEXT NOT NULL,
    descricao VARCHAR(200),
    tipo VARCHAR(50) DEFAULT 'texto',
    data_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ====================
-- PASSO 3: INSERIR DADOS INICIAIS
-- ====================

-- Criar usuário admin padrão (senha: admin123)
INSERT INTO usuarios (nome, email, senha_hash, tipo) VALUES 
('Administrador', 'admin@sistema.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5dtD7cLlWaVSm', 'admin');

-- Inserir tipos de lote comuns (pode expandir até 150)
INSERT INTO tipos_lote (nome, descricao, codigo) VALUES 
('Placa Leve Tipo A', 'Placas eletrônicas leves categoria A', 'PL-A'),
('Placa Pesada Tipo A', 'Placas eletrônicas pesadas categoria A', 'PP-A'),
('Placa Média Tipo A', 'Placas eletrônicas médias categoria A', 'PM-A'),
('Placa Leve Tipo B', 'Placas eletrônicas leves categoria B', 'PL-B'),
('Placa Pesada Tipo B', 'Placas eletrônicas pesadas categoria B', 'PP-B'),
('Placa Média Tipo B', 'Placas eletrônicas médias categoria B', 'PM-B'),
('Processadores', 'Processadores de computador', 'PROC'),
('Memórias RAM', 'Módulos de memória RAM', 'RAM'),
('Placas de Vídeo', 'Placas de vídeo/GPU', 'GPU'),
('Placas-Mãe', 'Placas-mãe de computadores', 'MB'),
('Fonte de Alimentação', 'Fontes de alimentação ATX', 'PSU'),
('Discos Rígidos', 'HD e SSD', 'HDD'),
('Cabos e Conectores', 'Cabos e conectores diversos', 'CABO'),
('Baterias', 'Baterias de notebook e celular', 'BAT'),
('Teclados', 'Teclados de computador', 'KBD'),
('Mouses', 'Mouses de computador', 'MSE'),
('Monitores', 'Monitores e displays', 'MON'),
('Notebooks', 'Notebooks completos', 'NB'),
('Celulares', 'Telefones celulares', 'CEL'),
('Tablets', 'Tablets e iPads', 'TAB');

COMMENT ON TABLE usuarios IS 'Tabela de usuários do sistema (funcionários e administradores)';
COMMENT ON TABLE vendedores IS 'Tabela de vendedores que gerenciam fornecedores';
COMMENT ON TABLE tipos_lote IS 'Tipos de lotes/produtos que podem ser comprados (até 150 tipos)';
COMMENT ON TABLE fornecedores IS 'Fornecedores de materiais eletrônicos';
COMMENT ON TABLE fornecedor_tipo_lote_precos IS 'Preços configurados por fornecedor, tipo de lote e classificação por estrelas (1-5)';
COMMENT ON TABLE solicitacoes IS 'Solicitações de compra criadas por funcionários';
COMMENT ON TABLE itens_solicitacao IS 'Itens individuais de cada solicitação (foto + peso + classificação IA)';
COMMENT ON TABLE lotes IS 'Lotes criados após aprovação de solicitações, agrupados por fornecedor e tipo';
COMMENT ON TABLE entradas_estoque IS 'Controle de entrada de lotes aprovados no estoque';
COMMENT ON TABLE notificacoes IS 'Notificações do sistema para usuários';
COMMENT ON TABLE configuracoes IS 'Configurações gerais do sistema';

-- Mensagem de sucesso
DO $$
BEGIN
    RAISE NOTICE '============================================';
    RAISE NOTICE 'MIGRAÇÃO CONCLUÍDA COM SUCESSO!';
    RAISE NOTICE '============================================';
    RAISE NOTICE 'Estrutura antiga removida';
    RAISE NOTICE 'Nova estrutura criada';
    RAISE NOTICE 'Dados iniciais inseridos:';
    RAISE NOTICE '  - 1 usuário admin (email: admin@sistema.com, senha: admin123)';
    RAISE NOTICE '  - 20 tipos de lote padrão';
    RAISE NOTICE '';
    RAISE NOTICE 'PRÓXIMOS PASSOS:';
    RAISE NOTICE '  1. Cadastrar fornecedores';
    RAISE NOTICE '  2. Configurar preços por fornecedor/tipo/estrelas';
    RAISE NOTICE '  3. Criar solicitações com itens';
    RAISE NOTICE '============================================';
END $$;
