#!/usr/bin/env python3
"""
Script para executar a migração 018_add_fornecedor_tabela_precos
e popular com dados iniciais (seed)
"""
import os
import sys

def main():
    """Função principal com um único contexto de app"""
    from app import create_app
    from app.models import db, Fornecedor, MaterialBase, Usuario, FornecedorTabelaPrecos
    
    app = create_app()
    
    with app.app_context():
        print("=" * 60)
        print("Migração 018: Tabela fornecedor_tabela_precos")
        print("=" * 60)
        
        migration_path = 'migrations/018_add_fornecedor_tabela_precos.sql'
        
        if not os.path.exists(migration_path):
            print(f"Erro: Arquivo de migração não encontrado: {migration_path}")
            sys.exit(1)
        
        print("\nIniciando migração 018_add_fornecedor_tabela_precos...")
        
        with open(migration_path, 'r') as f:
            sql_content = f.read()
        
        try:
            db.session.execute(db.text(sql_content))
            db.session.commit()
            print("✓ Migração executada com sucesso!")
        except Exception as e:
            db.session.rollback()
            print(f"Erro ao executar migração: {e}")
            sys.exit(1)
        
        print("\nVerificando tabelas criadas...")
        tabelas = ['fornecedor_tabela_precos', 'auditoria_fornecedor_tabela_precos']
        
        for tabela in tabelas:
            result = db.session.execute(db.text(f"""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = '{tabela}'
                )
            """))
            existe = result.scalar()
            
            if existe:
                count_result = db.session.execute(db.text(f"SELECT COUNT(*) FROM {tabela}"))
                count = count_result.scalar()
                print(f"  ✓ Tabela '{tabela}' existe ({count} registros)")
            else:
                print(f"  ✗ Tabela '{tabela}' NÃO existe")
                sys.exit(1)
        
        print("\nPopulando dados de seed...")
        
        fornecedores = Fornecedor.query.filter_by(ativo=True).limit(3).all()
        materiais = MaterialBase.query.filter_by(ativo=True).limit(5).all()
        admin = Usuario.query.filter_by(tipo='admin').first()
        
        if not fornecedores:
            print("Aviso: Nenhum fornecedor ativo encontrado para seed")
        elif not materiais:
            print("Aviso: Nenhum material ativo encontrado para seed")
        else:
            precos_base = {
                'leve': 2.50,
                'medio': 4.00,
                'pesado': 6.50
            }
            
            contador = 0
            for fornecedor in fornecedores:
                for material in materiais:
                    existente = FornecedorTabelaPrecos.query.filter_by(
                        fornecedor_id=fornecedor.id,
                        material_id=material.id,
                        versao=1
                    ).first()
                    
                    if existente:
                        continue
                    
                    preco_base = precos_base.get(material.classificacao, 3.00)
                    variacao = (hash(f"{fornecedor.id}{material.id}") % 100) / 100
                    preco_final = round(preco_base * (0.9 + variacao * 0.3), 2)
                    
                    novo_preco = FornecedorTabelaPrecos(
                        fornecedor_id=fornecedor.id,
                        material_id=material.id,
                        preco_fornecedor=preco_final,
                        status='ativo',
                        versao=1,
                        created_by=admin.id if admin else None
                    )
                    db.session.add(novo_preco)
                    contador += 1
            
            try:
                db.session.commit()
                print(f"✓ {contador} registros de preços criados com sucesso!")
            except Exception as e:
                db.session.rollback()
                print(f"Erro ao popular dados de seed: {e}")
                sys.exit(1)
        
        print("\n" + "=" * 60)
        print("Migração concluída com sucesso!")
        print("=" * 60)

if __name__ == '__main__':
    main()
