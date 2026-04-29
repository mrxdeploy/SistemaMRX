import os
import sys

# Add app directory to sys.path to import models
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'app')))

from flask import Flask
from app.models import db, Lote, LoteSeparacao, ItemSolicitacao

app = Flask(__name__)
# Use the provided database URL
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:dWldGAyqtVAsQvMYvTIqBKXTkHedCLAS@shortline.proxy.rlwy.net:26559/railway'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

with app.app_context():
    lote1 = Lote.query.filter_by(numero_lote='2026-04295').first()
    lote2 = Lote.query.filter_by(numero_lote='2026-04299').first()

    def print_lote_info(lote):
        if not lote:
            print("Lote not found")
            return
        
        print(f"Lote: {lote.numero_lote} (ID: {lote.id})")
        print(f"  Status: {lote.status}")
        print(f"  Peso original: {lote.peso_bruto_recebido} / {lote.peso_liquido} / {lote.peso_total_kg}")
        
        # Check solicitacao_origem_id
        print(f"  Solicitação Origem ID: {lote.solicitacao_origem_id}")
        
        # Check separacao
        separacoes = LoteSeparacao.query.filter_by(lote_id=lote.id).all()
        for sep in separacoes:
            print(f"  Separação: ID {sep.id}, Status {sep.status}, Operador {sep.operador_id}")
            print(f"    Sublotes peso: {sep.peso_total_sublotes}, Residuos: {sep.peso_total_residuos}")

        # Check sublotes
        sublotes = Lote.query.filter_by(lote_pai_id=lote.id).all()
        print(f"  Sublotes count: {len(sublotes)}")
        for sub in sublotes:
            print(f"    Sublote: {sub.numero_lote}, Peso: {sub.peso_total_kg}")

        # Check itens if Lote has itens
        try:
            itens = lote.itens
            print(f"  Itens do lote count: {len(itens)}")
            for item in itens:
                 print(f"    Item: ID {item.id}, Peso {item.peso_kg}, Material ID {item.material_id}")
        except Exception as e:
            print(f"  Lote não tem atributo itens ou erro: {e}")

    print("=== LOTE 1 (Com Problema) ===")
    print_lote_info(lote1)
    print("\n=== LOTE 2 (Correto) ===")
    print_lote_info(lote2)

