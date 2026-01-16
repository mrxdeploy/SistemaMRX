
import os
from app import create_app, db
from sqlalchemy import text

app = create_app()

def reset_flow():
    with app.app_context():
        print("Starting selective database wipe (Process Data ONLY)...")
        print("Preserving: Fornecedores, Tipos de Lote, Tabela de Preços, Materiais Base, Users...")

        try:
            # 1. Break Self-References in Lotes to avoid FK cycles during deletion
            print("Breaking Lote self-references...")
            db.session.execute(text("UPDATE lotes SET lote_pai_id = NULL"))
            
            # 2. List of tables to DELETE in dependency order (Child -> Parent)
            tables_to_delete = [
                # --- DEPENDENTS OF LOTES / PRODUCTION ---
                'itens_separados_producao',
                'bags_producao',
                'ordens_producao', # References Lote (lote_origem_id)
                'classificacoes_grade', 
                
                'residuos',
                'lotes_separacao',       # References Lote
                'movimentacoes_estoque', # References Lote
                'entradas_estoque',      # References Lote
                'inventario_contagens',  # References Lote
                'inventarios',
                'itens_solicitacao',     # References Lote and Solicitacao
                
                # --- LOTES (The Hub) ---
                # Must be deleted BEFORE: Conferencias, Ordens Compra, Ordens Servico
                'lotes',
                
                # --- PARENTS of Lotes (Logistics/Procurement) ---
                'conferencias_recebimento',
                
                'gps_logs',
                'rotas_operacionais',
                'ordens_servico', # References OC
                
                'auditoria_oc',
                'solicitacoes_autorizacao_preco',
                'ordens_compra', # References Solicitacao
                'solicitacoes'
            ]
            
            for table in tables_to_delete:
                print(f"Deleting data from: {table}")
                db.session.execute(text(f"DELETE FROM {table}"))
                
            db.session.commit()
            print("SUCCESS: Process flow data cleared.")
            
        except Exception as e:
            db.session.rollback()
            print(f"CRITICAL ERROR: {e}")
            raise e

if __name__ == "__main__":
    reset_flow()
