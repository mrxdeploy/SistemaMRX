"""Script para configurar preços para os fornecedores"""
from app import create_app
from app.models import db, Fornecedor, TipoLote, FornecedorTipoLotePreco, ItemSolicitacao, OrdemCompra

app = create_app()

with app.app_context():
    print("🔧 Configurando preços para fornecedores...\n")
    
    # Preços de exemplo (R$ por kg)
    precos_config = [
        # Metais Silva (fornecedor 1)
        {"fornecedor_id": 1, "tipo_lote_nome": "Alumínio", "estrelas": 3, "preco": 8.50},
        {"fornecedor_id": 1, "tipo_lote_nome": "Alumínio", "estrelas": 4, "preco": 10.00},
        {"fornecedor_id": 1, "tipo_lote_nome": "Alumínio", "estrelas": 5, "preco": 12.00},
        {"fornecedor_id": 1, "tipo_lote_nome": "Cobre", "estrelas": 3, "preco": 25.00},
        {"fornecedor_id": 1, "tipo_lote_nome": "Cobre", "estrelas": 4, "preco": 28.00},
        {"fornecedor_id": 1, "tipo_lote_nome": "Cobre", "estrelas": 5, "preco": 32.00},
        {"fornecedor_id": 1, "tipo_lote_nome": "Aço", "estrelas": 3, "preco": 3.50},
        {"fornecedor_id": 1, "tipo_lote_nome": "Aço", "estrelas": 4, "preco": 4.00},
        {"fornecedor_id": 1, "tipo_lote_nome": "Aço", "estrelas": 5, "preco": 4.50},
        
        # Recicla Plásticos (fornecedor 2)
        {"fornecedor_id": 2, "tipo_lote_nome": "Plástico PET", "estrelas": 3, "preco": 2.50},
        {"fornecedor_id": 2, "tipo_lote_nome": "Plástico PET", "estrelas": 4, "preco": 3.00},
        {"fornecedor_id": 2, "tipo_lote_nome": "Plástico PET", "estrelas": 5, "preco": 3.50},
        {"fornecedor_id": 2, "tipo_lote_nome": "Plástico PEAD", "estrelas": 3, "preco": 2.20},
        {"fornecedor_id": 2, "tipo_lote_nome": "Plástico PEAD", "estrelas": 4, "preco": 2.70},
        {"fornecedor_id": 2, "tipo_lote_nome": "Plástico PEAD", "estrelas": 5, "preco": 3.20},
        
        # Papel & Vidro (fornecedor 3)
        {"fornecedor_id": 3, "tipo_lote_nome": "Papel/Papelão", "estrelas": 3, "preco": 0.50},
        {"fornecedor_id": 3, "tipo_lote_nome": "Papel/Papelão", "estrelas": 4, "preco": 0.65},
        {"fornecedor_id": 3, "tipo_lote_nome": "Papel/Papelão", "estrelas": 5, "preco": 0.80},
        {"fornecedor_id": 3, "tipo_lote_nome": "Vidro", "estrelas": 3, "preco": 0.30},
        {"fornecedor_id": 3, "tipo_lote_nome": "Vidro", "estrelas": 4, "preco": 0.40},
        {"fornecedor_id": 3, "tipo_lote_nome": "Vidro", "estrelas": 5, "preco": 0.50},
    ]
    
    precos_criados = 0
    for config in precos_config:
        tipo_lote = TipoLote.query.filter_by(nome=config["tipo_lote_nome"]).first()
        if not tipo_lote:
            print(f"  ⚠️  Tipo de lote '{config['tipo_lote_nome']}' não encontrado")
            continue
        
        # Verificar se já existe
        preco_existente = FornecedorTipoLotePreco.query.filter_by(
            fornecedor_id=config["fornecedor_id"],
            tipo_lote_id=tipo_lote.id,
            estrelas=config["estrelas"]
        ).first()
        
        if preco_existente:
            continue
        
        preco = FornecedorTipoLotePreco(
            fornecedor_id=config["fornecedor_id"],
            tipo_lote_id=tipo_lote.id,
            estrelas=config["estrelas"],
            preco_por_kg=config["preco"],
            ativo=True
        )
        db.session.add(preco)
        precos_criados += 1
    
    db.session.commit()
    print(f"✅ {precos_criados} preços configurados!\n")
    
    # Atualizar valores calculados dos itens existentes
    print("🔄 Atualizando valores dos itens das solicitações...\n")
    
    itens_atualizados = 0
    itens = ItemSolicitacao.query.filter_by(valor_calculado=0).all()
    
    for item in itens:
        if not item.tipo_lote_id or not item.solicitacao:
            continue
        
        preco_config = FornecedorTipoLotePreco.query.filter_by(
            fornecedor_id=item.solicitacao.fornecedor_id,
            tipo_lote_id=item.tipo_lote_id,
            estrelas=item.estrelas_final
        ).first()
        
        if preco_config and preco_config.preco_por_kg:
            item.valor_calculado = item.peso_kg * preco_config.preco_por_kg
            itens_atualizados += 1
            print(f"  ✅ Item #{item.id}: {item.peso_kg}kg × R${preco_config.preco_por_kg}/kg = R${item.valor_calculado:.2f}")
    
    db.session.commit()
    print(f"\n✅ {itens_atualizados} itens atualizados!\n")
    
    # Atualizar valor total das OCs
    print("🔄 Atualizando valores das Ordens de Compra...\n")
    
    ocs = OrdemCompra.query.all()
    for oc in ocs:
        if oc.solicitacao and oc.solicitacao.itens:
            valor_total = sum((item.valor_calculado or 0.0) for item in oc.solicitacao.itens)
            oc.valor_total = valor_total
            print(f"  ✅ OC #{oc.id}: R${valor_total:.2f}")
    
    db.session.commit()
    
    print(f"\n{'='*60}")
    print(f"🎉 Configuração concluída!")
    print(f"{'='*60}")
    print("\n💡 Agora as Ordens de Compra têm valores corretos!")
    print("   Atualize a página para ver as mudanças.")
