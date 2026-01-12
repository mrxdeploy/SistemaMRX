
-- Migração 021: Adicionar colunas foto_data e foto_mimetype à tabela usuarios
-- Permite armazenar imagens diretamente no banco de dados (Railway-friendly)

DO $$
BEGIN
    -- Adicionar coluna foto_data se não existir
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'usuarios' 
        AND column_name = 'foto_data'
    ) THEN
        ALTER TABLE usuarios 
        ADD COLUMN foto_data BYTEA;
        RAISE NOTICE 'Coluna foto_data adicionada com sucesso';
    ELSE
        RAISE NOTICE 'Coluna foto_data já existe';
    END IF;

    -- Adicionar coluna foto_mimetype se não existir
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'usuarios' 
        AND column_name = 'foto_mimetype'
    ) THEN
        ALTER TABLE usuarios 
        ADD COLUMN foto_mimetype VARCHAR(50);
        RAISE NOTICE 'Coluna foto_mimetype adicionada com sucesso';
    ELSE
        RAISE NOTICE 'Coluna foto_mimetype já existe';
    END IF;
END $$;

-- Criar índice para melhor performance (opcional)
CREATE INDEX IF NOT EXISTS idx_usuarios_foto_path ON usuarios(foto_path);

-- Verificar se as colunas foram criadas
DO $$
DECLARE
    col_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO col_count
    FROM information_schema.columns 
    WHERE table_name = 'usuarios' 
    AND column_name IN ('foto_data', 'foto_mimetype');
    
    RAISE NOTICE 'Total de colunas de foto encontradas: %', col_count;
END $$;
