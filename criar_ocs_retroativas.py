"""Script para criar OCs retroativamente para solicitações já aprovadas"""
from app import create_app
from app.models import db, Solicitacao, OrdemCompra, AuditoriaOC
from datetime import datetime

app = create_app()

with app.app_context():
    print("🔧 Criando OCs retroativamente para solicitações aprovadas...\n")
    
    # Buscar solicitações aprovadas sem OC
    solicitacoes_aprovadas = Solicitacao.query.filter_by(status='aprovada').all()
    
    ocs_criadas = 0
    for solicitacao in solicitacoes_aprovadas:
        # Verificar se já tem OC
        oc_existente = OrdemCompra.query.filter_by(solicitacao_id=solicitacao.id).first()
        
        if oc_existente:
            print(f"  ℹ️  Solicitação #{solicitacao.id} já tem OC #{oc_existente.id}")
            continue
        
        # Calcular valor total
        if not solicitacao.itens or len(solicitacao.itens) == 0:
            print(f"  ⚠️  Solicitação #{solicitacao.id} não possui itens, pulando...")
            continue
        
        valor_total = sum((item.valor_calculado or 0.0) for item in solicitacao.itens)
        
        # Criar OC
        oc = OrdemCompra(
            solicitacao_id=solicitacao.id,
            fornecedor_id=solicitacao.fornecedor_id,
            valor_total=valor_total,
            status='em_analise',
            criado_por=solicitacao.admin_id,
            observacao=f'OC criada retroativamente para solicitação #{solicitacao.id} aprovada anteriormente'
        )
        db.session.add(oc)
        db.session.flush()
        
        # Registrar auditoria
        auditoria = AuditoriaOC(
            oc_id=oc.id,
            usuario_id=solicitacao.admin_id,
            acao='criacao',
            status_anterior=None,
            status_novo='em_analise',
            observacao=f'OC criada retroativamente para solicitação #{solicitacao.id}',
            ip='127.0.0.1',
            gps=None,
            dispositivo='Script Retroativo'
        )
        db.session.add(auditoria)
        
        ocs_criadas += 1
        print(f"  ✅ OC #{oc.id} criada para Solicitação #{solicitacao.id} - Fornecedor: {solicitacao.fornecedor.nome} - Valor: R$ {valor_total:.2f}")
    
    db.session.commit()
    
    print(f"\n{'='*60}")
    print(f"🎉 {ocs_criadas} Ordens de Compra criadas retroativamente!")
    print(f"{'='*60}")
    
    # Resumo
    total_ocs = OrdemCompra.query.count()
    print(f"\n📊 Total de OCs no sistema: {total_ocs}")
    
    print("\n💡 Agora você pode:")
    print("   1. Visualizar as OCs na interface")
    print("   2. Aprovar a Solicitação #1 (pendente) para testar a criação automática")
