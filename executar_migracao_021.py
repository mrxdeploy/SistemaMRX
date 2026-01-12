
#!/usr/bin/env python3
"""Script para executar a migração 021 - Adicionar colunas foto_data e foto_mimetype"""

import os
import sys
from sqlalchemy import create_engine, text

def executar_migracao():
    """Executa a migração 021"""
    database_url = os.environ.get('DATABASE_URL')
    
    if not database_url:
        print("❌ ERRO: DATABASE_URL não está definido!")
        return False
    
    print("=" * 60)
    print("MIGRAÇÃO 021: Adicionar colunas foto_data e foto_mimetype")
    print("=" * 60)
    
    # SQL da migração embutido no script
    sql_migration = """
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
"""
    
    try:
        # Conectar ao banco
        print(f"\n🔗 Conectando ao banco de dados...")
        print(f"   URL: {database_url[:30]}...")
        
        engine = create_engine(database_url)
        
        # Executar migração
        print("\n📝 Executando SQL...")
        with engine.connect() as conn:
            conn.execute(text(sql_migration))
            conn.commit()
        
        print("\n✅ Migração 021 executada com sucesso!")
        print("   - Coluna foto_data adicionada (BYTEA)")
        print("   - Coluna foto_mimetype adicionada (VARCHAR(50))")
        print("   - Índice idx_usuarios_foto_path criado")
        
        # Verificar se as colunas foram criadas
        print("\n🔍 Verificando colunas criadas...")
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'usuarios' 
                AND column_name IN ('foto_data', 'foto_mimetype')
                ORDER BY column_name
            """))
            
            colunas = result.fetchall()
            for coluna in colunas:
                print(f"   ✓ {coluna[0]}: {coluna[1]}")
        
        print("\n" + "=" * 60)
        print("✨ Migração concluída! O sistema está pronto para uso.")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"\n❌ Erro ao executar migração: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    sucesso = executar_migracao()
    sys.exit(0 if sucesso else 1)
