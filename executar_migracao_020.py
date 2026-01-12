
#!/usr/bin/env python3
"""
Executa a migração 020 - Adicionar colunas de tabela de preço
"""
import os
from app import create_app, db

def executar_migracao():
    app = create_app()
    
    with app.app_context():
        try:
            print("🔄 Executando migração 020...")
            
            # Ler o arquivo SQL
            with open('migrations/020_add_tabela_preco_columns.sql', 'r', encoding='utf-8') as f:
                sql = f.read()
            
            # Executar a migração
            db.session.execute(db.text(sql))
            db.session.commit()
            
            print("✅ Migração 020 executada com sucesso!")
            print("   - Coluna tabela_preco_status adicionada")
            print("   - Coluna tabela_preco_aprovada_em adicionada")
            print("   - Coluna tabela_preco_aprovada_por_id adicionada")
            
        except Exception as e:
            print(f"❌ Erro na migração: {e}")
            db.session.rollback()
            raise

if __name__ == '__main__':
    executar_migracao()
