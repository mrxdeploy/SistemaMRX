
-- Migração 016: Adicionar colunas faltantes à tabela lotes
-- Data: 2025-11-15

-- Adicionar colunas que faltam no banco mas existem no modelo
ALTER TABLE lotes ADD COLUMN IF NOT EXISTS peso_bruto_recebido FLOAT;
ALTER TABLE lotes ADD COLUMN IF NOT EXISTS peso_liquido FLOAT;
ALTER TABLE lotes ADD COLUMN IF NOT EXISTS qualidade_recebida VARCHAR(50);

-- Comentários
COMMENT ON COLUMN lotes.peso_bruto_recebido IS 'Peso bruto recebido na conferência';
COMMENT ON COLUMN lotes.peso_liquido IS 'Peso líquido após descontos (se houver)';
COMMENT ON COLUMN lotes.qualidade_recebida IS 'Qualidade avaliada no recebimento';
