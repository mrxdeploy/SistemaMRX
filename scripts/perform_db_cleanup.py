import os
import sys
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database URL
DATABASE_URL = "postgresql://postgres:dWldGAyqtVAsQvMYvTIqBKXTkHedCLAS@shortline.proxy.rlwy.net:26559/railway"

# CNPJs to delete (unformatted because that's how they are stored in DB based on inspection)
SUPPLIERS_TO_DELETE_CNPJ = [
    "15436940000103", # AMAZON.COM.BR
    "35860384000105"  # SHEIK A EVOLUCAO DE RESIDUOS LTDA
]

# Tables to TRUNCATE (Transactional Data)
# Order matters slightly, but CASCADE handles dependencies.
TRANSACTIONAL_TABLES = [
    # Production
    "itens_separados_producao",
    "bags_producao",
    "ordens_producao",
    "residuos",
    "lotes_separacao",
    
    # Inventory & Stock
    "inventario_contagens",
    "inventarios",
    "movimentacoes_estoque",
    "entradas_estoque",
    
    # Orders & Services
    "conferencias_recebimento",
    "rotas_operacionais",
    "gps_logs",
    "ordens_servico",
    "auditoria_oc",
    "ordens_compra",
    
    # Requests & Authorizations
    "solicitacoes_autorizacao_preco",
    "itens_solicitacao",
    "lotes",
    "solicitacoes",
    
    # User / System logs & misc
    "notificacoes",
    "auditoria_logs",
    "visitas_fornecedor",
    "conversas_bot",
    "scanner_analyses",
    "aportes_conquista",
    "conquistas",
    "auditoria_fornecedor_tabela_precos"
]

def perform_cleanup():
    print("--- STARTING DATABASE CLEANUP ---")
    
    try:
        engine = create_engine(DATABASE_URL)
        with engine.connect() as connection:
            # 1. TRUNCATE TRANSACTIONAL TABLES FIRST
            # We do this first to clear the heavy volume of dependencies like 'solicitacoes'
            print("\n--- TRUNCATING TRANSACTIONAL DATA ---")
            for table in TRANSACTIONAL_TABLES:
                try:
                    exists = connection.execute(text(f"SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = '{table}')")).scalar()
                    if exists:
                        print(f"Clearing table: {table}...")
                        connection.execute(text(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE;"))
                    else:
                        print(f"Table {table} does not exist. Skipping.")
                except Exception as e:
                    print(f"ERROR clearing {table}: {e}")

            # 2. DELETE SPECIFIC SUPPLIERS AND THEIR DEPENDENCIES
            print("\n--- DELETING SPECIFIC SUPPLIERS ---")
            
            # List of tables that depend on supplier but are NOT in the truncated list
            # We must manually clear these for the specific suppliers
            SUPPLIER_DEPENDENCY_TABLES = [
                "fornecedor_tabela_precos",
                "fornecedor_tipo_lote",
                "fornecedor_tipo_lote_precos", 
                "fornecedor_classificacao_estrela",
                "fornecedor_funcionario_atribuicao",
                "fornecedor_tipo_lote_classificacao"
            ]

            for cnpj in SUPPLIERS_TO_DELETE_CNPJ:
                # Find ID first
                result = connection.execute(text("SELECT id, nome FROM fornecedores WHERE cnpj = :cnpj"), {"cnpj": cnpj}).fetchone()
                
                if result:
                    supplier_id = result.id
                    supplier_name = result.nome
                    print(f"Deleting supplier: {supplier_name} (ID: {supplier_id}, CNPJ: {cnpj})...")
                    
                    # Delete dependencies first
                    for dep_table in SUPPLIER_DEPENDENCY_TABLES:
                        try:
                            exists = connection.execute(text(f"SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = '{dep_table}')")).scalar()
                            if exists:
                                print(f"  - Cleaning {dep_table} for supplier {supplier_id}...")
                                connection.execute(text(f"DELETE FROM {dep_table} WHERE fornecedor_id = :id"), {"id": supplier_id})
                        except Exception as e:
                            print(f"  - Warning: Could not clear {dep_table}: {e}")

                    # Finally delete the supplier
                    connection.execute(text("DELETE FROM fornecedores WHERE id = :id"), {"id": supplier_id})
                    print("Deleted.")
                else:
                    print(f"Supplier with CNPJ {cnpj} NOT FOUND in database. Skipping.")

            connection.commit()
            print("\n--- CLEANUP COMPLETED SUCCESSFULLY ---")
            print("Preserved tables: usuarios, perfis, fornecedores (others), materiais_base, tipos_lote, veiculos, motoristas, configuracoes etc.")

    except Exception as e:
        print(f"\nFATAL ERROR DURING CLEANUP: {e}")
        sys.exit(1)

if __name__ == "__main__":
    perform_cleanup()
