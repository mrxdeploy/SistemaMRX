-- Migration: adiciona campo comprador ao sistema
-- Executar no banco de produção (Railway PostgreSQL)
-- Data: 2026-11-11

-- 1. Adiciona is_comprador nos usuários (default FALSE)
ALTER TABLE usuarios
    ADD COLUMN IF NOT EXISTS is_comprador BOOLEAN NOT NULL DEFAULT FALSE;

-- 2. Marca como comprador todos os usuários com perfil "Comprador (PJ)"
UPDATE usuarios u
SET is_comprador = TRUE
FROM perfis p
WHERE u.perfil_id = p.id
  AND p.nome = 'Comprador (PJ)';

-- 3. Adiciona comprador_id na tabela ordens_compra (nullable para OCs antigas)
ALTER TABLE ordens_compra
    ADD COLUMN IF NOT EXISTS comprador_id INTEGER REFERENCES usuarios(id);

-- 4. Preenche retroativamente: comprador_id = criado_por para OCs existentes
UPDATE ordens_compra
SET comprador_id = criado_por
WHERE comprador_id IS NULL;

-- Verificação (rodar depois para conferir)
-- SELECT COUNT(*) FROM usuarios WHERE is_comprador = TRUE;
-- SELECT COUNT(*) FROM ordens_compra WHERE comprador_id IS NULL;
