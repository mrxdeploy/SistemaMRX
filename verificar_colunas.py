import psycopg2
import sys

DB_URL = 'postgresql://postgres:dWldGAyqtVAsQvMYvTIqBKXTkHedCLAS@shortline.proxy.rlwy.net:26559/railway'

def list_columns(cur, table_name):
    print(f"\n--- Colunas da tabela '{table_name}' ---")
    cur.execute(f"""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_schema = 'public' AND table_name = '{table_name}'
    """)
    for row in cur.fetchall():
        print(f"  {row[0]} ({row[1]})")

try:
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    
    list_columns(cur, 'solicitacoes')
    list_columns(cur, 'itens_solicitacao')
    list_columns(cur, 'ordens_compra')
    list_columns(cur, 'fornecedor_tabela_precos')
    list_columns(cur, 'materiais_base')
    
    conn.close()

except Exception as e:
    print(f"Erro: {e}")
