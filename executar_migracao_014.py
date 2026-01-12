
"""
Migração 014: Adicionar campos tipo e url à tabela notificacoes
"""
import os
from sqlalchemy import create_engine, text

def executar_migracao():
    """Executa a migração 014"""
    database_url = os.environ.get('DATABASE_URL')
    
    if not database_url:
        print("❌ ERRO: DATABASE_URL não está definido!")
        return False
    
    print("=" * 60)
    print("MIGRAÇÃO 014: Adicionar campos tipo e url em notificações")
    print("=" * 60)
    
    # SQL da migração
    sql_migration = """
    -- Adicionar coluna tipo se não existir
    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'notificacoes' 
            AND column_name = 'tipo'
        ) THEN
            ALTER TABLE notificacoes 
            ADD COLUMN tipo VARCHAR(50) DEFAULT NULL;
            RAISE NOTICE 'Coluna tipo adicionada com sucesso';
        ELSE
            RAISE NOTICE 'Coluna tipo já existe';
        END IF;
    END $$;

    -- Adicionar coluna url se não existir
    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'notificacoes' 
            AND column_name = 'url'
        ) THEN
            ALTER TABLE notificacoes 
            ADD COLUMN url VARCHAR(500) DEFAULT NULL;
            RAISE NOTICE 'Coluna url adicionada com sucesso';
        ELSE
            RAISE NOTICE 'Coluna url já existe';
        END IF;
    END $$;

    -- Atualizar notificações existentes
    UPDATE notificacoes SET tipo = 'geral' WHERE tipo IS NULL;

    -- Adicionar comentários
    COMMENT ON COLUMN notificacoes.tipo IS 'Tipo/categoria da notificação para filtros e roteamento';
    COMMENT ON COLUMN notificacoes.url IS 'URL de destino quando a notificação for clicada';
    """
    
    try:
        # Conectar ao banco
        print(f"\n🔗 Conectando ao banco de dados...")
        engine = create_engine(database_url)
        
        # Executar migração
        print("\n📝 Executando SQL...")
        with engine.connect() as conn:
            conn.execute(text(sql_migration))
            conn.commit()
        
        print("\n✅ Migração 014 executada com sucesso!")
        print("   - Coluna tipo adicionada (VARCHAR(50))")
        print("   - Coluna url adicionada (VARCHAR(500))")
        
        # Verificar se as colunas foram criadas
        print("\n🔍 Verificando colunas criadas...")
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT column_name, data_type, character_maximum_length
                FROM information_schema.columns 
                WHERE table_name = 'notificacoes' 
                AND column_name IN ('tipo', 'url')
                ORDER BY column_name
            """))
            
            colunas = result.fetchall()
            if colunas:
                print("\n✅ Colunas encontradas:")
                for col in colunas:
                    print(f"   - {col[0]}: {col[1]}({col[2]})")
            else:
                print("   ⚠️ Nenhuma coluna encontrada")
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERRO ao executar migração: {e}")
        return False

if __name__ == '__main__':
    executar_migracao()
