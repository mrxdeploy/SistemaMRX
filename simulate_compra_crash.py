import sys
import os
import logging

# Configure logging to catch everything
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

sys.path.append(os.getcwd())

from app import create_app
from app.models import db, TabelaPreco, TabelaPrecoItem, MaterialBase, ItemSolicitacao, Solicitacao, OrdemCompra
from sqlalchemy import func

app = create_app()

def simulate_route():
    print("=== SIMULATION START ===")
    try:
        # 1. Main Query
        oc_status_aprovados = ['aprovada', 'em_transporte', 'recebida', 'conferida', 'finalizada']
        
        print("Executing Main Query...")
        resultados = db.session.query(
            MaterialBase.id,
            MaterialBase.codigo,
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
            ItemSolicitacao.peso_kg > 0
        ).group_by(
            MaterialBase.id,
            MaterialBase.codigo,
            MaterialBase.nome,
            MaterialBase.classificacao
        ).order_by(
            MaterialBase.classificacao,
            MaterialBase.nome
        ).all()
        
        print(f"Main Query returned {len(resultados)} rows.")
        
        # 2. Table Prices Query
        print("Executing Table Prices Query...")
        tabelas_ativas_ids = [t.id for t in db.session.query(TabelaPreco.id).filter_by(ativo=True).all()]
        
        soma_precos_por_material = {}
        if tabelas_ativas_ids:
            precos_itens = db.session.query(
                TabelaPrecoItem.material_id,
                func.sum(TabelaPrecoItem.preco_por_kg)
            ).filter(
                TabelaPrecoItem.tabela_preco_id.in_(tabelas_ativas_ids),
                TabelaPrecoItem.ativo == True
            ).group_by(
                TabelaPrecoItem.material_id
            ).all()
            
            soma_precos_por_material = {pid: float(soma or 0) for pid, soma in precos_itens}
            print(f"Prices dictionary built with {len(soma_precos_por_material)} items.")

        # 3. Processing Loop (The suspected failure point)
        print("Starting Loop Processing...")
        dados = {}
        processed_count = 0
        
        for row in resultados:
            # Manual Unpacking Check
            if len(row) < 6:
                print(f"WARNING: Row has length {len(row)}, skipping.")
                continue
                
            mat_id = row[0]
            mat_codigo = row[1]
            mat_nome = row[2]
            mat_classif = row[3]
            peso = row[4]
            valor = row[5]
            
            # Data Type Checks
            p = float(peso or 0)
            v = float(valor or 0)
            
            soma_tabelas = soma_precos_por_material.get(mat_id, 0.0)
            
            # Division Check
            media = round(v / soma_tabelas, 2) if soma_tabelas > 0 else 0.0
            
            # Simple aggregation simulation
            cat_key = mat_classif or 'OUTROS'
            processed_count += 1
            
        print(f"Successfully processed {processed_count} items.")
        print("=== SIMULATION SUCCESS ===")

    except Exception as e:
        print("\n!!! CRASH DETECTED !!!")
        print(f"Error Type: {type(e)}")
        print(f"Error Message: {str(e)}")
        import traceback
        traceback.print_exc()

with app.app_context():
    simulate_route()
