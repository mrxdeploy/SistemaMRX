from app.models import db, Notificacao, Usuario, Fornecedor, OrdemCompra
from datetime import datetime, timedelta

def obter_admins():
    return Usuario.query.filter(
        Usuario.tipo == 'admin',
        Usuario.ativo == True
    ).all()

def criar_notificacao_admin(titulo, mensagem, tipo, url):
    admins = obter_admins()
    notificacoes_criadas = []
    
    for admin in admins:
        notificacoes_existentes = Notificacao.query.filter(
            Notificacao.usuario_id == admin.id,
            Notificacao.tipo == tipo
        ).all()
        
        if notificacoes_existentes:
            notificacao_principal = notificacoes_existentes[0]
            notificacao_principal.titulo = titulo
            notificacao_principal.mensagem = mensagem
            notificacao_principal.url = url
            notificacao_principal.lida = False
            notificacao_principal.data_envio = datetime.utcnow()
            
            for duplicada in notificacoes_existentes[1:]:
                db.session.delete(duplicada)
        else:
            notificacao = Notificacao(
                usuario_id=admin.id,
                titulo=titulo,
                mensagem=mensagem,
                tipo=tipo,
                url=url
            )
            db.session.add(notificacao)
            notificacoes_criadas.append(notificacao)
    
    db.session.commit()
    
    return notificacoes_criadas

def remover_notificacao_por_tipo(tipo):
    Notificacao.query.filter(
        Notificacao.tipo == tipo
    ).delete()
    db.session.commit()

def verificar_fornecedores_pendentes():
    fornecedores_pendentes = Fornecedor.query.filter(
        Fornecedor.tabela_preco_status == 'pendente',
        Fornecedor.ativo == True
    ).all()
    
    tipo = 'fornecedor_tabela_pendente'
    notificacoes = []
    
    if len(fornecedores_pendentes) > 0:
        titulo = f"Tabelas de Preço Pendentes"
        mensagem = f"Existem {len(fornecedores_pendentes)} fornecedor(es) com tabela de preços aguardando aprovação."
        url = "/revisao-tabelas-admin.html"
        
        notificacoes.extend(criar_notificacao_admin(titulo, mensagem, tipo, url))
    else:
        remover_notificacao_por_tipo(tipo)
    
    return {
        'total_pendentes': len(fornecedores_pendentes),
        'notificacoes_criadas': len(notificacoes),
        'fornecedores': [{'id': f.id, 'nome': f.nome} for f in fornecedores_pendentes]
    }

def verificar_ordens_compra_pendentes():
    ocs_pendentes = OrdemCompra.query.filter(
        OrdemCompra.status == 'em_analise'
    ).all()
    
    tipo = 'ordem_compra_pendente'
    notificacoes = []
    
    if len(ocs_pendentes) > 0:
        valor_total = sum(oc.valor_total for oc in ocs_pendentes)
        titulo = f"Ordens de Compra Pendentes"
        mensagem = f"Existem {len(ocs_pendentes)} OC(s) aguardando aprovação. Valor total: R$ {valor_total:.2f}"
        url = "/solicitacoes.html?tab=ordens-compra&status=em_analise"
        
        notificacoes.extend(criar_notificacao_admin(titulo, mensagem, tipo, url))
    else:
        remover_notificacao_por_tipo(tipo)
    
    return {
        'total_pendentes': len(ocs_pendentes),
        'notificacoes_criadas': len(notificacoes),
        'ordens': [{'id': oc.id, 'fornecedor': oc.fornecedor.nome if oc.fornecedor else None, 'valor': float(oc.valor_total)} for oc in ocs_pendentes]
    }

def verificar_solicitacoes_pendentes():
    from app.models import Solicitacao
    
    solicitacoes_pendentes = Solicitacao.query.filter(
        Solicitacao.status == 'pendente'
    ).all()
    
    tipo = 'solicitacao_pendente'
    notificacoes = []
    
    if len(solicitacoes_pendentes) > 0:
        titulo = f"Pedidos de Compra Pendentes"
        mensagem = f"Existem {len(solicitacoes_pendentes)} pedido(s) de compra aguardando análise."
        url = "/solicitacoes.html?status=pendente"
        
        notificacoes.extend(criar_notificacao_admin(titulo, mensagem, tipo, url))
    else:
        remover_notificacao_por_tipo(tipo)
    
    return {
        'total_pendentes': len(solicitacoes_pendentes),
        'notificacoes_criadas': len(notificacoes),
        'solicitacoes': [{'id': s.id, 'fornecedor': s.fornecedor.nome if s.fornecedor else None} for s in solicitacoes_pendentes]
    }

