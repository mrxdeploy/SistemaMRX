
import sys
import os

# Adicionar o diretório atual ao path para importar app
sys.path.append(os.getcwd())

from app import create_app, db
from app.models import OrdemCompra, Solicitacao, ItemSolicitacao, MaterialBase, TabelaPreco, TabelaPrecoItem
from sqlalchemy import func

app = create_app()

with app.app_context():
    print("Investigating High Grade materials in OCs...")
    
    # 1. Find approved OCs
    oc_status_aprovados = ['aprovada', 'em_transporte', 'recebida', 'conferida', 'finalizada']
    
    # 2. Query High Grade items in these OCs
    results = db.session.query(
        MaterialBase.id,
        MaterialBase.nome,
        MaterialBase.classificacao,
        func.sum(ItemSolicitacao.peso_kg).label('peso_total'),
        func.sum(ItemSolicitacao.preco_por_kg_snapshot * ItemSolicitacao.peso_kg).label('valor_total')
    ).join(
        ItemSolicitacao.material
    ).join(
        ItemSolicitacao.solicitacao
    ).join(
        Solicitacao.ordem_compra
    ).filter(
        OrdemCompra.status.in_(oc_status_aprovados),
        ItemSolicitacao.preco_por_kg_snapshot.isnot(None),
        ItemSolicitacao.peso_kg > 0,
        func.lower(MaterialBase.classificacao).in_(['high_grade', 'high'])
    ).group_by(
        MaterialBase.id,
        MaterialBase.nome,
        MaterialBase.classificacao
    ).all()
    
    print(f"Found {len(results)} High Grade materials in approved OCs.")
    
    # 3. Check active price tables for these materials
    tabelas_ativas_ids = [t.id for t in db.session.query(TabelaPreco.id).filter_by(ativo=True).all()]
    print(f"Active Price Table IDs: {tabelas_ativas_ids}")
    
    for mid, nome, classif, peso, valor in results:
        print(f"\nMaterial: {nome} (ID: {mid}, Class: {classif})")
        print(f"  Total Weight: {peso}")
        print(f"  Total Value: {valor}")
        
        # Check prices in active tables
        precos = db.session.query(
            TabelaPreco.nome,
            TabelaPrecoItem.preco_por_kg
        ).join(
            TabelaPreco
        ).filter(
            TabelaPrecoItem.material_id == mid,
            TabelaPrecoItem.tabela_preco_id.in_(tabelas_ativas_ids),
            TabelaPrecoItem.ativo == True
        ).all()
        
        if not precos:
            print("  ❌ NO PRICES in active tables! This item will be skipped by the current logic.")
        else:
            soma_precos = sum(p[1] for p in precos)
            print(f"  Prices found: {precos}")
            print(f"  Sum of prices: {soma_precos}")
            if soma_precos == 0:
                 print("  ❌ Sum of prices is 0! This item will be skipped.")

