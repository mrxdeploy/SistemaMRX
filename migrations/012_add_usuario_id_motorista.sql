
-- Adicionar coluna usuario_id na tabela motoristas
ALTER TABLE motoristas ADD COLUMN IF NOT EXISTS usuario_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL;

-- Criar índice para melhorar performance
CREATE INDEX IF NOT EXISTS idx_motoristas_usuario_id ON motoristas(usuario_id);
