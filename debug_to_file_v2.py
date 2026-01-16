
import sys
import os

sys.path.append(os.getcwd())

from app import create_app, db
from app.models import OrdemCompra, Solicitacao, ItemSolicitacao, MaterialBase, TabelaPreco, TabelaPrecoItem
from sqlalchemy import func

app = create_app()

with app.app_context():
    with open('debug_output.txt', 'w', encoding='utf-8') as f:
        f.write("--- DEBUG START ---\n")
        
        # 1. Check approved OCs
        oc_status_aprovados = ['aprovada', 'em_transporte', 'recebida', 'conferida', 'finalizada']
        ocs_count = OrdemCompra.query.filter(OrdemCompra.status.in_(oc_status_aprovados)).count()
        f.write(f"Total Approved OCs: {ocs_count}\n")
        
        # 2. List all materials in approved OCs
        results = db.session.query(
            MaterialBase.id,
            MaterialBase.nome,
            MaterialBase.classificacao,
            func.sum(ItemSolicitacao.peso_kg),
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
            ItemSolicitacao.peso_kg > 0
        ).group_by(
            MaterialBase.id,
            MaterialBase.nome,
            MaterialBase.classificacao
        ).all()
        
        f.write(f"Found {len(results)} distinct materials in approved OCs:\n")
        
        tabelas_ativas_ids = [t.id for t in db.session.query(TabelaPreco.id).filter_by(ativo=True).all()]
        f.write(f"Active Price Table IDs: {tabelas_ativas_ids}\n")

        for mid, nome, classif, peso, valor in results:
            # Cast to floats safely
            peso_f = float(peso) if peso else 0.0
            valor_f = float(valor) if valor else 0.0
            
            f.write(f"\n[Material ID: {mid}] {nome}\n")
            f.write(f"  Classificacao: '{classif}'\n")
            f.write(f"  Peso Total: {peso_f}\n")
            f.write(f"  Valor Total: {valor_f}\n")
            
            precos = db.session.query(
                 TabelaPrecoItem.preco_por_kg,
                 TabelaPrecoItem.tabela_preco_id
            ).filter(
                TabelaPrecoItem.material_id == mid,
                TabelaPrecoItem.tabela_preco_id.in_(tabelas_ativas_ids),
                TabelaPrecoItem.ativo == True
            ).all()
            
            soma_precos = sum(float(p[0]) for p in precos if p[0] is not None)
            f.write(f"  Precos Tabela RAW: {precos}\n")
            f.write(f"  Soma Precos Tabela: {soma_precos}\n")
            
            if soma_precos == 0:
                f.write("  ⚠️ WOULD BE SKIPPED due to zero table price sum\n")
            else:
                f.write(f"  ✅ INCLUDED. Calculated Avg: {valor_f / soma_precos:.2f}\n")
                
        f.write("--- DEBUG END ---\n")
