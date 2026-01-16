import sys
import os
import logging
import traceback

# Setup file logging
logging.basicConfig(filename='debug_output.txt', level=logging.DEBUG, filemode='w')
logger = logging.getLogger(__name__)

sys.path.append(os.getcwd())

def log(msg):
    print(msg)
    logger.info(msg)

try:
    log("Importing app...")
    from app import create_app
    from app.models import db, TabelaPreco, TabelaPrecoItem, MaterialBase, ItemSolicitacao, Solicitacao, OrdemCompra
    from sqlalchemy import func
    log("App imported.")

    app = create_app()

    with app.app_context():
        log("=== SIMULATION START ===")
        
        # 1. Main Query
        oc_status_aprovados = ['aprovada', 'em_transporte', 'recebida', 'conferida', 'finalizada']
        
        log("Executing Main Query...")
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
        
        log(f"Main Query returned {len(resultados)} rows.")
        if len(resultados) > 0:
            log(f"Sample row: {resultados[0]}")
            log(f"Sample row length: {len(resultados[0])}")
        
        # 2. Table Prices Query
        log("Executing Table Prices Query...")
        tabelas_ativas_ids = [t.id for t in db.session.query(TabelaPreco.id).filter_by(ativo=True).all()]
        log(f"Active Tables: {tabelas_ativas_ids}")
        
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
            log(f"Prices dictionary built with {len(soma_precos_por_material)} items.")

        # 3. Processing Loop
        log("Starting Loop Processing...")
        processed_count = 0
        
        for row in resultados:
            # Manual Unpacking Check
            if len(row) < 6:
                log(f"WARNING: Row has length {len(row)}, skipping.")
                continue
                
            mat_id = row[0]
            mat_codigo = row[1]
            mat_nome = row[2]
            mat_classif = row[3]
            peso = row[4]
            valor = row[5]
            
            p = float(peso or 0)
            v = float(valor or 0)
            
            soma_tabelas = soma_precos_por_material.get(mat_id, 0.0)
            
            # Division Check
            media = round(v / soma_tabelas, 2) if soma_tabelas > 0 else 0.0
            
            processed_count += 1
            
        log(f"Successfully processed {processed_count} items.")
        log("=== SIMULATION SUCCESS ===")

except Exception as e:
    log("\n!!! CRASH DETECTED !!!")
    log(f"Error Type: {type(e)}")
    log(f"Error Message: {str(e)}")
    log(traceback.format_exc())