def verificar_conferencias_pendentes():
    from app.models import Conferencia
    
    tipo = 'conferencia_pendente'
    
    try:
        conferencias_pendentes = Conferencia.query.filter(
            Conferencia.status.in_(['pendente', 'em_andamento'])
        ).all()
        
        notificacoes = []
        if len(conferencias_pendentes) > 0:
            titulo = f"Conferências Pendentes"
            mensagem = f"Existem {len(conferencias_pendentes)} conferência(s) aguardando processamento."
            url = "/conferencias.html"
            
            notificacoes.extend(criar_notificacao_admin(titulo, mensagem, tipo, url))
        else:
            remover_notificacao_por_tipo(tipo)
        
        return {
            'total_pendentes': len(conferencias_pendentes),
            'notificacoes_criadas': len(notificacoes)
        }
    except Exception as e:
        return {'total_pendentes': 0, 'notificacoes_criadas': 0, 'erro': str(e)}

def verificar_autorizacoes_preco_pendentes():
    from app.models import SolicitacaoAutorizacaoPreco
    
    tipo = 'autorizacao_preco_pendente'
    
    try:
        autorizacoes_pendentes = SolicitacaoAutorizacaoPreco.query.filter(
            SolicitacaoAutorizacaoPreco.status == 'pendente'
        ).all()
        
        notificacoes = []
        if len(autorizacoes_pendentes) > 0:
            titulo = f"Autorizações de Preço Pendentes"
            mensagem = f"Existem {len(autorizacoes_pendentes)} autorização(ões) de preço aguardando aprovação."
            url = "/autorizacoes-preco.html"
            
            notificacoes.extend(criar_notificacao_admin(titulo, mensagem, tipo, url))
        else:
            remover_notificacao_por_tipo(tipo)
        
        return {
            'total_pendentes': len(autorizacoes_pendentes),
            'notificacoes_criadas': len(notificacoes)
        }
    except Exception as e:
        return {'total_pendentes': 0, 'notificacoes_criadas': 0, 'erro': str(e)}

def gerar_todas_notificacoes_pendentes():
    resultados = {
        'fornecedores': verificar_fornecedores_pendentes(),
        'ordens_compra': verificar_ordens_compra_pendentes(),
        'solicitacoes': verificar_solicitacoes_pendentes(),
        'autorizacoes_preco': verificar_autorizacoes_preco_pendentes(),
        'conferencias': verificar_conferencias_pendentes()
    }
    
    total_pendentes = sum([
        resultados['fornecedores'].get('total_pendentes', 0),
        resultados['ordens_compra'].get('total_pendentes', 0),
        resultados['solicitacoes'].get('total_pendentes', 0),
        resultados['autorizacoes_preco'].get('total_pendentes', 0),
        resultados['conferencias'].get('total_pendentes', 0)
    ])
    
    total_notificacoes = sum([
        resultados['fornecedores'].get('notificacoes_criadas', 0),
        resultados['ordens_compra'].get('notificacoes_criadas', 0),
        resultados['solicitacoes'].get('notificacoes_criadas', 0),
        resultados['autorizacoes_preco'].get('notificacoes_criadas', 0),
        resultados['conferencias'].get('notificacoes_criadas', 0)
    ])
    
    return {
        'total_pendentes': total_pendentes,
        'total_notificacoes_criadas': total_notificacoes,
        'detalhes': resultados
    }

def obter_resumo_pendencias():
    fornecedores_pendentes = Fornecedor.query.filter(
        Fornecedor.tabela_preco_status == 'pendente',
        Fornecedor.ativo == True
    ).count()
    
    ocs_pendentes = OrdemCompra.query.filter(
        OrdemCompra.status == 'em_analise'
    ).count()
    
    from app.models import Solicitacao
    solicitacoes_pendentes = Solicitacao.query.filter(
        Solicitacao.status == 'pendente'
    ).count()
    
    try:
        from app.models import SolicitacaoAutorizacaoPreco
        autorizacoes_pendentes = SolicitacaoAutorizacaoPreco.query.filter(
            SolicitacaoAutorizacaoPreco.status == 'pendente'
        ).count()
    except:
        autorizacoes_pendentes = 0
    
    return {
        'fornecedores_tabela_pendente': fornecedores_pendentes,
        'ordens_compra_pendentes': ocs_pendentes,
        'solicitacoes_pendentes': solicitacoes_pendentes,
        'autorizacoes_preco_pendentes': autorizacoes_pendentes,
        'total': fornecedores_pendentes + ocs_pendentes + solicitacoes_pendentes + autorizacoes_pendentes
    }
