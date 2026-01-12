from app import create_app
from app.models import db, Fornecedor, TipoLote, Solicitacao, ItemSolicitacao, Usuario, TipoLotePreco, FornecedorTipoLote
from datetime import datetime, timedelta

app = create_app()

with app.app_context():
    print("🔧 Criando dados de teste...")
    
    # Criar Tipos de Lote
    tipos_lote = [
        {"nome": "Alumínio", "descricao": "Alumínio e suas ligas", "codigo": "ALU"},
        {"nome": "Cobre", "descricao": "Cobre e suas ligas", "codigo": "COB"},
        {"nome": "Aço", "descricao": "Aço carbono e inoxidável", "codigo": "ACO"},
        {"nome": "Plástico PET", "descricao": "Polietileno tereftalato", "codigo": "PET"},
        {"nome": "Plástico PEAD", "descricao": "Polietileno alta densidade", "codigo": "PEAD"},
        {"nome": "Papel/Papelão", "descricao": "Papel branco e papelão", "codigo": "PAP"},
        {"nome": "Vidro", "descricao": "Vidro transparente e colorido", "codigo": "VID"},
    ]
    
    print("\n📦 Criando Tipos de Lote...")
    tipos_lote_criados = {}
    for tl_data in tipos_lote:
        existing = TipoLote.query.filter_by(nome=tl_data["nome"]).first()
        if not existing:
            tipo_lote = TipoLote(
                nome=tl_data["nome"],
                descricao=tl_data["descricao"],
                codigo=tl_data["codigo"],
                ativo=True
            )
            db.session.add(tipo_lote)
            db.session.flush()
            tipos_lote_criados[tl_data["nome"]] = tipo_lote
            print(f"  ✅ {tl_data['nome']}")
        else:
            tipos_lote_criados[tl_data["nome"]] = existing
            print(f"  ℹ️  {tl_data['nome']} (já existe)")
    
    db.session.commit()
    
    # Criar Fornecedores
    fornecedores_data = [
        {
            "nome": "Metais Silva LTDA",
            "nome_social": "Metais Silva Comércio e Reciclagem LTDA",
            "cnpj": "12.345.678/0001-90",
            "email": "contato@metaissilva.com.br",
            "telefone": "(11) 98765-4321",
            "tipos": ["Alumínio", "Cobre", "Aço"]
        },
        {
            "nome": "Recicla Plásticos",
            "nome_social": "Recicla Plásticos Indústria e Comércio LTDA",
            "cnpj": "98.765.432/0001-10",
            "email": "vendas@reciclaplasticos.com.br",
            "telefone": "(11) 91234-5678",
            "tipos": ["Plástico PET", "Plástico PEAD"]
        },
        {
            "nome": "Papel & Vidro Reciclagem",
            "nome_social": "Papel e Vidro Reciclagem e Comércio S/A",
            "cnpj": "11.222.333/0001-44",
            "email": "comercial@papelevidro.com.br",
            "telefone": "(11) 99876-5432",
            "tipos": ["Papel/Papelão", "Vidro"]
        },
    ]
    
    print("\n🏭 Criando Fornecedores...")
    fornecedores_criados = []
    for f_data in fornecedores_data:
        existing = Fornecedor.query.filter_by(cnpj=f_data["cnpj"]).first()
        if not existing:
            fornecedor = Fornecedor(
                nome=f_data["nome"],
                nome_social=f_data["nome_social"],
                cnpj=f_data["cnpj"],
                email=f_data["email"],
                telefone=f_data["telefone"],
                ativo=True
            )
            db.session.add(fornecedor)
            db.session.flush()
            
            # Associar tipos de lote ao fornecedor
            for tipo_nome in f_data["tipos"]:
                if tipo_nome in tipos_lote_criados:
                    tipo_lote = tipos_lote_criados[tipo_nome]
                    assoc = FornecedorTipoLote(
                        fornecedor_id=fornecedor.id,
                        tipo_lote_id=tipo_lote.id,
                        ativo=True
                    )
                    db.session.add(assoc)
            
            fornecedores_criados.append(fornecedor)
            print(f"  ✅ {f_data['nome']} - {', '.join(f_data['tipos'])}")
        else:
            fornecedores_criados.append(existing)
            print(f"  ℹ️  {f_data['nome']} (já existe)")
    
    db.session.commit()
    
    # Criar Solicitações de exemplo
    print("\n📋 Criando Solicitações de Teste...")
    comprador = Usuario.query.filter_by(email="comprador@teste.com").first()
    
    if comprador and len(fornecedores_criados) > 0:
        solicitacoes_data = [
            {
                "fornecedor": 0,  # Metais Silva
                "observacoes": "Solicitação de alumínio para produção mensal",
                "itens": [
                    {"tipo": "Alumínio", "peso_kg": 500, "estrelas": 4},
                    {"tipo": "Cobre", "peso_kg": 200, "estrelas": 3},
                ]
            },
            {
                "fornecedor": 1,  # Recicla Plásticos
                "observacoes": "Solicitação de plásticos recicláveis",
                "itens": [
                    {"tipo": "Plástico PET", "peso_kg": 1000, "estrelas": 5},
                    {"tipo": "Plástico PEAD", "peso_kg": 500, "estrelas": 4},
                ]
            },
            {
                "fornecedor": 2,  # Papel & Vidro
                "observacoes": "Compra de materiais diversos",
                "itens": [
                    {"tipo": "Papel/Papelão", "peso_kg": 800, "estrelas": 3},
                    {"tipo": "Vidro", "peso_kg": 400, "estrelas": 4},
                ]
            },
        ]
        
        for idx, sol_data in enumerate(solicitacoes_data, 1):
            if sol_data["fornecedor"] < len(fornecedores_criados):
                fornecedor = fornecedores_criados[sol_data["fornecedor"]]
                solicitacao = Solicitacao(
                    funcionario_id=comprador.id,
                    fornecedor_id=fornecedor.id,
                    observacoes=sol_data["observacoes"],
                    status="pendente",
                    tipo_retirada="buscar"
                )
                db.session.add(solicitacao)
                db.session.flush()
                
                for item_data in sol_data["itens"]:
                    tipo_lote = tipos_lote_criados.get(item_data["tipo"])
                    if tipo_lote:
                        item = ItemSolicitacao(
                            solicitacao_id=solicitacao.id,
                            tipo_lote_id=tipo_lote.id,
                            peso_kg=item_data["peso_kg"],
                            estrelas_final=item_data["estrelas"]
                        )
                        db.session.add(item)
                
                print(f"  ✅ Solicitação #{idx}: {sol_data['observacoes']}")
        
        db.session.commit()
        print(f"\n✅ {len(solicitacoes_data)} solicitações criadas!")
    else:
        print("  ⚠️  Usuário comprador ou fornecedores não encontrados. Pulando criação de solicitações.")
    
    # Resumo
    print("\n" + "="*60)
    print("🎉 DADOS DE TESTE CRIADOS COM SUCESSO!")
    print("="*60)
    print(f"📦 Tipos de Lote: {TipoLote.query.count()}")
    print(f"🏭 Fornecedores: {Fornecedor.query.count()}")
    print(f"📋 Solicitações: {Solicitacao.query.count()}")
    print(f"📝 Itens de Solicitação: {ItemSolicitacao.query.count()}")
    print(f"👤 Usuários: {Usuario.query.count()}")
    print("="*60)
    print("\n💡 Use as credenciais dos usuários de teste para acessar o sistema!")
    print("   Exemplo: comprador@teste.com / teste123")
