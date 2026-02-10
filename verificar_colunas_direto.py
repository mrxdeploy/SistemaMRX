import psycopg2
import sys

# DB_URL = 'postgresql://postgres:dWldGAyqtVAsQvMYvTIqBKXTkHedCLAS@shortline.proxy.rlwy.net:26559/railway'
DB_URL = 'postgresql://postgres:dWldGAyqtVAsQvMYvTIqBKXTkHedCLAS@shortline.proxy.rlwy.net:26559/railway'

def check_table(cur, table_name):
    print(f"\n--- {table_name} ---")
    try:
        cur.execute(f"SELECT * FROM {table_name} LIMIT 0")
        cols = [desc[0] for desc in cur.description]
        print(", ".join(cols))
    except Exception as e:
        print(f"Erro ao acessar {table_name}: {e}")
        conn.rollback()

try:
    print("Conectando...")
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    
    check_table(cur, 'solicitacoes')
    check_table(cur, 'itens_solicitacao')
    check_table(cur, 'ordens_compra')
    
    conn.close()

except Exception as e:
    print(f"Erro geral: {e}")
