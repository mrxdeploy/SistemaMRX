import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'app')))

from flask import Flask
from app.models import db, ModeloTabelaPreco
from sqlalchemy import text

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:dWldGAyqtVAsQvMYvTIqBKXTkHedCLAS@shortline.proxy.rlwy.net:26559/railway'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

with app.app_context():
    try:
        # Add column status if it doesn't exist
        db.session.execute(text("ALTER TABLE modelos_tabela_preco ADD COLUMN IF NOT EXISTS status VARCHAR(50) DEFAULT 'APROVADO' NOT NULL"))
        db.session.commit()
        print("Migração concluída com sucesso: Coluna 'status' adicionada à tabela 'modelos_tabela_preco'.")
    except Exception as e:
        print(f"Erro na migração: {e}")
        db.session.rollback()
