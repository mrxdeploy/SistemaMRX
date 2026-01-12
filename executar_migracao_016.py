
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def executar_migracao():
    DATABASE_URL = os.getenv('DATABASE_URL')
    
    if not DATABASE_URL:
        print("❌ DATABASE_URL não configurada")
        return
    
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        print("🔧 Executando migração 016: Adicionar colunas faltantes à tabela lotes...")
        
        with open('migrations/016_add_missing_lote_columns.sql', 'r') as f:
            sql = f.read()
            cursor.execute(sql)
        
        conn.commit()
        
        print("\n✅ Migração 016 executada com sucesso!")
        print("\nColunas adicionadas à tabela lotes:")
        print("  • peso_bruto_recebido")
        print("  • peso_liquido")
        print("  • qualidade_recebida")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Erro ao executar migração: {e}")
        if conn:
            conn.rollback()

if __name__ == '__main__':
    executar_migracao()
