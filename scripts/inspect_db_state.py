import os
from sqlalchemy import create_engine, text, inspect
from dotenv import load_dotenv

# Use the URL provided by the user
DATABASE_URL = "postgresql://postgres:dWldGAyqtVAsQvMYvTIqBKXTkHedCLAS@shortline.proxy.rlwy.net:26559/railway"

def inspect_database():
    print("--- INSPECTING DATABASE STATE ---")
    try:
        engine = create_engine(DATABASE_URL)
        inspector = inspect(engine)
        
        # 1. List all tables and row counts
        tables = inspector.get_table_names()
        print(f"\nTotal Tables: {len(tables)}")
        
        print("\n--- ROW COUNTS ---")
        with engine.connect() as connection:
            for table in sorted(tables):
                try:
                    count = connection.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
                    print(f"{table}: {count}")
                except Exception as e:
                    print(f"{table}: Error counting ({e})")

            # 2. Check for specific suppliers
            print("\n--- SPECIFIC SUPPLIERS CHECK ---")
            suppliers_to_check = [
                "15.436.940/0001-03", # AMAZON
                "35.860.384/0001-05"  # SHEIK
            ]
            
            for cnpj in suppliers_to_check:
                # Assuming table is 'fornecedores' and column is 'cnpj'
                if 'fornecedores' in tables:
                    query = text("SELECT id, nome, cnpj FROM fornecedores WHERE cnpj = :cnpj")
                    result = connection.execute(query, {"cnpj": cnpj}).fetchone()
                    if result:
                        print(f"FOUND: {result.nome} (ID: {result.id}, CNPJ: {result.cnpj})")
                    else:
                        print(f"NOT FOUND: CNPJ {cnpj}")
                else:
                    print(f"Table 'fornecedores' not found.")

    except Exception as e:
        print(f"FATAL ERROR: {e}")

if __name__ == "__main__":
    inspect_database()
