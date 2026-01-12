"""
Migração: Adicionar campo tipo_documento à tabela fornecedores
"""
from app import create_app, db

def migrate():
    app = create_app()
    with app.app_context():
        try:
            # Adicionar coluna tipo_documento
            db.session.execute(db.text("""
                ALTER TABLE fornecedores 
                ADD COLUMN IF NOT EXISTS tipo_documento VARCHAR(10) DEFAULT 'cnpj';
            """))
            
            # Atualizar registros existentes baseado em qual campo está preenchido
            db.session.execute(db.text("""
                UPDATE fornecedores 
                SET tipo_documento = CASE 
                    WHEN cpf IS NOT NULL AND cpf != '' THEN 'cpf'
                    ELSE 'cnpj'
                END
                WHERE tipo_documento IS NULL;
            """))
            
            db.session.commit()
            print("✅ Migração concluída: Campo 'tipo_documento' adicionado à tabela 'fornecedores'")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Erro na migração: {e}")
            raise

if __name__ == '__main__':
    migrate()
