"""
Migração para adicionar funcionalidades WMS ao sistema
- Adiciona campos de localização, reservas e bloqueios ao modelo Lote
- Cria tabelas Inventario e InventarioContagem
"""

from app import create_app
from app.models import db

def migrate():
    app = create_app()
    
    with app.app_context():
        print("Iniciando migração WMS...")
        
        try:
            with db.engine.connect() as conn:
                print("Adicionando novos campos ao modelo Lote...")
                
                conn.execute(db.text("""
                    ALTER TABLE lotes 
                    ADD COLUMN IF NOT EXISTS localizacao_atual VARCHAR(100),
                    ADD COLUMN IF NOT EXISTS reservado BOOLEAN DEFAULT FALSE NOT NULL,
                    ADD COLUMN IF NOT EXISTS reservado_para VARCHAR(200),
                    ADD COLUMN IF NOT EXISTS reservado_por_id INTEGER REFERENCES usuarios(id),
                    ADD COLUMN IF NOT EXISTS reservado_em TIMESTAMP,
                    ADD COLUMN IF NOT EXISTS bloqueado BOOLEAN DEFAULT FALSE NOT NULL,
                    ADD COLUMN IF NOT EXISTS tipo_bloqueio VARCHAR(50),
                    ADD COLUMN IF NOT EXISTS bloqueado_por_id INTEGER REFERENCES usuarios(id),
                    ADD COLUMN IF NOT EXISTS bloqueado_em TIMESTAMP,
                    ADD COLUMN IF NOT EXISTS motivo_bloqueio TEXT,
                    ADD COLUMN IF NOT EXISTS gps_inicio JSON,
                    ADD COLUMN IF NOT EXISTS gps_fim JSON,
                    ADD COLUMN IF NOT EXISTS ip_inicio VARCHAR(50),
                    ADD COLUMN IF NOT EXISTS device_id VARCHAR(255);
                """))
                conn.commit()
                
                print("Criando tabela Inventarios...")
                
                conn.execute(db.text("""
                    CREATE TABLE IF NOT EXISTS inventarios (
                        id SERIAL PRIMARY KEY,
                        numero_inventario VARCHAR(50) UNIQUE NOT NULL,
                        tipo VARCHAR(50) DEFAULT 'GERAL' NOT NULL,
                        localizacao VARCHAR(100),
                        status VARCHAR(50) DEFAULT 'EM_ANDAMENTO' NOT NULL,
                        data_inicio TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                        data_finalizacao TIMESTAMP,
                        criado_por_id INTEGER NOT NULL REFERENCES usuarios(id),
                        finalizado_por_id INTEGER REFERENCES usuarios(id),
                        observacoes TEXT,
                        divergencias_consolidadas JSON DEFAULT '[]',
                        auditoria JSON DEFAULT '[]'
                    );
                    
                    CREATE INDEX IF NOT EXISTS idx_status_data ON inventarios(status, data_inicio);
                """))
                conn.commit()
                
                print("Criando tabela InventarioContagens...")
                
                conn.execute(db.text("""
                    CREATE TABLE IF NOT EXISTS inventario_contagens (
                        id SERIAL PRIMARY KEY,
                        inventario_id INTEGER NOT NULL REFERENCES inventarios(id),
                        lote_id INTEGER NOT NULL REFERENCES lotes(id),
                        numero_contagem INTEGER NOT NULL,
                        quantidade_contada DOUBLE PRECISION,
                        peso_contado DOUBLE PRECISION,
                        localizacao_encontrada VARCHAR(100),
                        contador_id INTEGER NOT NULL REFERENCES usuarios(id),
                        data_contagem TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                        observacoes TEXT,
                        fotos JSON DEFAULT '[]',
                        gps JSON,
                        device_id VARCHAR(255),
                        CONSTRAINT uq_inv_lote_contagem UNIQUE (inventario_id, lote_id, numero_contagem)
                    );
                    
                    CREATE INDEX IF NOT EXISTS idx_inventario_lote ON inventario_contagens(inventario_id, lote_id);
                """))
                conn.commit()
                
                print("Migração concluída com sucesso!")
                
        except Exception as e:
            print(f"Erro durante a migração: {e}")
            raise

if __name__ == '__main__':
    migrate()
