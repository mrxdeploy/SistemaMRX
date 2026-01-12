-- Script de Reset e Recriação Completa do Banco de Dados
-- Sistema MRX - Gestão de Compras de Placas Eletrônicas
-- Data: 2025-11-10
-- USO: Execute este script no Railway para recriar todas as tabelas com as novas funcionalidades

-- AVISO: Este script APAGA todos os dados existentes e recria o banco do zero
-- Use com cuidado! Faça backup antes de executar!

-- Drop all tables (ordem reversa para respeitar foreign keys)
DROP TABLE IF EXISTS notificacoes CASCADE;
DROP TABLE IF EXISTS entradas_estoque CASCADE;
DROP TABLE IF EXISTS itens_solicitacao CASCADE;
DROP TABLE IF EXISTS lotes CASCADE;
DROP TABLE IF EXISTS solicitacoes CASCADE;
DROP TABLE IF EXISTS fornecedor_tipo_lote_classificacao CASCADE;
DROP TABLE IF EXISTS fornecedor_tipo_lote_precos CASCADE;
DROP TABLE IF EXISTS tipo_lote_preco_estrelas CASCADE;
DROP TABLE IF EXISTS fornecedores CASCADE;
DROP TABLE IF EXISTS vendedores CASCADE;
DROP TABLE IF EXISTS tipos_lote CASCADE;
DROP TABLE IF EXISTS configuracoes CASCADE;
DROP TABLE IF EXISTS usuarios CASCADE;

-- Criar tabela de usuários
CREATE TABLE usuarios (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    email VARCHAR(120) UNIQUE NOT NULL,
    senha_hash VARCHAR(255) NOT NULL,
    tipo VARCHAR(20) NOT NULL,
    data_cadastro TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW() NOT NULL,
    ativo BOOLEAN DEFAULT TRUE NOT NULL
);

-- Criar tabela de vendedores
CREATE TABLE vendedores (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    email VARCHAR(120) UNIQUE,
    telefone VARCHAR(20),
    cpf VARCHAR(14) UNIQUE,
    data_cadastro TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW() NOT NULL,
    ativo BOOLEAN DEFAULT TRUE NOT NULL
);

-- Criar tabela de tipos de lote
CREATE TABLE tipos_lote (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(100) UNIQUE NOT NULL,
    descricao VARCHAR(300),
    codigo VARCHAR(20) UNIQUE,
    classificacao VARCHAR(10) DEFAULT 'media' NOT NULL CHECK (classificacao IN ('leve', 'media', 'pesada')),
    ativo BOOLEAN DEFAULT TRUE NOT NULL,
    data_cadastro TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW() NOT NULL,
    data_atualizacao TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
);

-- Criar tabela de preços de tipo de lote por estrelas
CREATE TABLE tipo_lote_preco_estrelas (
    id SERIAL PRIMARY KEY,
    tipo_lote_id INTEGER NOT NULL REFERENCES tipos_lote(id) ON DELETE CASCADE,
    estrelas INTEGER NOT NULL CHECK (estrelas >= 1 AND estrelas <= 5),
    preco_por_kg FLOAT DEFAULT 0.0 NOT NULL,
    ativo BOOLEAN DEFAULT TRUE NOT NULL,
    data_cadastro TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW() NOT NULL,
    data_atualizacao TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
    CONSTRAINT uq_tipo_lote_estrelas UNIQUE (tipo_lote_id, estrelas)
);

CREATE INDEX idx_tipo_lote_estrelas ON tipo_lote_preco_estrelas(tipo_lote_id, estrelas);

-- Criar tabela de fornecedores
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
    vendedor_id INTEGER REFERENCES vendedores(id),
    conta_bancaria VARCHAR(50),
    agencia VARCHAR(20),
    chave_pix VARCHAR(100),
    banco VARCHAR(100),
    condicao_pagamento VARCHAR(50) DEFAULT 'avista',
    forma_pagamento VARCHAR(50) DEFAULT 'pix',
    observacoes TEXT,
    data_cadastro TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW() NOT NULL,
    ativo BOOLEAN DEFAULT TRUE NOT NULL
);

