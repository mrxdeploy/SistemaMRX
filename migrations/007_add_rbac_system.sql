-- Migration 007: Adicionar Sistema RBAC Completo
-- Data: 12/11/2025
-- Descrição: Adiciona tabelas de Perfis, Veículos, Motoristas e Auditoria + atualiza Usuario

-- 1. Criar tabela de Perfis
CREATE TABLE IF NOT EXISTS perfis (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(50) UNIQUE NOT NULL,
    descricao TEXT,
    permissoes JSONB NOT NULL DEFAULT '{}',
    ativo BOOLEAN NOT NULL DEFAULT TRUE,
    data_cadastro TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    data_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Criar tabela de Veículos
CREATE TABLE IF NOT EXISTS veiculos (
    id SERIAL PRIMARY KEY,
    placa VARCHAR(10) UNIQUE NOT NULL,
    renavam VARCHAR(20) UNIQUE,
    tipo VARCHAR(50) NOT NULL,
    capacidade FLOAT,
    marca VARCHAR(50),
    modelo VARCHAR(50),
    ano INTEGER,
    ativo BOOLEAN NOT NULL DEFAULT TRUE,
    data_cadastro TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    data_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    criado_por INTEGER REFERENCES usuarios(id)
);

-- 3. Criar tabela de Motoristas
CREATE TABLE IF NOT EXISTS motoristas (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    cpf VARCHAR(14) UNIQUE NOT NULL,
    telefone VARCHAR(20),
    email VARCHAR(120),
    cnh VARCHAR(20) UNIQUE,
    categoria_cnh VARCHAR(5),
    veiculo_id INTEGER REFERENCES veiculos(id),
    ativo BOOLEAN NOT NULL DEFAULT TRUE,
    data_cadastro TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    data_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    criado_por INTEGER REFERENCES usuarios(id)
);

-- 4. Criar tabela de Auditoria
CREATE TABLE IF NOT EXISTS auditoria_logs (
    id SERIAL PRIMARY KEY,
    usuario_id INTEGER REFERENCES usuarios(id),
    acao VARCHAR(50) NOT NULL,
    entidade_tipo VARCHAR(50) NOT NULL,
    entidade_id INTEGER,
    detalhes JSONB,
    ip_address VARCHAR(50),
    user_agent VARCHAR(500),
    data_acao TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 5. Criar índices para Auditoria
CREATE INDEX IF NOT EXISTS idx_usuario_data ON auditoria_logs(usuario_id, data_acao);
CREATE INDEX IF NOT EXISTS idx_entidade_acao ON auditoria_logs(entidade_tipo, acao);
CREATE INDEX IF NOT EXISTS idx_data_acao ON auditoria_logs(data_acao);

-- 6. Adicionar colunas ao Usuario (se não existirem)
ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS perfil_id INTEGER REFERENCES perfis(id);
ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS criado_por INTEGER REFERENCES usuarios(id);

-- 7. Inserir os 7 perfis padrão
INSERT INTO perfis (nome, descricao, permissoes) VALUES
(
    'Administrador',
    'Acesso total; define limites; aprova exceções; autoriza descarte; fecha inventário; gerencia usuários e perfis.',
    '{"gerenciar_usuarios": true, "gerenciar_perfis": true, "gerenciar_fornecedores": true, "gerenciar_veiculos": true, "gerenciar_motoristas": true, "criar_solicitacao": true, "aprovar_solicitacao": true, "rejeitar_solicitacao": true, "criar_lote": true, "aprovar_lote": true, "processar_entrada": true, "visualizar_auditoria": true, "exportar_relatorios": true, "definir_limites": true, "autorizar_descarte": true}'::jsonb
),
(
    'Comprador (PJ)',
    'Abre solicitações de compra, cadastra fornecedores, informa entregas/coletas e registra preço pago.',
    '{"criar_fornecedor": true, "editar_fornecedor": true, "criar_solicitacao": true, "visualizar_solicitacao": true, "informar_entrega": true, "registrar_preco": true, "visualizar_fornecedores": true}'::jsonb
),
(
    'Conferente / Estoque',
    'Valida chegada, pesa, confere itens e qualidade; cria lotes e dá entrada no estoque.',
    '{"validar_chegada": true, "pesar_itens": true, "conferir_qualidade": true, "criar_lote": true, "dar_entrada_estoque": true, "visualizar_lotes": true, "visualizar_entradas": true}'::jsonb
),
(
    'Separação',
    'Separa lotes por material/condição; gera sublotes e resíduos para descarte (com aprovação ADM).',
    '{"separar_lotes": true, "criar_sublotes": true, "marcar_residuos": true, "visualizar_lotes": true, "solicitar_descarte": true}'::jsonb
),
(
    'Motorista',
    'Recebe rotas, realiza coletas e envia comprovantes/fotos.',
    '{"visualizar_rotas": true, "registrar_coleta": true, "enviar_comprovante": true, "enviar_fotos": true, "visualizar_dados_pessoais": true}'::jsonb
),
(
    'Financeiro',
    'Emite notas, controla pagamentos e conciliação bancária.',
    '{"emitir_notas": true, "controlar_pagamentos": true, "conciliacao_bancaria": true, "visualizar_fornecedores": true, "visualizar_solicitacoes": true, "exportar_relatorios": true}'::jsonb
),
(
    'Auditoria / BI',
    'Acesso apenas leitura aos painéis e trilhas de auditoria.',
    '{"visualizar_auditoria": true, "visualizar_paineis": true, "visualizar_relatorios": true, "exportar_relatorios": true, "visualizar_usuarios": true, "visualizar_fornecedores": true, "visualizar_solicitacoes": true, "visualizar_lotes": true, "visualizar_entradas": true, "somente_leitura": true}'::jsonb
)
ON CONFLICT (nome) DO NOTHING;

-- 8. Atualizar usuários admin existentes para ter perfil Administrador
UPDATE usuarios 
SET perfil_id = (SELECT id FROM perfis WHERE nome = 'Administrador')
WHERE tipo = 'admin' AND perfil_id IS NULL;

-- 9. Comentários nas tabelas
COMMENT ON TABLE perfis IS 'Perfis de acesso do sistema RBAC com permissões baseadas em JSON';
COMMENT ON TABLE veiculos IS 'Cadastro de veículos para transporte e coleta';
COMMENT ON TABLE motoristas IS 'Cadastro de motoristas vinculados a veículos';
COMMENT ON TABLE auditoria_logs IS 'Logs de auditoria de todas as ações críticas do sistema';

-- Migration completa
