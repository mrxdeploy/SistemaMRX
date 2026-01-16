import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

DATABASE_URL = "postgresql://postgres:dWldGAyqtVAsQvMYvTIqBKXTkHedCLAS@shortline.proxy.rlwy.net:26559/railway"

def list_suppliers():
    engine = create_engine(DATABASE_URL)
    with engine.connect() as connection:
        result = connection.execute(text("SELECT id, nome, cnpj FROM fornecedores")).fetchall()
        print("\n--- EXISTING SUPPLIERS ---")
        for row in result:
            print(f"ID: {row.id} | Nome: {row.nome} | CNPJ: {row.cnpj}")

if __name__ == "__main__":
    list_suppliers()
