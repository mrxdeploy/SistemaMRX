"""
Migration script to add HR-related fields to usuarios table.
Run this script to add the new columns if they don't exist.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text

def run_migration():
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        print("DATABASE_URL not set")
        return False
    
    engine = create_engine(database_url)
    
    with engine.connect() as conn:
        columns_to_add = [
            ("foto_path", "VARCHAR(255)"),
            ("percentual_comissao", "NUMERIC(5,2) DEFAULT 0"),
            ("telefone", "VARCHAR(20)"),
            ("cpf", "VARCHAR(14)"),
            ("data_atualizacao", "TIMESTAMP")
        ]
        
        for column_name, column_type in columns_to_add:
            try:
                result = conn.execute(text(f"""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'usuarios' AND column_name = '{column_name}'
                """))
                
                if result.fetchone() is None:
                    conn.execute(text(f"ALTER TABLE usuarios ADD COLUMN {column_name} {column_type}"))
                    conn.commit()
                    print(f"Added column: {column_name}")
                else:
                    print(f"Column already exists: {column_name}")
            except Exception as e:
                print(f"Error adding column {column_name}: {e}")
                return False
    
    print("Migration completed successfully!")
    return True

if __name__ == "__main__":
    run_migration()
