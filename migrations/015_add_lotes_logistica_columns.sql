
-- Migração 015: Adicionar colunas de logística à tabela lotes
-- Data: 2025-11-15

-- Adicionar as colunas que faltam na tabela lotes
ALTER TABLE lotes ADD COLUMN IF NOT EXISTS oc_id INTEGER REFERENCES ordens_compra(id) ON DELETE SET NULL;
ALTER TABLE lotes ADD COLUMN IF NOT EXISTS os_id INTEGER REFERENCES ordens_servico(id) ON DELETE SET NULL;
ALTER TABLE lotes ADD COLUMN IF NOT EXISTS conferencia_id INTEGER REFERENCES conferencias_recebimento(id) ON DELETE SET NULL;

-- Adicionar índices para melhor performance
CREATE INDEX IF NOT EXISTS idx_lotes_oc_id ON lotes(oc_id);
CREATE INDEX IF NOT EXISTS idx_lotes_os_id ON lotes(os_id);
CREATE INDEX IF NOT EXISTS idx_lotes_conferencia_id ON lotes(conferencia_id);

-- Comentários
COMMENT ON COLUMN lotes.oc_id IS 'Referência à Ordem de Compra associada ao lote';
COMMENT ON COLUMN lotes.os_id IS 'Referência à Ordem de Serviço associada ao lote';
COMMENT ON COLUMN lotes.conferencia_id IS 'Referência à Conferência de Recebimento associada ao lote';
