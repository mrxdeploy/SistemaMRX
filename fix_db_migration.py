import psycopg2
import os
from datetime import datetime

# URL do banco de dados Railway
DATABASE_URL = "postgresql://postgres:JLNFuhSFMbRaQlBAxuFynwIOMtLyalqt@centerbeam.proxy.rlwy.net:35419/railway"

def fix_database():
    try:
        print(f"Conectando ao banco de dados...")
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()

        # 1. Adicionar a coluna responsavel_id se não existir
        print("Verificando/Adicionando coluna responsavel_id...")
        cur.execute("""
            ALTER TABLE bags_producao 
            ADD COLUMN IF NOT EXISTS responsavel_id INTEGER REFERENCES usuarios(id);
        """)

        # 2. Alterar a coluna criado_por_id para ser opcional (NULL)
        # O erro 'NotNullViolation' indica que o sistema está tentando criar um Bag sem esse ID
        print("Alterando criado_por_id para permitir valores nulos...")
        cur.execute("""
            ALTER TABLE bags_producao 
            ALTER COLUMN criado_por_id DROP NOT NULL;
        """)

        conn.commit()
        print("Sucesso: Banco de dados atualizado corretamente!")
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Erro ao atualizar banco de dados: {e}")

if __name__ == "__main__":
    fix_database()
