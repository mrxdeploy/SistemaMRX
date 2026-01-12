"""
Migração para adicionar novas colunas à tabela scanner_analyses
"""
import os
import sys

def run_migration():
    from app import create_app
    from app.models import db
    from sqlalchemy import text, inspect
    
    app = create_app()
    
    with app.app_context():
        inspector = inspect(db.engine)
        
        if 'scanner_analyses' not in inspector.get_table_names():
            print("Tabela scanner_analyses não existe, será criada automaticamente")
            db.create_all()
            print("Tabelas criadas com sucesso!")
            return
        
        columns = [col['name'] for col in inspector.get_columns('scanner_analyses')]
        print(f"Colunas existentes: {columns}")
        
        migrations = []
        
        if 'components_count' not in columns:
            migrations.append("ALTER TABLE scanner_analyses ADD COLUMN components_count INTEGER")
        
        if 'density_score' not in columns:
            migrations.append("ALTER TABLE scanner_analyses ADD COLUMN density_score FLOAT")
        
        if 'image_data' not in columns:
            migrations.append("ALTER TABLE scanner_analyses ADD COLUMN image_data BYTEA")
        
        if 'image_mimetype' not in columns:
            migrations.append("ALTER TABLE scanner_analyses ADD COLUMN image_mimetype VARCHAR(50)")
        
        for migration in migrations:
            try:
                print(f"Executando: {migration}")
                db.session.execute(text(migration))
                db.session.commit()
                print("OK!")
            except Exception as e:
                print(f"Erro (pode ser ignorado se coluna já existe): {e}")
                db.session.rollback()
        
        print("\nMigração concluída!")

if __name__ == '__main__':
    run_migration()
