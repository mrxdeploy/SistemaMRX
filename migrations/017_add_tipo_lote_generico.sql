
-- Migração 017: Adicionar tipo de lote genérico para sistema de materiais
-- Data: 2025-11-18

BEGIN;

-- Inserir tipo de lote genérico se não existir
INSERT INTO tipos_lote (id, nome, codigo, descricao, classificacao, ativo, data_cadastro)
VALUES (
    1,
    'Material Eletrônico',
    'MAT-GEN',
    'Tipo genérico para materiais eletrônicos diversos',
    NULL,
    TRUE,
    NOW()
)
ON CONFLICT (id) DO UPDATE SET
    nome = 'Material Eletrônico',
    codigo = 'MAT-GEN',
    descricao = 'Tipo genérico para materiais eletrônicos diversos',
    ativo = TRUE;

-- Comentário
COMMENT ON TABLE tipos_lote IS 'Tipos de lote - ID 1 é reservado para tipo genérico usado com sistema de materiais';

COMMIT;

-- Log de sucesso
DO $$
BEGIN
    RAISE NOTICE '✓ Migração 017 concluída - Tipo de lote genérico criado/atualizado';
END $$;
