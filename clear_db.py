import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

# URL do Banco de Dados Railway (conforme scratchpad)
DATABASE_URL = "postgresql://postgres:JLNFuhSFMbRaQlBAxuFynwIOMtLyalqt@centerbeam.proxy.rlwy.net:35419/railway"

def clear_database_except_users():
    """
    Limpa todos os dados das tabelas, exceto a tabela de usuários.
    Usa TRUNCATE com CASCADE para lidar com chaves estrangeiras.
    """
    try:
        engine = create_engine(DATABASE_URL)
        Session = sessionmaker(bind=engine)
        session = Session()

        # Tabelas para limpar (em ordem ou usando CASCADE)
        # De acordo com o contexto do projeto, estas são as tabelas principais
        tables_to_clear = [
            "itens_bag",
            "bags_producao",
            "registros_producao",
            "ordens_producao",
            "classificacoes",
            "estoque_ativo",
            "lotes",
            "fornecedores",
            "notificacoes",
            "mensagens_chat"
        ]

        print("--- Iniciando limpeza do banco de dados ---")
        
        # Desabilitar triggers temporariamente pode ser necessário em alguns casos, 
        # mas TRUNCATE CASCADE costuma ser suficiente e mais seguro.
        
        for table in tables_to_clear:
            try:
                # Verifica se a tabela existe antes de tentar limpar
                check_table = session.execute(text(f"SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = '{table}');")).scalar()
                
                if check_table:
                    print(f"Limpando tabela: {table}...")
                    session.execute(text(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE;"))
                    print(f"Tabela {table} limpa com sucesso.")
                else:
                    print(f"Tabela {table} não encontrada, pulando...")
            except Exception as e:
                print(f"Erro ao limpar tabela {table}: {str(e)}")

        session.commit()
        print("--- Limpeza concluída com sucesso (Usuários preservados) ---")

    except Exception as e:
        print(f"Erro fatal durante a limpeza: {str(e)}")
    finally:
        session.close()

if __name__ == "__main__":
    clear_database_except_users()
