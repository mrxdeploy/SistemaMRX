import psycopg2

conn = psycopg2.connect('postgresql://postgres:dWldGAyqtVAsQvMYvTIqBKXTkHedCLAS@shortline.proxy.rlwy.net:26559/railway')
cur = conn.cursor()

print("Listando tabelas no banco de dados...\n")
cur.execute("""
    SELECT table_name 
    FROM information_schema.tables 
    WHERE table_schema = 'public' 
    ORDER BY table_name
""")

for row in cur.fetchall():
    print(f"  - {row[0]}")

cur.close()
conn.close()
