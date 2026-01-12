"""
Migração: Adicionar campo modalidade_frete à tabela solicitacoes
"""
from app import create_app, db

def migrate():
    app = create_app()
    with app.app_context():
        try:
            # Adicionar coluna modalidade_frete
            db.session.execute(db.text("""
                ALTER TABLE solicitacoes 
                ADD COLUMN IF NOT EXISTS modalidade_frete VARCHAR(10) DEFAULT 'FOB';
            """))
            
            db.session.commit()
            print("✅ Migração concluída: Campo 'modalidade_frete' adicionado à tabela 'solicitacoes'")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Erro na migração: {e}")
            raise

if __name__ == '__main__':
    migrate()
