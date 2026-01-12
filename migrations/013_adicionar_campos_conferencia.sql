-- Migração 013: Adicionar novos campos à tabela de conferências
-- Data: 2025-11-15
-- Descrição: Adiciona campos quantidade_real, observacoes, gps_conferencia e device_id_conferencia

-- Adicionar campos se ainda não existirem
DO $$ 
BEGIN
    -- Adicionar quantidade_prevista
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'conferencias_recebimento' 
                   AND column_name = 'quantidade_prevista') THEN
        ALTER TABLE conferencias_recebimento 
        ADD COLUMN quantidade_prevista INTEGER;
    END IF;

    -- Adicionar quantidade_real
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'conferencias_recebimento' 
                   AND column_name = 'quantidade_real') THEN
        ALTER TABLE conferencias_recebimento 
        ADD COLUMN quantidade_real INTEGER;
    END IF;

    -- Adicionar observacoes
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'conferencias_recebimento' 
                   AND column_name = 'observacoes') THEN
        ALTER TABLE conferencias_recebimento 
        ADD COLUMN observacoes TEXT;
    END IF;

    -- Adicionar gps_conferencia
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'conferencias_recebimento' 
                   AND column_name = 'gps_conferencia') THEN
        ALTER TABLE conferencias_recebimento 
        ADD COLUMN gps_conferencia JSON;
    END IF;

    -- Adicionar device_id_conferencia
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'conferencias_recebimento' 
                   AND column_name = 'device_id_conferencia') THEN
        ALTER TABLE conferencias_recebimento 
        ADD COLUMN device_id_conferencia VARCHAR(255);
    END IF;
END $$;

-- Adicionar comentários aos campos
COMMENT ON COLUMN conferencias_recebimento.quantidade_prevista IS 'Quantidade prevista de itens';
COMMENT ON COLUMN conferencias_recebimento.quantidade_real IS 'Quantidade real conferida';
COMMENT ON COLUMN conferencias_recebimento.observacoes IS 'Observações do conferente sobre a conferência';
COMMENT ON COLUMN conferencias_recebimento.gps_conferencia IS 'Coordenadas GPS da conferência';
COMMENT ON COLUMN conferencias_recebimento.device_id_conferencia IS 'ID do dispositivo usado na conferência';
