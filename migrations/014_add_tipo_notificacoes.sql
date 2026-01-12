ALTER TABLE notificacoes ADD COLUMN IF NOT EXISTS tipo VARCHAR(50) DEFAULT NULL;

UPDATE notificacoes SET tipo = 'geral' WHERE tipo IS NULL;

COMMENT ON COLUMN notificacoes.tipo IS 'Tipo/categoria da notificação para filtros e roteamento (ex: nova_conferencia, divergencia_conferencia, decisao_conferencia)';
