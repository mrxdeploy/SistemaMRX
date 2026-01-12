"""Script para criar OCs para solicitações #1 e #4 que foram aprovadas antes da correção"""
from app import create_app
from app.models import db, Solicitacao, OrdemCompra, AuditoriaOC

app = create_app()

with app.app_context():
    print("🔧 Criando OCs para solicitações aprovadas sem OC...\n")
    
    solicitacoes_ids = [1, 4]
    ocs_criadas = 0
    
    for sol_id in solicitacoes_ids:
        solicitacao = Solicitacao.query.get(sol_id)
        
        if not solicitacao:
            print(f"  ⚠️  Solicitação #{sol_id} não encontrada")
            continue
        
        if solicitacao.status != 'aprovada':
            print(f"  ⚠️  Solicitação #{sol_id} não está aprovada")
            continue
        
        # Verificar se já tem OC
        oc_existente = OrdemCompra.query.filter_by(solicitacao_id=sol_id).first()
        if oc_existente:
            print(f"  ℹ️  Solicitação #{sol_id} já tem OC #{oc_existente.id}")
            continue
        
        # Calcular valor total (tratando None como 0)
        valor_total = sum((item.valor_calculado or 0.0) for item in solicitacao.itens)
        
        print(f"  📋 Solicitação #{sol_id}:")
        print(f"     Fornecedor: {solicitacao.fornecedor.nome}")
        print(f"     Itens: {len(solicitacao.itens)}")
        print(f"     Valor: R$ {valor_total:.2f}")
        
        # Criar OC
        oc = OrdemCompra(
            solicitacao_id=sol_id,
            fornecedor_id=solicitacao.fornecedor_id,
            valor_total=valor_total,
            status='em_analise',
            criado_por=solicitacao.admin_id,
            observacao=f'OC criada retroativamente (solicitação aprovada antes da correção do bug)'
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
            observacao=f'OC criada retroativamente para solicitação #{sol_id}',
            ip='127.0.0.1',
            gps=None,
            dispositivo='Script Retroativo'
        )
        db.session.add(auditoria)
        
        ocs_criadas += 1
        print(f"     ✅ OC #{oc.id} criada!\n")
    
    db.session.commit()
    
    print(f"{'='*60}")
    print(f"🎉 {ocs_criadas} Ordens de Compra criadas!")
    print(f"{'='*60}\n")
    
    # Resumo final
    total_ocs = OrdemCompra.query.count()
    total_solicitacoes_aprovadas = Solicitacao.query.filter_by(status='aprovada').count()
    
    print(f"📊 Resumo do sistema:")
    print(f"   • Total de Solicitações Aprovadas: {total_solicitacoes_aprovadas}")
    print(f"   • Total de Ordens de Compra: {total_ocs}")
    print(f"\n💡 Agora TODAS as solicitações aprovadas têm suas OCs!")
    print(f"   E as novas aprovações criarão OCs automaticamente.")
