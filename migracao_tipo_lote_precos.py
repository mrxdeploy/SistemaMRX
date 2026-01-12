"""
Migração: Unificar tabelas de preços de tipos de lote
- Cria nova tabela tipo_lote_precos
- Migra dados das tabelas antigas (se existirem)
- Remove tabelas antigas
"""
from app import create_app
from app.models import db, TipoLote, TipoLotePreco
from sqlalchemy import text
import sys

def executar_migracao():
    app = create_app()
    
    with app.app_context():
        print("=" * 60)
        print("MIGRAÇÃO: Unificação de preços de tipos de lote")
        print("=" * 60)
        
        try:
            print("\n1. Criando nova tabela tipo_lote_precos...")
            db.create_all()
            print("✓ Tabela tipo_lote_precos criada com sucesso!")
            
            print("\n2. Verificando tabelas antigas para migração...")
            inspector = db.inspect(db.engine)
            tabelas_existentes = inspector.get_table_names()
            
            dados_migrados = 0
            
            if 'tipo_lote_preco_estrelas' in tabelas_existentes:
                print("   - Encontrada tabela tipo_lote_preco_estrelas")
                result = db.session.execute(text("""
                    SELECT tipo_lote_id, estrelas, preco_por_kg, ativo 
                    FROM tipo_lote_preco_estrelas
                """))
                
                for row in result:
                    preco = TipoLotePreco.query.filter_by(
                        tipo_lote_id=row[0],
                        classificacao='medio',
                        estrelas=row[1]
                    ).first()
                    
                    if not preco:
                        preco = TipoLotePreco(
                            tipo_lote_id=row[0],
                            classificacao='medio',
                            estrelas=row[1],
                            preco_por_kg=row[2],
                            ativo=row[3]
                        )
                        db.session.add(preco)
                        dados_migrados += 1
                
                db.session.commit()
                print(f"   ✓ {dados_migrados} registros migrados de tipo_lote_preco_estrelas")
            
            if 'tipo_lote_preco_classificacoes' in tabelas_existentes:
                print("   - Encontrada tabela tipo_lote_preco_classificacoes")
                result = db.session.execute(text("""
                    SELECT tipo_lote_id, classificacao, preco_por_kg, ativo 
                    FROM tipo_lote_preco_classificacoes
                """))
                
                migrados_class = 0
                for row in result:
                    for estrela in range(1, 6):
                        preco = TipoLotePreco.query.filter_by(
                            tipo_lote_id=row[0],
                            classificacao=row[1],
                            estrelas=estrela
                        ).first()
                        
                        if not preco:
                            preco = TipoLotePreco(
                                tipo_lote_id=row[0],
                                classificacao=row[1],
                                estrelas=estrela,
                                preco_por_kg=row[2],
                                ativo=row[3]
                            )
                            db.session.add(preco)
                            migrados_class += 1
                
                db.session.commit()
                print(f"   ✓ {migrados_class} registros migrados de tipo_lote_preco_classificacoes")
            
            print("\n3. Removendo tabelas antigas...")
            if 'tipo_lote_preco_estrelas' in tabelas_existentes:
                db.session.execute(text("DROP TABLE IF EXISTS tipo_lote_preco_estrelas CASCADE"))
                print("   ✓ Tabela tipo_lote_preco_estrelas removida")
            
            if 'tipo_lote_preco_classificacoes' in tabelas_existentes:
                db.session.execute(text("DROP TABLE IF EXISTS tipo_lote_preco_classificacoes CASCADE"))
                print("   ✓ Tabela tipo_lote_preco_classificacoes removida")
            
            db.session.commit()
            
            print("\n4. Verificando dados migrados...")
            total_tipos = TipoLote.query.count()
            total_precos = TipoLotePreco.query.count()
            print(f"   - Total de tipos de lote: {total_tipos}")
            print(f"   - Total de preços configurados: {total_precos}")
            
            print("\n" + "=" * 60)
            print("✓ MIGRAÇÃO CONCLUÍDA COM SUCESSO!")
            print("=" * 60)
            
            return True
            
        except Exception as e:
            print(f"\n✗ ERRO na migração: {str(e)}")
            db.session.rollback()
            return False

if __name__ == '__main__':
    sucesso = executar_migracao()
    sys.exit(0 if sucesso else 1)
