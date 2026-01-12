
"""Script para executar a migração 010 - adicionar colunas de logística na tabela lotes"""
import os
from app import create_app
from app.models import db

app = create_app()

with app.app_context():
    print("🔧 Executando migração 010: Adicionar colunas de logística...\n")
    
    # Ler o arquivo SQL
    with open('migrations/010_add_logistica_tables.sql', 'r', encoding='utf-8') as f:
        sql = f.read()
    
    try:
        # Executar a migração
        db.session.execute(db.text(sql))
        db.session.commit()
        print("✅ Migração 010 executada com sucesso!")
        print("\nColunas adicionadas à tabela lotes:")
        print("  • oc_id")
        print("  • os_id")
        print("  • conferencia_id")
        print("\nTabelas criadas:")
        print("  • ordens_servico")
        print("  • rotas_operacionais")
        print("  • gps_logs")
        print("  • conferencias_recebimento")
    except Exception as e:
        db.session.rollback()
        print(f"❌ Erro ao executar migração: {str(e)}")
        print("\nVerificando se as colunas já existem...")
        
        try:
            result = db.session.execute(db.text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'lotes' 
                AND column_name IN ('oc_id', 'os_id', 'conferencia_id')
            """))
            
            colunas_existentes = [row[0] for row in result]
            
            if len(colunas_existentes) == 3:
                print("✅ As colunas já existem no banco de dados!")
            else:
                print(f"⚠️ Apenas {len(colunas_existentes)} coluna(s) encontrada(s): {colunas_existentes}")
                print("\nTentando adicionar colunas manualmente...")
                
                if 'oc_id' not in colunas_existentes:
                    db.session.execute(db.text("ALTER TABLE lotes ADD COLUMN IF NOT EXISTS oc_id INTEGER REFERENCES ordens_compra(id)"))
                if 'os_id' not in colunas_existentes:
                    db.session.execute(db.text("ALTER TABLE lotes ADD COLUMN IF NOT EXISTS os_id INTEGER REFERENCES ordens_servico(id)"))
                if 'conferencia_id' not in colunas_existentes:
                    db.session.execute(db.text("ALTER TABLE lotes ADD COLUMN IF NOT EXISTS conferencia_id INTEGER REFERENCES conferencias_recebimento(id)"))
                
                db.session.commit()
                print("✅ Colunas adicionadas manualmente com sucesso!")
        except Exception as e2:
            db.session.rollback()
            print(f"❌ Erro ao verificar/adicionar colunas: {str(e2)}")
