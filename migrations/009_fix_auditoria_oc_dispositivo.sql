
-- Migração para corrigir tamanho do campo dispositivo em auditoria_oc
-- Data: 2025-11-14

ALTER TABLE auditoria_oc 
ALTER COLUMN dispositivo TYPE VARCHAR(500);

-- Comentário explicativo
COMMENT ON COLUMN auditoria_oc.dispositivo IS 'User-Agent do dispositivo (até 500 caracteres para suportar user-agents longos)';
