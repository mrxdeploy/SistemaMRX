import psycopg2
import sys

# DB_URL = 'postgresql://postgres:dWldGAyqtVAsQvMYvTIqBKXTkHedCLAS@shortline.proxy.rlwy.net:26559/railway'
DB_URL = 'postgresql://postgres:dWldGAyqtVAsQvMYvTIqBKXTkHedCLAS@shortline.proxy.rlwy.net:26559/railway'

def list_filtered_columns(cur, table_name):
    print(f"\n--- Colunas FILTRADAS da tabela '{table_name}' ---")
    cur.execute(f"""
        SELECT column_name
        FROM information_schema.columns 
        WHERE table_schema = 'public' 
          AND table_name = '{table_name}'
          AND (column_name LIKE '%id%' OR column_name LIKE '%peso%' OR column_name LIKE '%preco%' OR column_name LIKE '%valor%')
        ORDER BY column_name
    """)
    cols = [row[0] for row in cur.fetchall()]
    print(", ".join(cols))

try:
    print("Conectando...")
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    
    list_filtered_columns(cur, 'solicitacoes')
    list_filtered_columns(cur, 'itens_solicitacao')
    list_filtered_columns(cur, 'ordens_compra')
    list_filtered_columns(cur, 'fornecedor_tabela_precos')
    list_filtered_columns(cur, 'materiais_base')
    
    conn.close()

except Exception as e:
    print(f"Erro: {e}")
