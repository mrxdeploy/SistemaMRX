-- Migration: 018_add_fornecedor_tabela_precos.sql
-- Descrição: Cria tabela fornecedor_tabela_precos e sua tabela de auditoria
-- Data: 2025-11-29

-- Tabela principal: fornecedor_tabela_precos
CREATE TABLE IF NOT EXISTS fornecedor_tabela_precos (
    id SERIAL PRIMARY KEY,
    fornecedor_id INTEGER NOT NULL REFERENCES fornecedores(id) ON DELETE CASCADE,
    material_id INTEGER NOT NULL REFERENCES materiais_base(id) ON DELETE CASCADE,
    preco_fornecedor NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    status VARCHAR(20) NOT NULL DEFAULT 'ativo' CHECK (status IN ('ativo', 'inativo', 'pendente_aprovacao')),
    versao INTEGER NOT NULL DEFAULT 1 CHECK (versao >= 1),
    created_by INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    updated_by INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    arquivo_origem_id INTEGER,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_fornecedor_material_versao UNIQUE (fornecedor_id, material_id, versao)
);

-- Índices para fornecedor_tabela_precos
CREATE INDEX IF NOT EXISTS idx_fornecedor_material_preco ON fornecedor_tabela_precos(fornecedor_id, material_id);
CREATE INDEX IF NOT EXISTS idx_fornecedor_preco_status ON fornecedor_tabela_precos(status);
CREATE INDEX IF NOT EXISTS idx_fornecedor_preco_versao ON fornecedor_tabela_precos(versao);

-- Tabela de auditoria: auditoria_fornecedor_tabela_precos
CREATE TABLE IF NOT EXISTS auditoria_fornecedor_tabela_precos (
    id SERIAL PRIMARY KEY,
    preco_id INTEGER NOT NULL REFERENCES fornecedor_tabela_precos(id) ON DELETE CASCADE,
    usuario_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    acao VARCHAR(50) NOT NULL CHECK (acao IN ('criacao', 'atualizacao', 'exclusao', 'ativacao', 'desativacao', 'nova_versao')),
    dados_anteriores JSONB,
    dados_novos JSONB,
    ip_address VARCHAR(50),
    user_agent VARCHAR(500),
    data_acao TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Índices para auditoria_fornecedor_tabela_precos
CREATE INDEX IF NOT EXISTS idx_auditoria_ftp_preco ON auditoria_fornecedor_tabela_precos(preco_id);
CREATE INDEX IF NOT EXISTS idx_auditoria_ftp_usuario ON auditoria_fornecedor_tabela_precos(usuario_id);
CREATE INDEX IF NOT EXISTS idx_auditoria_ftp_data ON auditoria_fornecedor_tabela_precos(data_acao);

-- Trigger para atualizar updated_at automaticamente (apenas quando updated_at não foi definido explicitamente)
CREATE OR REPLACE FUNCTION update_fornecedor_tabela_precos_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    IF OLD.updated_at = NEW.updated_at OR NEW.updated_at IS NULL THEN
        NEW.updated_at = CURRENT_TIMESTAMP;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_fornecedor_tabela_precos_updated_at ON fornecedor_tabela_precos;
CREATE TRIGGER trigger_update_fornecedor_tabela_precos_updated_at
    BEFORE UPDATE ON fornecedor_tabela_precos
    FOR EACH ROW
    EXECUTE FUNCTION update_fornecedor_tabela_precos_updated_at();

-- Trigger para registrar auditoria automaticamente
-- Usa updated_by para UPDATE e created_by para INSERT
CREATE OR REPLACE FUNCTION audit_fornecedor_tabela_precos()
RETURNS TRIGGER AS $$
DECLARE
    usuario_acao INTEGER;
    acao_tipo VARCHAR(50);
    dados_ant JSONB;
    dados_nov JSONB;
    preco_id_ref INTEGER;
BEGIN
    usuario_acao := COALESCE(NEW.updated_by, NEW.created_by, OLD.updated_by);

    IF TG_OP = 'INSERT' THEN
        acao_tipo := 'criacao';
        dados_ant := NULL;
        dados_nov := row_to_json(NEW)::jsonb;
        preco_id_ref := NEW.id;
    ELSIF TG_OP = 'UPDATE' THEN
        IF OLD.status != NEW.status THEN
            acao_tipo := CASE 
                WHEN NEW.status = 'ativo' THEN 'ativacao'
                WHEN NEW.status = 'inativo' THEN 'desativacao'
                ELSE 'atualizacao'
            END;
        ELSIF OLD.versao != NEW.versao THEN
            acao_tipo := 'nova_versao';
        ELSE
            acao_tipo := 'atualizacao';
        END IF;
        dados_ant := row_to_json(OLD)::jsonb;
        dados_nov := row_to_json(NEW)::jsonb;
        preco_id_ref := NEW.id;
    ELSIF TG_OP = 'DELETE' THEN
        acao_tipo := 'exclusao';
        dados_ant := row_to_json(OLD)::jsonb;
        dados_nov := NULL;
        usuario_acao := OLD.updated_by;
        preco_id_ref := OLD.id;
    END IF;

    INSERT INTO auditoria_fornecedor_tabela_precos (preco_id, usuario_id, acao, dados_anteriores, dados_novos, data_acao)
        VALUES (preco_id_ref, usuario_acao, acao_tipo, dados_ant, dados_nov, CURRENT_TIMESTAMP);

    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    ELSE
        RETURN NEW;
    END IF;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_audit_fornecedor_tabela_precos ON fornecedor_tabela_precos;
CREATE TRIGGER trigger_audit_fornecedor_tabela_precos
    AFTER INSERT OR UPDATE OR DELETE ON fornecedor_tabela_precos
    FOR EACH ROW
    EXECUTE FUNCTION audit_fornecedor_tabela_precos();

-- Comentários nas tabelas
COMMENT ON TABLE fornecedor_tabela_precos IS 'Tabela de preços personalizada por fornecedor e material com versionamento';
COMMENT ON COLUMN fornecedor_tabela_precos.fornecedor_id IS 'ID do fornecedor';
COMMENT ON COLUMN fornecedor_tabela_precos.material_id IS 'ID do material base';
COMMENT ON COLUMN fornecedor_tabela_precos.preco_fornecedor IS 'Preço oferecido pelo fornecedor (R$/kg)';
COMMENT ON COLUMN fornecedor_tabela_precos.status IS 'Status do preço: ativo, inativo, pendente_aprovacao';
COMMENT ON COLUMN fornecedor_tabela_precos.versao IS 'Versão do registro para controle de histórico';
COMMENT ON COLUMN fornecedor_tabela_precos.created_by IS 'ID do usuário que criou o registro';
COMMENT ON COLUMN fornecedor_tabela_precos.updated_by IS 'ID do usuário que atualizou o registro';
COMMENT ON COLUMN fornecedor_tabela_precos.arquivo_origem_id IS 'ID do arquivo de origem (importação)';

COMMENT ON TABLE auditoria_fornecedor_tabela_precos IS 'Registro de auditoria de alterações na tabela fornecedor_tabela_precos';