-- Criar tabela de preços por fornecedor, tipo de lote e estrelas
CREATE TABLE fornecedor_tipo_lote_precos (
    id SERIAL PRIMARY KEY,
    fornecedor_id INTEGER NOT NULL REFERENCES fornecedores(id) ON DELETE CASCADE,
    tipo_lote_id INTEGER NOT NULL REFERENCES tipos_lote(id) ON DELETE CASCADE,
    estrelas INTEGER NOT NULL CHECK (estrelas >= 1 AND estrelas <= 5),
    preco_por_kg FLOAT DEFAULT 0.0 NOT NULL,
    ativo BOOLEAN DEFAULT TRUE NOT NULL,
    data_cadastro TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW() NOT NULL,
    data_atualizacao TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
    CONSTRAINT uq_fornecedor_tipo_estrelas UNIQUE (fornecedor_id, tipo_lote_id, estrelas)
);

CREATE INDEX idx_fornecedor_tipo_estrelas ON fornecedor_tipo_lote_precos(fornecedor_id, tipo_lote_id, estrelas);

-- Criar tabela de classificação de lotes por fornecedor (NOVA FUNCIONALIDADE)
CREATE TABLE fornecedor_tipo_lote_classificacao (
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

CREATE INDEX idx_fornecedor_tipo_class ON fornecedor_tipo_lote_classificacao(fornecedor_id, tipo_lote_id);
CREATE INDEX idx_fornecedor_class_ativo ON fornecedor_tipo_lote_classificacao(fornecedor_id, ativo);

-- Criar tabela de solicitações
CREATE TABLE solicitacoes (
    id SERIAL PRIMARY KEY,
    funcionario_id INTEGER NOT NULL REFERENCES usuarios(id),
    fornecedor_id INTEGER NOT NULL REFERENCES fornecedores(id) ON DELETE CASCADE,
    tipo_retirada VARCHAR(20) DEFAULT 'buscar' NOT NULL,
    status VARCHAR(20) DEFAULT 'pendente' NOT NULL,
    observacoes TEXT,
    data_envio TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW() NOT NULL,
    data_confirmacao TIMESTAMP WITHOUT TIME ZONE,
    admin_id INTEGER REFERENCES usuarios(id),
    rua VARCHAR(200),
    numero VARCHAR(20),
    cep VARCHAR(10),
    localizacao_lat FLOAT,
    localizacao_lng FLOAT,
    endereco_completo VARCHAR(500)
);

-- Criar tabela de lotes
CREATE TABLE lotes (
    id SERIAL PRIMARY KEY,
    numero_lote VARCHAR(50) UNIQUE NOT NULL,
    fornecedor_id INTEGER NOT NULL REFERENCES fornecedores(id),
    tipo_lote_id INTEGER NOT NULL REFERENCES tipos_lote(id),
    solicitacao_origem_id INTEGER REFERENCES solicitacoes(id),
    peso_total_kg FLOAT DEFAULT 0.0 NOT NULL,
    valor_total FLOAT DEFAULT 0.0 NOT NULL,
    quantidade_itens INTEGER DEFAULT 0,
    estrelas_media FLOAT,
    classificacao_predominante VARCHAR(10) CHECK (classificacao_predominante IN ('leve', 'medio', 'pesado')),
    status VARCHAR(20) DEFAULT 'aberto' NOT NULL,
    tipo_retirada VARCHAR(20),
    data_criacao TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW() NOT NULL,
    data_fechamento TIMESTAMP WITHOUT TIME ZONE,
    data_aprovacao TIMESTAMP WITHOUT TIME ZONE,
    observacoes TEXT
);

CREATE INDEX idx_numero_lote ON lotes(numero_lote);
CREATE INDEX idx_fornecedor_tipo_status ON lotes(fornecedor_id, tipo_lote_id, status);

-- Criar tabela de itens de solicitação
CREATE TABLE itens_solicitacao (
    id SERIAL PRIMARY KEY,
    solicitacao_id INTEGER NOT NULL REFERENCES solicitacoes(id) ON DELETE CASCADE,
    tipo_lote_id INTEGER NOT NULL REFERENCES tipos_lote(id),
    peso_kg FLOAT NOT NULL,
    estrelas_sugeridas_ia INTEGER,
    estrelas_final INTEGER DEFAULT 3 NOT NULL CHECK (estrelas_final >= 1 AND estrelas_final <= 5),
    classificacao VARCHAR(10) CHECK (classificacao IN ('leve', 'medio', 'pesado')),
    classificacao_sugerida_ia VARCHAR(10) CHECK (classificacao_sugerida_ia IN ('leve', 'medio', 'pesado')),
    valor_calculado FLOAT DEFAULT 0.0 NOT NULL,
    imagem_url VARCHAR(500),
    observacoes TEXT,
    data_registro TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW() NOT NULL,
    lote_id INTEGER REFERENCES lotes(id)
);

-- Criar tabela de entradas de estoque
CREATE TABLE entradas_estoque (
    id SERIAL PRIMARY KEY,
    lote_id INTEGER NOT NULL REFERENCES lotes(id) ON DELETE CASCADE,
    admin_id INTEGER REFERENCES usuarios(id),
    status VARCHAR(20) DEFAULT 'pendente' NOT NULL,
    data_entrada TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW() NOT NULL,
    data_processamento TIMESTAMP WITHOUT TIME ZONE,
    observacoes TEXT
);

-- Criar tabela de notificações
CREATE TABLE notificacoes (
    id SERIAL PRIMARY KEY,
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    titulo VARCHAR(200) NOT NULL,
    mensagem TEXT NOT NULL,
    lida BOOLEAN DEFAULT FALSE NOT NULL,
    data_envio TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW() NOT NULL
);

-- Criar tabela de configurações
CREATE TABLE configuracoes (
    id SERIAL PRIMARY KEY,
    chave VARCHAR(100) UNIQUE NOT NULL,
    valor TEXT NOT NULL,
    descricao VARCHAR(200),
    tipo VARCHAR(50) DEFAULT 'texto',
    data_atualizacao TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
);

-- Inserir configuração de valor base por estrela
INSERT INTO configuracoes (chave, valor, descricao, tipo)
VALUES ('valor_base_por_estrela', '1.00', 'Valor base em reais por estrela para cálculo de preços', 'decimal');

-- Comentários nas tabelas
COMMENT ON TABLE fornecedor_tipo_lote_classificacao IS 'Configuração de estrelas por classificação (leve, médio, pesado) para cada fornecedor e tipo de lote';
COMMENT ON COLUMN fornecedor_tipo_lote_classificacao.leve_estrelas IS 'Número de estrelas (1-5) para classificação leve';
COMMENT ON COLUMN fornecedor_tipo_lote_classificacao.medio_estrelas IS 'Número de estrelas (1-5) para classificação média';
COMMENT ON COLUMN fornecedor_tipo_lote_classificacao.pesado_estrelas IS 'Número de estrelas (1-5) para classificação pesada';
COMMENT ON COLUMN itens_solicitacao.classificacao IS 'Classificação final do lote: leve, medio ou pesado';
COMMENT ON COLUMN itens_solicitacao.classificacao_sugerida_ia IS 'Classificação sugerida pela IA Gemini';
COMMENT ON COLUMN lotes.classificacao_predominante IS 'Classificação predominante dos itens do lote';

-- Script concluído com sucesso
SELECT 'Banco de dados recriado com sucesso!' AS resultado;
