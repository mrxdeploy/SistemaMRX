
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')

if not DATABASE_URL:
    print("❌ DATABASE_URL não configurada!")
    exit(1)

print("🔧 Executando migração 015: Adicionar colunas de logística à tabela lotes...\n")

try:
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    
    with open('migrations/015_add_lotes_logistica_columns.sql', 'r', encoding='utf-8') as f:
        migration_sql = f.read()
    
    cursor.execute(migration_sql)
    conn.commit()
    
    print("✅ Migração 015 executada com sucesso!\n")
    print("Colunas adicionadas à tabela lotes:")
    print("  • oc_id")
    print("  • os_id")
    print("  • conferencia_id")
    
    cursor.close()
    conn.close()

except Exception as e:
    print(f"❌ Erro ao executar migração: {str(e)}")
    if conn:
        conn.rollback()
        conn.close()
