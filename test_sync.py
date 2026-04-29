import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'app')))

from flask import Flask
from app.models import db, Lote, LoteSeparacao, TipoLote
from decimal import Decimal

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:dWldGAyqtVAsQvMYvTIqBKXTkHedCLAS@shortline.proxy.rlwy.net:26559/railway'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

with app.app_context():
    separacao = LoteSeparacao.query.get(133) # Separação ID 133 for Lote 2026-04295
    if not separacao:
        print("Separação not found")
        sys.exit(1)
        
    lote_pai = separacao.lote
    print(f"Lote Pai ID: {lote_pai.id}, Tipo Lote ID: {lote_pai.tipo_lote_id}")
    
    itens = lote_pai.itens
    print(f"Total itens: {len(itens)}")
    
    for i, item in enumerate(itens):
        print(f"--- Item {i} ---")
        try:
            tipo_lote_id = item.tipo_lote_id
            if not tipo_lote_id and item.material:
                tipo = TipoLote.query.filter_by(nome=item.material.nome).first()
                if tipo:
                    tipo_lote_id = tipo.id
            
            if not tipo_lote_id:
                tipo_lote_id = lote_pai.tipo_lote_id # Fallback
                
            print(f"tipo_lote_id resolvido: {tipo_lote_id}")
            
            if tipo_lote_id is None:
                print("ERRO: tipo_lote_id é None. Isso vai falhar ao criar o Lote (IntegrityError constraint null)")
                
            peso_item = Decimal(str(item.peso_kg))
            peso_pai = Decimal(str(lote_pai.peso_total_kg or 1))
            valor_pai = Decimal(str(lote_pai.valor_total or 0))
            valor_proporcional = (peso_item / peso_pai) * valor_pai if peso_pai > 0 else Decimal(0)
            
            print(f"peso_item: {peso_item}, peso_pai: {peso_pai}, valor_pai: {valor_pai}, valor_prop: {valor_proporcional}")
            
            obs = f"MATERIAL:{item.material.nome}" if item.material else f"Item importado do lote {lote_pai.numero_lote}"
            print(f"Observacoes: {obs}")
            
        except Exception as e:
            print(f"Erro ao processar item {i}: {e}")

