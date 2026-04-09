import os
from app import create_app
from app.models import db, Fornecedor, Lote, Solicitacao, TipoLote, FornecedorTipoLotePreco, BagProducao, OrdemCompra

app = create_app()
with app.app_context():
    def print_model_info(model):
        print(f"\nModel: {model.__name__}")
        for column in model.__table__.columns:
            print(f"  {column.name} ({column.type})")

    for m in [Fornecedor, Lote, Solicitacao, FornecedorTipoLotePreco, BagProducao, OrdemCompra]:
        print_model_info(m)
