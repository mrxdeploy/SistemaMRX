import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'app')))

from flask import Flask
from app.models import db, Lote
from sqlalchemy import func

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:dWldGAyqtVAsQvMYvTIqBKXTkHedCLAS@shortline.proxy.rlwy.net:26559/railway'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

with app.app_context():
    ano = 2026
    count_lotes = Lote.query.filter(Lote.numero_lote.like(f"{ano}-%")).count()
    
    # Try the next 15 numbers to see if any already exists
    print(f"Current count: {count_lotes}")
    for i in range(1, 16):
        test_num = f"{ano}-{str(count_lotes + i).zfill(5)}"
        exists = Lote.query.filter_by(numero_lote=test_num).first()
        if exists:
            print(f"ERRO: Lote {test_num} ALREADY EXISTS! (ID: {exists.id})")
        else:
            print(f"Lote {test_num} is available.")
            
    # Em rotas: numero_sequencial = Lote.query.filter(Lote.numero_lote.like(f"{ano}-%")).count() + 1
    # Isso tem grande chance de falhar se houver "buracos" causados por exclusões.
