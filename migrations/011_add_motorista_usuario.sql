
-- Adicionar coluna usuario_id à tabela motoristas
ALTER TABLE motoristas ADD COLUMN IF NOT EXISTS usuario_id INTEGER UNIQUE REFERENCES usuarios(id);

-- Criar índice
CREATE INDEX IF NOT EXISTS idx_motorista_usuario ON motoristas(usuario_id);
