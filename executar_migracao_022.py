#!/usr/bin/env python3
"""Script para executar a migração 022 - Adicionar coluna ordem_exportacao"""

import os
import sys
from sqlalchemy import create_engine, text

def executar_migracao():
    """Executa a migração 022"""
    database_url = os.environ.get('DATABASE_URL')
    
    if not database_url:
        print("❌ ERRO: DATABASE_URL não está definido!")
        return False
    
    print("=" * 60)
    print("MIGRAÇÃO 022: Adicionar coluna ordem_exportacao à tabela bags_producao")
    print("=" * 60)
    
    # SQL da migração embutido no script
    sql_migration = """
DO $$
BEGIN
    -- Adicionar coluna ordem_exportacao se não existir
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'bags_producao' 
        AND column_name = 'ordem_exportacao'
    ) THEN
        ALTER TABLE bags_producao 
        ADD COLUMN ordem_exportacao VARCHAR(100);
        RAISE NOTICE 'Coluna ordem_exportacao adicionada com sucesso';
    ELSE
        RAISE NOTICE 'Coluna ordem_exportacao já existe';
    END IF;
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
        
        print("\n✅ Migração 022 executada com sucesso!")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Erro ao executar migração: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    sucesso = executar_migracao()
    sys.exit(0 if sucesso else 1)
