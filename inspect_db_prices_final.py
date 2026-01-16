
import sys
import os
from sqlalchemy import create_engine, text

# Database URL provided by the user
db_url = "postgresql://postgres:dWldGAyqtVAsQvMYvTIqBKXTkHedCLAS@shortline.proxy.rlwy.net:26559/railway"

try:
    engine = create_engine(db_url)
    connection = engine.connect()
    
    with open('db_inspection_output.txt', 'w', encoding='utf-8') as f:
        f.write("--- Database Inspection Start ---\n")
        
        # 1. Get IDs of active Price Tables
        query_tabelas = text("SELECT id, nome FROM tabelas_preco WHERE ativo = true;")
        result_tabelas = connection.execute(query_tabelas).fetchall()
        active_table_ids = [row[0] for row in result_tabelas]
        f.write(f"Active Price Tables: {result_tabelas}\n")
        
        if not active_table_ids:
            f.write("CRITICAL: No active price tables found!\n")
        else:
            # 2. Check materials shown in the screenshot
            target_materials = [
                'SUCATA PLACA CENTRAL B',
                'SUCATA PLACA HD',
                'SUCATA PLACA DE CELULAR'
            ]
            
            for mat_name in target_materials:
                f.write(f"\nChecking Material: '{mat_name}'\n")
                
                # Get Material ID
                query_mat = text("SELECT id, nome, classificacao FROM materiais_base WHERE nome ILIKE :nome")
                result_mat = connection.execute(query_mat, {"nome": mat_name}).fetchone()
                
                if not result_mat:
                    f.write(f"  ❌ Material '{mat_name}' not found in 'materiais_base' table.\n")
                    continue
                    
                mat_id = result_mat[0]
                f.write(f"  Found Material ID: {mat_id}, Classificacao: {result_mat[2]}\n")
                
                # Check Price Items for this material in ACTIVE tables
                tables_str = ', '.join(str(id) for id in active_table_ids)
                
                # CORRECTED TABLE NAME: tabela_preco_itens (singular tabela, plural itens as per the model definition)
                # Model TabelaPrecoItem -> __tablename__ = 'tabela_preco_itens'
                
                query_prices = text(f"""
                    SELECT tpi.preco_por_kg, tpi.ativo, tp.nome 
                    FROM tabela_preco_itens tpi
                    JOIN tabelas_preco tp ON tpi.tabela_preco_id = tp.id
                    WHERE tpi.material_id = :mat_id 
                    AND tpi.tabela_preco_id IN ({tables_str})
                """)
                
                result_prices = connection.execute(query_prices, {"mat_id": mat_id}).fetchall()
                
                if not result_prices:
                    f.write(f"  ❌ No price entries found in ACTIVE tables ({tables_str}).\n")
                else:
                    soma = 0
                    f.write(f"  Found {len(result_prices)} entries in active tables:\n")
                    for row in result_prices:
                        status = "Active" if row[1] else "Inactive"
                        val = float(row[0]) if row[0] is not None else 0.0
                        f.write(f"    - Table '{row[2]}': Value {val} ({status})\n")
                        if row[1]: # If item entry is active
                            soma += val
                    
                    f.write(f"  Sum of active prices: {soma}\n")
                    if soma == 0:
                         f.write("  ⚠️ Sum is 0, which explains why Media R$ is 0.\n")

        f.write("\n--- Database Inspection End ---\n")
    connection.close()
    
except Exception as e:
    with open('db_inspection_output.txt', 'w', encoding='utf-8') as f:
        f.write(f"Error connecting or querying: {str(e)}\n")
