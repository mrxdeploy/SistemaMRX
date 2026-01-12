-- Migração 010: Adicionar tabelas de Logística (OS, Rotas, GPS, Conferência)
-- Data: 2025-11-15

-- Criar tabela de Ordens de Serviço
CREATE TABLE IF NOT EXISTS ordens_servico (
    id SERIAL PRIMARY KEY,
    oc_id INTEGER NOT NULL REFERENCES ordens_compra(id) ON DELETE CASCADE,
    numero_os VARCHAR(50) UNIQUE NOT NULL,
    fornecedor_snapshot JSONB NOT NULL,
    tipo VARCHAR(20) NOT NULL DEFAULT 'COLETA',
    janela_coleta_inicio TIMESTAMP,
    janela_coleta_fim TIMESTAMP,
    motorista_id INTEGER REFERENCES motoristas(id) ON DELETE SET NULL,
    veiculo_id INTEGER REFERENCES veiculos(id) ON DELETE SET NULL,
    rota JSONB,
    status VARCHAR(50) NOT NULL DEFAULT 'PENDENTE',
    gps_logs JSONB DEFAULT '[]'::jsonb,
    attachments JSONB DEFAULT '[]'::jsonb,
    created_by INTEGER NOT NULL REFERENCES usuarios(id),
    auditoria JSONB DEFAULT '[]'::jsonb,
    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Criar índices para ordens_servico
CREATE INDEX IF NOT EXISTS idx_os_oc_id ON ordens_servico(oc_id);
CREATE INDEX IF NOT EXISTS idx_os_motorista_id ON ordens_servico(motorista_id);
CREATE INDEX IF NOT EXISTS idx_os_veiculo_id ON ordens_servico(veiculo_id);
CREATE INDEX IF NOT EXISTS idx_os_status ON ordens_servico(status);
CREATE INDEX IF NOT EXISTS idx_os_criado_em ON ordens_servico(criado_em);

-- Criar tabela de Rotas Operacionais
CREATE TABLE IF NOT EXISTS rotas_operacionais (
    id SERIAL PRIMARY KEY,
    os_id INTEGER NOT NULL REFERENCES ordens_servico(id) ON DELETE CASCADE,
    motorista_id INTEGER NOT NULL REFERENCES motoristas(id) ON DELETE CASCADE,
    veiculo_id INTEGER NOT NULL REFERENCES veiculos(id) ON DELETE CASCADE,
    pontos JSONB NOT NULL,
    km_estimado REAL,
    km_real REAL,
    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    finalizado_em TIMESTAMP
);

-- Criar índices para rotas_operacionais
CREATE INDEX IF NOT EXISTS idx_rota_os_id ON rotas_operacionais(os_id);
CREATE INDEX IF NOT EXISTS idx_rota_motorista_id ON rotas_operacionais(motorista_id);
CREATE INDEX IF NOT EXISTS idx_rota_veiculo_id ON rotas_operacionais(veiculo_id);

-- Criar tabela de GPS Logs
CREATE TABLE IF NOT EXISTS gps_logs (
    id SERIAL PRIMARY KEY,
    os_id INTEGER NOT NULL REFERENCES ordens_servico(id) ON DELETE CASCADE,
    evento VARCHAR(50) NOT NULL,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    precisao REAL,
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    device_id VARCHAR(255),
    ip VARCHAR(50),
    dados_adicionais JSONB
);

-- Criar índices para gps_logs
CREATE INDEX IF NOT EXISTS idx_gps_os_id ON gps_logs(os_id);
CREATE INDEX IF NOT EXISTS idx_gps_timestamp ON gps_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_gps_evento ON gps_logs(evento);

-- Criar tabela de Conferência de Recebimento
CREATE TABLE IF NOT EXISTS conferencias_recebimento (
    id SERIAL PRIMARY KEY,
    os_id INTEGER NOT NULL REFERENCES ordens_servico(id) ON DELETE CASCADE,
    oc_id INTEGER NOT NULL REFERENCES ordens_compra(id) ON DELETE CASCADE,
    peso_fornecedor REAL,
    peso_real REAL,
    fotos_pesagem JSONB DEFAULT '[]'::jsonb,
    qualidade VARCHAR(50),
    divergencia BOOLEAN NOT NULL DEFAULT FALSE,
    tipo_divergencia VARCHAR(50),
    percentual_diferenca REAL,
    conferencia_status VARCHAR(50) NOT NULL DEFAULT 'PENDENTE',
    conferente_id INTEGER REFERENCES usuarios(id),
    auditoria JSONB DEFAULT '[]'::jsonb,
    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    decisao_adm VARCHAR(50),
    decisao_adm_por INTEGER REFERENCES usuarios(id),
    decisao_adm_em TIMESTAMP,
    decisao_adm_motivo TEXT
);

-- Criar índices para conferencias_recebimento
CREATE INDEX IF NOT EXISTS idx_conf_os_id ON conferencias_recebimento(os_id);
CREATE INDEX IF NOT EXISTS idx_conf_oc_id ON conferencias_recebimento(oc_id);
CREATE INDEX IF NOT EXISTS idx_conf_status ON conferencias_recebimento(conferencia_status);
CREATE INDEX IF NOT EXISTS idx_conf_conferente_id ON conferencias_recebimento(conferente_id);
CREATE INDEX IF NOT EXISTS idx_conf_criado_em ON conferencias_recebimento(criado_em);
CREATE INDEX IF NOT EXISTS idx_conf_decisao_adm_por ON conferencias_recebimento(decisao_adm_por);

-- Criar função para atualizar updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.atualizado_em = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Criar triggers para atualizar automaticamente atualizado_em
CREATE TRIGGER update_os_atualizado_em BEFORE UPDATE ON ordens_servico
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_conf_atualizado_em BEFORE UPDATE ON conferencias_recebimento
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Comentários nas tabelas
COMMENT ON TABLE ordens_servico IS 'Ordens de Serviço de logística vinculadas a Ordens de Compra';
COMMENT ON TABLE rotas_operacionais IS 'Rotas operacionais para motoristas executarem';
COMMENT ON TABLE gps_logs IS 'Logs de GPS para rastreamento de eventos em tempo real';
COMMENT ON TABLE conferencias_recebimento IS 'Conferência de recebimento de materiais na matriz';
