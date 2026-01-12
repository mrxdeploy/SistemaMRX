
#!/usr/bin/env python3
"""
Script para executar a migração 017 - Tipo de lote genérico
"""

import os
from app import create_app, db

def executar_migracao():
    app = create_app()
    
    with app.app_context():
        print("=" * 60)
        print(" EXECUTANDO MIGRAÇÃO 017 - TIPO DE LOTE GENÉRICO")
        print("=" * 60)
        
        try:
            # Ler arquivo SQL
            migration_file = 'migrations/017_add_tipo_lote_generico.sql'
            
            if not os.path.exists(migration_file):
                print(f"❌ Arquivo de migração não encontrado: {migration_file}")
                return
            
            with open(migration_file, 'r', encoding='utf-8') as f:
                sql = f.read()
            
            # Executar migração
            print("\n📝 Executando SQL...")
            db.session.execute(db.text(sql))
            db.session.commit()
            
            print("\n✅ Migração 017 executada com sucesso!")
            print("   - Tipo de lote genérico (ID: 1) criado/atualizado")
            
        except Exception as e:
            db.session.rollback()
            print(f"\n❌ Erro ao executar migração: {str(e)}")
            raise
        
        print("=" * 60)

if __name__ == '__main__':
    executar_migracao()
