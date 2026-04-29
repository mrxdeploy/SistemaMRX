import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'app')))

from flask import Flask
from app.models import db, Lote, LoteSeparacao

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:dWldGAyqtVAsQvMYvTIqBKXTkHedCLAS@shortline.proxy.rlwy.net:26559/railway'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

with app.app_context():
    lote = Lote.query.filter_by(numero_lote='2026-04295').first()
    if lote:
        print(f"Reverting Lote {lote.numero_lote} (ID {lote.id}) from {lote.status} to AGUARDANDO_SEPARACAO")
        lote.status = 'AGUARDANDO_SEPARACAO'
        
        separacao = LoteSeparacao.query.filter_by(lote_id=lote.id).first()
        if separacao:
            print(f"Reverting Separacao {separacao.id} from {separacao.status} to AGUARDANDO_SEPARACAO")
            separacao.status = 'AGUARDANDO_SEPARACAO'
            
        db.session.commit()
        print("Success!")
    else:
        print("Lote not found!")
