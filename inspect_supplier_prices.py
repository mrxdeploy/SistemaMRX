
import sys
import os
from sqlalchemy import create_engine, text

db_url = "postgresql://postgres:dWldGAyqtVAsQvMYvTIqBKXTkHedCLAS@shortline.proxy.rlwy.net:26559/railway"

try:
    engine = create_engine(db_url)
    connection = engine.connect()
    
    with open('inspect_supplier_prices.txt', 'w', encoding='utf-8') as f:
        f.write("--- Supplier Prices Inspection Start ---\n")
        
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
                f.write(f"  ❌ Material '{mat_name}' not found.\n")
                continue
                
            mat_id = result_mat[0]
            f.write(f"  ID: {mat_id}, Class: {result_mat[2]}\n")
            
            # Query FornecedorTabelaPrecos
            query_prices = text("""
                SELECT ftp.preco_fornecedor, ftp.status, f.nome 
                FROM fornecedor_tabela_precos ftp
                JOIN fornecedores f ON ftp.fornecedor_id = f.id
                WHERE ftp.material_id = :mat_id
                AND ftp.status = 'ativo'
            """)
            
            result_prices = connection.execute(query_prices, {"mat_id": mat_id}).fetchall()
            
            if not result_prices:
                f.write("  ❌ No entries in 'fornecedor_tabela_precos' (status='ativo').\n")
            else:
                soma = 0
                f.write(f"  Found {len(result_prices)} active supplier prices:\n")
                for row in result_prices:
                    val = float(row[0] or 0)
                    f.write(f"    - Supplier '{row[2]}': {val}\n")
                    soma += val
                f.write(f"  Total Sum: {soma}\n")

        f.write("\n--- Supplier Prices Inspection End ---\n")
    connection.close()

except Exception as e:
    with open('inspect_supplier_prices.txt', 'w', encoding='utf-8') as f:
        f.write(f"Error: {str(e)}\n")
