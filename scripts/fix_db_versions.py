import os
import psycopg2
from urllib.parse import urlparse

def get_db_connection():
    # Tenta pegar a URL do banco das variáveis de ambiente
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        print("Erro: DATABASE_URL não encontrada.")
        return None
    
    return psycopg2.connect(db_url)

def fix_duplicate_versions():
    conn = None
    try:
        conn = get_db_connection()
        if not conn:
            return
        
        cur = conn.cursor()
        
        print("Identificando duplicatas na tabela fornecedor_tabela_precos...")
        
        # Script para recalcular versões se houver duplicatas ou inconsistências
        # Vamos garantir que para cada (fornecedor_id, material_id), as versões sejam sequenciais
        
        cur.execute("""
            WITH RankedPrices AS (
                SELECT 
                    id,
                    fornecedor_id,
                    material_id,
                    versao,
                    created_at,
                    ROW_NUMBER() OVER (
                        PARTITION BY fornecedor_id, material_id 
                        ORDER BY created_at ASC, id ASC
                    ) as correct_version
                FROM fornecedor_tabela_precos
            )
            UPDATE fornecedor_tabela_precos f
            SET versao = r.correct_version
            FROM RankedPrices r
            WHERE f.id = r.id AND f.versao != r.correct_version;
        """)
        
        print(f"Linhas atualizadas: {cur.rowcount}")
        
        conn.commit()
        print("Banco de dados atualizado com sucesso!")
        
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"Erro ao atualizar banco de dados: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    fix_duplicate_versions()
