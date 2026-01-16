
import sys
import os
from sqlalchemy import create_engine, text

# Database URL provided by the user
db_url = "postgresql://postgres:dWldGAyqtVAsQvMYvTIqBKXTkHedCLAS@shortline.proxy.rlwy.net:26559/railway"

try:
    engine = create_engine(db_url)
    connection = engine.connect()
    
    print("--- Database Inspection Start ---\n")
    
    # 1. Get IDs of active Price Tables
    query_tabelas = text("SELECT id, nome FROM tabelas_preco WHERE ativo = true;")
    result_tabelas = connection.execute(query_tabelas).fetchall()
    active_table_ids = [row[0] for row in result_tabelas]
    print(f"Active Price Tables: {result_tabelas}")
    
    if not active_table_ids:
        print("CRITICAL: No active price tables found!")
    else:
        # 2. Check materials shown in the screenshot
        target_materials = [
            'SUCATA PLACA CENTRAL B',
            'SUCATA PLACA HD',
            'SUCATA PLACA DE CELULAR'
        ]
        
        for mat_name in target_materials:
            print(f"\nChecking Material: '{mat_name}'")
            
            # Get Material ID
            query_mat = text("SELECT id, nome, classificacao FROM materiais_base WHERE nome ILIKE :nome")
            result_mat = connection.execute(query_mat, {"nome": mat_name}).fetchone()
            
            if not result_mat:
                print(f"  ❌ Material '{mat_name}' not found in 'materiais_base' table.")
                continue
                
            mat_id = result_mat[0]
            print(f"  Found Material ID: {mat_id}, Classificacao: {result_mat[2]}")
            
            # Check Price Items for this material in ACTIVE tables
            # Note: Formatting the list manually for the IN clause to avoid binding issues with lists in text() depending on driver
            tables_str = ', '.join(str(id) for id in active_table_ids)
            query_prices = text(f"""
                SELECT tpi.preco_por_kg, tpi.ativo, tp.nome 
                FROM tabela_precos_itens tpi
                JOIN tabelas_preco tp ON tpi.tabela_preco_id = tp.id
                WHERE tpi.material_id = :mat_id 
                AND tpi.tabela_preco_id IN ({tables_str})
            """)
            
            result_prices = connection.execute(query_prices, {"mat_id": mat_id}).fetchall()
            
            if not result_prices:
                print(f"  ❌ No price entries found in ACTIVE tables ({tables_str}).")
            else:
                soma = 0
                print(f"  Found {len(result_prices)} entries in active tables:")
                for row in result_prices:
                    status = "Active" if row[1] else "Inactive"
                    print(f"    - Table '{row[2]}': Value {row[0]} ({status})")
                    if row[1]: # If item entry is active
                        soma += float(row[0] or 0)
                
                print(f"  Sum of active prices: {soma}")
                if soma == 0:
                     print("  ⚠️ Sum is 0, which explains why Media R$ is 0.")

    print("\n--- Database Inspection End ---")
    connection.close()
    
except Exception as e:
    print(f"Error connecting or querying: {e}")
