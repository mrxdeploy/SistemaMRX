from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timedelta
import requests
import os
import uuid
import json

from app.models import (
    db, Usuario, ConversaBot, Conquista, AporteConquista,
    Fornecedor, Solicitacao, Lote, EntradaEstoque, TipoLote,
    OrdemCompra, ItemSolicitacao
)
from app.routes.metais import fetch_metals_data, METAL_SYMBOLS
from app.auth import admin_required

bp = Blueprint('assistente', __name__, url_prefix='/api/assistente')


def verificar_usuario(usuario_id):
    """Verifica se o usuario existe e esta ativo"""
    usuario = Usuario.query.get(usuario_id)
    if not usuario:
        return None, jsonify({'erro': 'Usuario nao encontrado'}), 404
    if not usuario.ativo:
        return None, jsonify({'erro': 'Usuario inativo'}), 403
    return usuario, None, None

PERPLEXITY_API_KEY = os.getenv('PERPLEXITY_API_KEY')
PERPLEXITY_MODEL = 'llama-3.1-sonar-small-128k-online'

def consultar_perplexity(mensagem, contexto_sistema=None):
    if not PERPLEXITY_API_KEY:
        return None, 'Chave API do Perplexity nao configurada'
    
    try:
        headers = {
            'Authorization': f'Bearer {PERPLEXITY_API_KEY}',
            'Content-Type': 'application/json'
        }
        
        system_content = contexto_sistema or """Voce e um assistente inteligente especializado em mercado de metais, reciclagem de eletronicos e investimentos. 
Responda de forma clara, objetiva e em portugues brasileiro.
Forneca informacoes precisas sobre cotacoes de metais, tendencias de mercado e dicas de investimento.
Quando nao souber algo, admita e sugira onde encontrar a informacao."""
        
        payload = {
            'model': PERPLEXITY_MODEL,
            'messages': [
                {'role': 'system', 'content': system_content},
                {'role': 'user', 'content': mensagem}
            ],
            'max_tokens': 1024,
            'temperature': 0.7,
            'top_p': 0.9,
            'return_images': False,
            'return_related_questions': True,
            'search_recency_filter': 'month',
            'stream': False
        }
        
        response = requests.post(
            'https://api.perplexity.ai/chat/completions',
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            resposta = data['choices'][0]['message']['content']
            citacoes = data.get('citations', [])
            return {
                'resposta': resposta,
                'citacoes': citacoes,
                'modelo': data.get('model', PERPLEXITY_MODEL)
            }, None
        else:
            return None, f'Erro na API Perplexity: {response.status_code}'
    except Exception as e:
        return None, str(e)

def obter_dados_metas(usuario_id):
    conquistas = Conquista.query.filter_by(usuario_id=usuario_id).all()
    
    if not conquistas:
        return None
    
    total_metas = len(conquistas)
    metas_concluidas = len([c for c in conquistas if c.status == 'concluida'])
    total_objetivo = sum(float(c.valor_total or 0) for c in conquistas)
    total_investido = sum(float(c.valor_investido or 0) for c in conquistas)
    progresso_geral = (total_investido / total_objetivo * 100) if total_objetivo > 0 else 0
    
    return {
        'total_metas': total_metas,
        'metas_concluidas': metas_concluidas,
        'metas_em_andamento': total_metas - metas_concluidas,
        'total_objetivo': round(total_objetivo, 2),
        'total_investido': round(total_investido, 2),
        'progresso_geral': round(progresso_geral, 2),
        'conquistas': [c.to_dict() for c in conquistas]
    }

def obter_dados_empresa():
    total_fornecedores = Fornecedor.query.filter_by(ativo=True).count()
    total_solicitacoes = Solicitacao.query.count()
    solicitacoes_pendentes = Solicitacao.query.filter_by(status='pendente').count()
    total_lotes = Lote.query.count()
    total_entradas = EntradaEstoque.query.count()
    
    return {
        'total_fornecedores_ativos': total_fornecedores,
        'total_solicitacoes': total_solicitacoes,
        'solicitacoes_pendentes': solicitacoes_pendentes,
        'total_lotes': total_lotes,
        'total_entradas_estoque': total_entradas
    }

def identificar_intencao(mensagem):
    mensagem_lower = mensagem.lower()
    
    if any(p in mensagem_lower for p in ['cotacao', 'preco', 'valor do', 'quanto custa', 'cotacoes']):
        if any(m in mensagem_lower for m in ['ouro', 'prata', 'cobre', 'platina', 'paladio', 'metal', 'metais']):
            return 'cotacao_metais'
    
    if any(p in mensagem_lower for p in ['meta', 'conquista', 'planejamento', 'investimento', 'objetivo', 'progresso']):
        return 'metas'
    
    if any(p in mensagem_lower for p in ['empresa', 'fornecedor', 'estoque', 'lote', 'solicitacao', 'entrada']):
        return 'dados_empresa'
    
    if any(p in mensagem_lower for p in ['dica', 'recomendacao', 'sugestao', 'conselho', 'melhor momento', 'quando comprar', 'quando vender']):
        return 'recomendacao'
    
    if any(p in mensagem_lower for p in ['relatorio', 'resumo', 'balanco', 'evolucao', 'historico']):
        return 'relatorio'
    
    return 'geral'

def formatar_cotacoes_metais(metals_data):
    if not metals_data or 'metals' not in metals_data:
        return 'Nao foi possivel obter as cotacoes no momento.'
    
    metals = metals_data['metals']
    usd_brl = metals_data.get('usd_brl', 5.0)
    
    linhas = [f"**Cotacoes de Metais** (Atualizado: {metals_data.get('timestamp', 'agora')})\n"]
    linhas.append(f"Taxa USD/BRL: R$ {usd_brl:.2f}\n")
    
    for symbol, data in metals.items():
        nome = data.get('name', symbol)
        preco_usd = data.get('price_usd', 0)
        preco_brl = data.get('price_brl', 0)
        variacao = data.get('variation', 0)
        
        seta = '' if variacao >= 0 else ''
        linhas.append(f"- **{nome}** ({symbol}): ${preco_usd:.2f} USD | R$ {preco_brl:.2f} BRL {seta} {variacao:+.2f}%")
    
    return '\n'.join(linhas)

def processar_mensagem(mensagem, usuario_id, sessao_id):
    intencao = identificar_intencao(mensagem)
    fonte_dados = []
    resposta_partes = []
    dados_adicionais = {'intencao': intencao}
    
    if intencao == 'cotacao_metais' or 'metal' in mensagem.lower() or 'ouro' in mensagem.lower():
        try:
            metals_data = fetch_metals_data()
            cotacoes_formatadas = formatar_cotacoes_metais(metals_data)
            resposta_partes.append(cotacoes_formatadas)
            fonte_dados.append('API de Metais')
            dados_adicionais['cotacoes'] = metals_data
        except Exception as e:
            resposta_partes.append(f'Nao foi possivel obter cotacoes: {str(e)}')
    
    if intencao == 'metas':
        dados_metas = obter_dados_metas(usuario_id)
        if dados_metas:
            resposta_partes.append(f"""**Resumo das suas Metas:**
- Total de metas: {dados_metas['total_metas']}
- Metas concluidas: {dados_metas['metas_concluidas']}
- Em andamento: {dados_metas['metas_em_andamento']}
- Valor total objetivo: R$ {dados_metas['total_objetivo']:,.2f}
- Total investido: R$ {dados_metas['total_investido']:,.2f}
- Progresso geral: {dados_metas['progresso_geral']:.1f}%""")
            fonte_dados.append('Banco de Dados Local')
            dados_adicionais['metas'] = dados_metas
        else:
            resposta_partes.append('Voce ainda nao possui metas cadastradas. Acesse o Planejamento de Conquistas para criar suas primeiras metas!')
    
    if intencao == 'dados_empresa':
        dados = obter_dados_empresa()
        resposta_partes.append(f"""**Dados da Empresa:**
- Fornecedores ativos: {dados['total_fornecedores_ativos']}
- Total de solicitacoes: {dados['total_solicitacoes']}
- Solicitacoes pendentes: {dados['solicitacoes_pendentes']}
- Total de lotes: {dados['total_lotes']}
- Entradas no estoque: {dados['total_entradas_estoque']}""")
        fonte_dados.append('Banco de Dados Local')
        dados_adicionais['empresa'] = dados
    
    if intencao in ['recomendacao', 'geral', 'relatorio'] or not resposta_partes:
        contexto = f"""Voce e um assistente especializado em metais preciosos e reciclagem de eletronicos.
O usuario trabalha com compra e venda de materiais eletronicos para reciclagem.
Forneca insights sobre mercado de metais, melhores praticas de investimento e analises."""
        
        resultado_perplexity, erro = consultar_perplexity(mensagem, contexto)
        
        if resultado_perplexity:
            resposta_partes.append(resultado_perplexity['resposta'])
            if resultado_perplexity.get('citacoes'):
                resposta_partes.append('\n**Fontes:**')
                for citacao in resultado_perplexity['citacoes'][:3]:
                    resposta_partes.append(f'- {citacao}')
            fonte_dados.append('IA Perplexity')
            dados_adicionais['perplexity'] = {'citacoes': resultado_perplexity.get('citacoes', [])}
        elif not resposta_partes:
            resposta_partes.append('Desculpe, nao consegui processar sua solicitacao no momento. Tente novamente ou reformule sua pergunta.')
    
    resposta_final = '\n\n'.join(resposta_partes)
    fontes_str = ', '.join(fonte_dados) if fonte_dados else 'Sistema'
    
    try:
        conversa = ConversaBot(
            usuario_id=usuario_id,
            sessao_id=sessao_id,
            mensagem_usuario=mensagem,
            resposta_bot=resposta_final,
            tipo_consulta=intencao,
            fonte_dados=fontes_str,
            dados_adicionais=dados_adicionais
        )
        db.session.add(conversa)
        db.session.commit()
    except Exception as e:
        print(f'Erro ao salvar conversa: {e}')
    
    return {
        'resposta': resposta_final,
        'tipo_consulta': intencao,
        'fonte_dados': fontes_str,
        'timestamp': datetime.now().isoformat()
    }


def obter_contexto_sistema_completo():
    """Obtem dados completos do sistema para dar contexto a IA"""
    try:
        total_fornecedores = Fornecedor.query.filter_by(ativo=True).count()
        total_solicitacoes = Solicitacao.query.count()
        solicitacoes_pendentes = Solicitacao.query.filter_by(status='pendente').count()
        solicitacoes_aprovadas = Solicitacao.query.filter_by(status='aprovado').count()
        total_lotes = Lote.query.count()
        total_entradas = EntradaEstoque.query.count()
        
        tipos_lote = TipoLote.query.filter_by(ativo=True).all()
        tipos_lote_nomes = [t.nome for t in tipos_lote]
        
        fornecedores_recentes = Fornecedor.query.filter_by(ativo=True).order_by(
            Fornecedor.data_cadastro.desc()
        ).limit(5).all()
        fornecedores_info = [f"{f.nome} ({f.cidade or 'sem cidade'})" for f in fornecedores_recentes]
        
        try:
            total_ocs = OrdemCompra.query.count()
            ocs_abertas = OrdemCompra.query.filter(OrdemCompra.status.in_(['pendente', 'em_transito'])).count()
        except:
            total_ocs = 0
            ocs_abertas = 0
        
        contexto = f"""Voce e o assistente inteligente do sistema MRX Systems - um sistema ERP completo para gestao de compra e venda de materiais eletronicos para reciclagem de metais preciosos.

DADOS ATUAIS DO SISTEMA (em tempo real):
- Fornecedores ativos: {total_fornecedores}
- Fornecedores recentes: {', '.join(fornecedores_info) if fornecedores_info else 'Nenhum'}
- Total de solicitacoes: {total_solicitacoes}
- Solicitacoes pendentes: {solicitacoes_pendentes}
- Solicitacoes aprovadas: {solicitacoes_aprovadas}
- Lotes registrados: {total_lotes}
- Entradas no estoque: {total_entradas}
- Ordens de compra: {total_ocs} (abertas: {ocs_abertas})
- Tipos de lote disponiveis: {', '.join(tipos_lote_nomes) if tipos_lote_nomes else 'Nenhum cadastrado'}

MODULOS DO SISTEMA QUE VOCE CONHECE:
1. Fornecedores - Cadastro e gestao de fornecedores de material eletronico
2. Solicitacoes - Pedidos de compra de materiais
3. Lotes - Classificacao de materiais por tipo (leve, medio, pesado)
4. Estoque - Controle de entradas e saidas
5. Ordens de Compra - Gestao de OCs para fornecedores
6. Dashboard - Metricas e indicadores do negocio
7. Conferencias - Verificacao de materiais recebidos
8. Logistica - Controle de veiculos e motoristas
9. Metais - Cotacoes de metais preciosos (ouro, prata, cobre, etc)
10. Financeiro - Controle de pagamentos

COMO VOCE DEVE RESPONDER:
- Sempre em portugues brasileiro
- De forma clara, objetiva e profissional
- Ofereca insights baseados nos dados do sistema
- Ajude o usuario a entender melhor o negocio
- Forneca recomendacoes quando apropriado
- Se nao souber algo especifico, admita e sugira onde encontrar"""
        
        return contexto
    except Exception as e:
        print(f'Erro ao obter contexto: {e}')
        return """Voce e o assistente inteligente do sistema MRX Systems para gestao de compra e venda de materiais eletronicos.
Responda em portugues brasileiro de forma clara e objetiva."""


@bp.route('/chat', methods=['POST'])
@jwt_required()
def chat():
    try:
        usuario_id = get_jwt_identity()
        usuario, erro_response, status_code = verificar_usuario(usuario_id)
        
        if erro_response:
            return erro_response, status_code
        
        data = request.get_json()
        
        if not data or 'mensagem' not in data:
            return jsonify({'erro': 'Mensagem nao fornecida'}), 400
        
        mensagem = data['mensagem'].strip()
        if not mensagem:
            return jsonify({'erro': 'Mensagem vazia'}), 400
        
        sessao_id = data.get('sessao_id')
        if not sessao_id or not sessao_id.strip():
            sessao_id = str(uuid.uuid4())
        
        resultado = processar_mensagem_inteligente(mensagem, int(usuario_id), sessao_id)
        resultado['sessao_id'] = sessao_id
        
        return jsonify(resultado)
    except Exception as e:
        print(f'Erro no chat: {e}')
        return jsonify({'erro': str(e)}), 500


def processar_mensagem_inteligente(mensagem, usuario_id, sessao_id):
    """Processa mensagem com contexto completo do sistema e executa ações"""
    from app.services.ai_actions import detectar_intencao_acao, executar_acao, obter_contexto_completo_ia
    
    intencao = identificar_intencao(mensagem)
    fonte_dados = []
    resposta_partes = []
    dados_adicionais = {'intencao': intencao}
    acao_executada = False
    
    intencao_acao = detectar_intencao_acao(mensagem)
    if intencao_acao:
        resultado_acao, resposta_acao = executar_acao(intencao_acao, mensagem, usuario_id)
        if resposta_acao:
            resposta_partes.append(resposta_acao)
            fonte_dados.append('Ação do Sistema')
            dados_adicionais['acao'] = intencao_acao
            dados_adicionais['resultado_acao'] = resultado_acao
            acao_executada = True
    
    if intencao == 'cotacao_metais' or 'metal' in mensagem.lower() or 'ouro' in mensagem.lower():
        try:
            metals_data = fetch_metals_data()
            cotacoes_formatadas = formatar_cotacoes_metais(metals_data)
            resposta_partes.append(cotacoes_formatadas)
            fonte_dados.append('API de Metais')
            dados_adicionais['cotacoes'] = metals_data
        except Exception as e:
            resposta_partes.append(f'Nao foi possivel obter cotacoes: {str(e)}')
    
    if intencao == 'metas':
        dados_metas = obter_dados_metas(usuario_id)
        if dados_metas:
            resposta_partes.append(f"""**Resumo das suas Metas:**
- Total de metas: {dados_metas['total_metas']}
- Metas concluidas: {dados_metas['metas_concluidas']}
- Em andamento: {dados_metas['metas_em_andamento']}
- Valor total objetivo: R$ {dados_metas['total_objetivo']:,.2f}
- Total investido: R$ {dados_metas['total_investido']:,.2f}
- Progresso geral: {dados_metas['progresso_geral']:.1f}%""")
            fonte_dados.append('Banco de Dados')
            dados_adicionais['metas'] = dados_metas
        else:
            resposta_partes.append('Voce ainda nao possui metas cadastradas.')
    
    if intencao == 'dados_empresa' and not acao_executada:
        dados = obter_dados_empresa()
        resposta_partes.append(f"""**Dados da Empresa:**
- Fornecedores ativos: {dados['total_fornecedores_ativos']}
- Total de solicitacoes: {dados['total_solicitacoes']}
- Solicitacoes pendentes: {dados['solicitacoes_pendentes']}
- Total de lotes: {dados['total_lotes']}
- Entradas no estoque: {dados['total_entradas_estoque']}""")
        fonte_dados.append('Banco de Dados')
        dados_adicionais['empresa'] = dados
    
    if not acao_executada or intencao in ['recomendacao', 'geral']:
        contexto_completo = obter_contexto_completo_ia()
        resultado_perplexity, erro = consultar_perplexity(mensagem, contexto_completo)
        
        if resultado_perplexity:
            if resposta_partes:
                resposta_partes.append("\n**Análise da IA:**")
            resposta_partes.append(resultado_perplexity['resposta'])
            if resultado_perplexity.get('citacoes'):
                resposta_partes.append('\n**Fontes:**')
                for citacao in resultado_perplexity['citacoes'][:3]:
                    resposta_partes.append(f'- {citacao}')
            fonte_dados.append('IA Perplexity')
            dados_adicionais['perplexity'] = {'citacoes': resultado_perplexity.get('citacoes', [])}
    
    if not resposta_partes:
        resposta_partes.append('Desculpe, nao consegui processar sua solicitacao. Tente reformular sua pergunta.')
    
    resposta_final = '\n\n'.join(resposta_partes)
    fontes_str = ', '.join(fonte_dados) if fonte_dados else 'Sistema'
    
    try:
        conversa = ConversaBot(
            usuario_id=usuario_id,
            sessao_id=sessao_id,
            mensagem_usuario=mensagem,
            resposta_bot=resposta_final,
            tipo_consulta=intencao_acao or intencao,
            fonte_dados=fontes_str,
            dados_adicionais=dados_adicionais
        )
        db.session.add(conversa)
        db.session.commit()
    except Exception as e:
        print(f'Erro ao salvar conversa: {e}')
    
    return {
        'resposta': resposta_final,
        'tipo_consulta': intencao_acao or intencao,
        'fonte_dados': fontes_str,
        'acao_executada': acao_executada,
        'timestamp': datetime.now().isoformat()
    }


@bp.route('/historico', methods=['GET'])
@jwt_required()
def historico():
    try:
        usuario_id = get_jwt_identity()
        usuario, erro_response, status_code = verificar_usuario(usuario_id)
        
        if erro_response:
            return erro_response, status_code
        
        sessao_id = request.args.get('sessao_id')
        limite = request.args.get('limite', 50, type=int)
        
        query = ConversaBot.query.filter_by(usuario_id=int(usuario_id))
        
        if sessao_id:
            query = query.filter_by(sessao_id=sessao_id)
        
        conversas = query.order_by(ConversaBot.data_criacao.desc()).limit(limite).all()
        
        return jsonify([c.to_dict() for c in conversas])
    except Exception as e:
        return jsonify({'erro': str(e)}), 500


@bp.route('/sessoes', methods=['GET'])
@jwt_required()
def listar_sessoes():
    try:
        usuario_id = get_jwt_identity()
        usuario, erro_response, status_code = verificar_usuario(usuario_id)
        
        if erro_response:
            return erro_response, status_code
        
        sessoes = db.session.query(
            ConversaBot.sessao_id,
            db.func.min(ConversaBot.data_criacao).label('inicio'),
            db.func.max(ConversaBot.data_criacao).label('fim'),
            db.func.count(ConversaBot.id).label('mensagens')
        ).filter_by(
            usuario_id=int(usuario_id)
        ).group_by(
            ConversaBot.sessao_id
        ).order_by(
            db.desc('fim')
        ).limit(20).all()
        
        return jsonify([{
            'sessao_id': s.sessao_id,
            'inicio': s.inicio.isoformat() if s.inicio else None,
            'fim': s.fim.isoformat() if s.fim else None,
            'mensagens': s.mensagens
        } for s in sessoes])
    except Exception as e:
        return jsonify({'erro': str(e)}), 500


@bp.route('/sugestoes', methods=['GET'])
@jwt_required()
def sugestoes():
    usuario_id = get_jwt_identity()
    usuario, erro_response, status_code = verificar_usuario(usuario_id)
    
    if erro_response:
        return erro_response, status_code
    sugestoes_lista = [
        {'texto': 'Cotacao do ouro hoje', 'icone': 'fa-coins', 'categoria': 'metais'},
        {'texto': 'Precos dos metais preciosos', 'icone': 'fa-chart-line', 'categoria': 'metais'},
        {'texto': 'Qual melhor momento para comprar ouro?', 'icone': 'fa-lightbulb', 'categoria': 'dica'},
        {'texto': 'Resumo das minhas metas', 'icone': 'fa-trophy', 'categoria': 'metas'},
        {'texto': 'Progresso dos investimentos', 'icone': 'fa-chart-pie', 'categoria': 'metas'},
        {'texto': 'Dados da empresa', 'icone': 'fa-building', 'categoria': 'empresa'},
        {'texto': 'Dica de investimento em metais', 'icone': 'fa-gem', 'categoria': 'dica'},
        {'texto': 'Tendencia do mercado de cobre', 'icone': 'fa-arrow-trend-up', 'categoria': 'metais'}
    ]
    
    return jsonify(sugestoes_lista)


@bp.route('/exportar/<sessao_id>', methods=['GET'])
@jwt_required()
def exportar_conversa(sessao_id):
    from flask import Response
    try:
        usuario_id = get_jwt_identity()
        usuario, erro_response, status_code = verificar_usuario(usuario_id)
        
        if erro_response:
            return erro_response, status_code
        
        conversas = ConversaBot.query.filter_by(
            usuario_id=int(usuario_id),
            sessao_id=sessao_id
        ).order_by(ConversaBot.data_criacao.asc()).all()
        
        if not conversas:
            return jsonify({'erro': 'Conversa nao encontrada'}), 404
        
        formato = request.args.get('formato', 'txt')
        
        if formato == 'json':
            return jsonify([c.to_dict() for c in conversas])
        else:
            linhas = [f"Conversa exportada em {datetime.now().strftime('%d/%m/%Y %H:%M')}\n"]
            linhas.append(f"Sessao: {sessao_id}\n")
            linhas.append("=" * 50 + "\n\n")
            
            for c in conversas:
                linhas.append(f"[{c.data_criacao.strftime('%d/%m %H:%M')}] Voce:\n{c.mensagem_usuario}\n\n")
                linhas.append(f"[{c.data_criacao.strftime('%d/%m %H:%M')}] Assistente ({c.fonte_dados}):\n{c.resposta_bot}\n\n")
                linhas.append("-" * 30 + "\n\n")
            
            return Response(
                '\n'.join(linhas),
                mimetype='text/plain',
                headers={'Content-Disposition': f'attachment; filename=conversa_{sessao_id[:8]}.txt'}
            )
    except Exception as e:
        return jsonify({'erro': str(e)}), 500
