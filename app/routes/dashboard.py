from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required
from app.models import db, Fornecedor, Solicitacao, Lote, EntradaEstoque, FornecedorTipoLotePreco, ItemSolicitacao, TipoLote, OrdemCompra, Usuario, Motorista, OrdemServico
from app.auth import admin_ou_auditor_required
from sqlalchemy import func, extract, case, and_, or_
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import requests

bp = Blueprint('dashboard', __name__, url_prefix='/api/dashboard')

@bp.route('/stats', methods=['GET'])
@admin_ou_auditor_required
def obter_estatisticas():
    """Retorna estatísticas gerais do sistema"""
    # Estatísticas de Solicitações/Relatórios
    total_pendentes = Solicitacao.query.filter_by(status='pendente').count()
    total_aprovados = Solicitacao.query.filter_by(status='aprovada').count()
    total_reprovados = Solicitacao.query.filter_by(status='rejeitada').count()
    
    # Valor total de lotes aprovados
    valor_total = db.session.query(func.sum(Lote.valor_total)).filter(
        Lote.status == 'aprovado'
    ).scalar() or 0
    
    from app.models import BagProducao, ClassificacaoGrade, ItemSeparadoProducao
    
    LOTES_ATIVOS_STATUS = ['em_estoque', 'disponivel', 'aprovado', 'em_producao', 'CRIADO_SEPARACAO', 'PROCESSADO', 'criado_separacao', 'processado', 'AGUARDANDO_SEPARACAO', 'EM_SEPARACAO']
    BAGS_ATIVOS_STATUS = ['devolvido_estoque', 'cheio', 'aberto', 'enviado_refinaria']

    def obter_peso_e_qtd_por_classificacao(lote_classif, bag_conditions):
        peso_lotes = db.session.query(func.sum(func.coalesce(Lote.peso_liquido, Lote.peso_total_kg))).join(
            TipoLote, Lote.tipo_lote_id == TipoLote.id
        ).filter(
            TipoLote.classificacao == lote_classif,
            Lote.status.in_(LOTES_ATIVOS_STATUS),
            Lote.bloqueado == False,
            Lote.lote_pai_id.is_(None)
        ).scalar() or 0
        
        qtd_lotes = db.session.query(func.count(Lote.id)).join(
            TipoLote, Lote.tipo_lote_id == TipoLote.id
        ).filter(
            TipoLote.classificacao == lote_classif,
            Lote.status.in_(LOTES_ATIVOS_STATUS),
            Lote.bloqueado == False,
            Lote.lote_pai_id.is_(None),
            func.coalesce(Lote.peso_liquido, Lote.peso_total_kg) > 0
        ).scalar() or 0

        peso_bags = db.session.query(func.sum(ItemSeparadoProducao.peso_kg)).join(
            ClassificacaoGrade, ItemSeparadoProducao.classificacao_grade_id == ClassificacaoGrade.id
        ).join(
            BagProducao, ItemSeparadoProducao.bag_id == BagProducao.id
        ).filter(
            bag_conditions,
            BagProducao.status.in_(BAGS_ATIVOS_STATUS)
        ).scalar() or 0
        
        qtd_bags = db.session.query(func.count(ItemSeparadoProducao.id)).join(
            ClassificacaoGrade, ItemSeparadoProducao.classificacao_grade_id == ClassificacaoGrade.id
        ).join(
            BagProducao, ItemSeparadoProducao.bag_id == BagProducao.id
        ).filter(
            bag_conditions,
            BagProducao.status.in_(BAGS_ATIVOS_STATUS)
        ).scalar() or 0
        
        return float(peso_lotes) + float(peso_bags), qtd_lotes + qtd_bags

    quilos_low, qtd_low = obter_peso_e_qtd_por_classificacao(
        'low', func.lower(ClassificacaoGrade.categoria).like('%low%')
    )
    
    quilos_mg1, qtd_mg1 = obter_peso_e_qtd_por_classificacao(
        'mg1', 
        (func.lower(ClassificacaoGrade.categoria) == 'mg1') | 
        (func.lower(ClassificacaoGrade.categoria).like('%mid_grade_1%')) |
        (func.lower(ClassificacaoGrade.categoria).like('%mid_grade%'))
    )
    
    quilos_mg2, qtd_mg2 = obter_peso_e_qtd_por_classificacao(
        'mg2',
        (func.lower(ClassificacaoGrade.categoria) == 'mg2') | 
        (func.lower(ClassificacaoGrade.categoria).like('%mid_grade_2%'))
    )

    quilos_high, qtd_high = obter_peso_e_qtd_por_classificacao(
        'high', func.lower(ClassificacaoGrade.categoria).like('%high%')
    )
    
    # Ranking de fornecedores (top 10)
    ranking = db.session.query(
        Fornecedor.id,
        Fornecedor.nome,
        func.count(Solicitacao.id).label('total')
    ).join(
        Solicitacao, Solicitacao.fornecedor_id == Fornecedor.id
    ).filter(
        Solicitacao.status == 'aprovada'
    ).group_by(
        Fornecedor.id, Fornecedor.nome
    ).order_by(
        func.count(Solicitacao.id).desc()
    ).limit(10).all()
    
    ranking_empresas = [
        {
            'id': r.id,
            'nome': r.nome,
            'total': r.total
        } for r in ranking
    ]
    
    return jsonify({
        'relatorios': {
            'pendentes': total_pendentes,
            'aprovados': total_aprovados,
            'reprovados': total_reprovados
        },
        'estoque_ativo_qtd': {
            'low': qtd_low,
            'mg1': qtd_mg1,
            'mg2': qtd_mg2,
            'high': qtd_high
        },
        'valor_total': float(valor_total),
        'quilos_por_tipo': {
            'low': float(quilos_low),
            'mg1': float(quilos_mg1),
            'mg2': float(quilos_mg2),
            'high': float(quilos_high)
        },
        'ranking_empresas': ranking_empresas
    }), 200

@bp.route('/grafico-mensal', methods=['GET'])
@admin_ou_auditor_required
def obter_grafico_mensal():
    """Retorna dados de movimentação mensal para gráficos"""
    from dateutil.relativedelta import relativedelta
    
    # Últimos 6 meses
    hoje = datetime.now()
    meses = []
    dados = []
    
    # Nome do mês em português
    nomes_meses = ['', 'Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 
                  'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
    
    for i in range(5, -1, -1):
        # Calcular o mês corretamente usando relativedelta
        mes_data = hoje - relativedelta(months=i)
        mes_num = mes_data.month
        ano = mes_data.year
        
        meses.append(nomes_meses[mes_num])
        
        # Calcular início e fim do mês para filtro correto
        inicio_mes = datetime(ano, mes_num, 1)
        if mes_num == 12:
            fim_mes = datetime(ano + 1, 1, 1)
        else:
            fim_mes = datetime(ano, mes_num + 1, 1)
        
        # Contar solicitações aprovadas no mês usando range de datas
        count = Solicitacao.query.filter(
            Solicitacao.data_envio >= inicio_mes,
            Solicitacao.data_envio < fim_mes,
            Solicitacao.status == 'aprovada'
        ).count()
        
        dados.append(count)
    
    return jsonify({
        'labels': meses,
        'data': dados
    }), 200

@bp.route('/financeiro', methods=['GET'])
@admin_ou_auditor_required
def obter_metricas_financeiras():
    """Retorna métricas financeiras dos compradores"""
    hoje = datetime.now()
    mes_atual = datetime(hoje.year, hoje.month, 1)
    mes_anterior = mes_atual - relativedelta(months=1)
    inicio_semana = hoje - timedelta(days=hoje.weekday())
    
    compradores = Usuario.query.filter(
        Usuario.tipo.in_(['admin', 'funcionario']),
        Usuario.ativo == True
    ).all()
    
    gastos_por_comprador = []
    for comprador in compradores:
        valor_mes = db.session.query(func.sum(Lote.valor_total)).join(
            Fornecedor, Lote.fornecedor_id == Fornecedor.id
        ).filter(
            Fornecedor.comprador_responsavel_id == comprador.id,
            Lote.data_criacao >= mes_atual,
            Lote.status == 'aprovado'
        ).scalar() or 0
        
        valor_semana = db.session.query(func.sum(Lote.valor_total)).join(
            Fornecedor, Lote.fornecedor_id == Fornecedor.id
        ).filter(
            Fornecedor.comprador_responsavel_id == comprador.id,
            Lote.data_criacao >= inicio_semana,
            Lote.status == 'aprovado'
        ).scalar() or 0
        
        qtd_compras = db.session.query(func.count(Lote.id)).join(
            Fornecedor, Lote.fornecedor_id == Fornecedor.id
        ).filter(
            Fornecedor.comprador_responsavel_id == comprador.id,
            Lote.data_criacao >= mes_atual,
            Lote.status == 'aprovado'
        ).scalar() or 0
        
        ticket_medio = (float(valor_mes) / qtd_compras) if qtd_compras > 0 else 0
        
        gastos_por_comprador.append({
            'nome': comprador.nome,
            'valor_mes': float(valor_mes),
            'valor_semana': float(valor_semana),
            'qtd_compras': qtd_compras,
            'ticket_medio': ticket_medio
        })
    
    gastos_mensais_ultimos_6_meses = []
    nomes_meses = ['', 'Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 
                  'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
    
    for i in range(5, -1, -1):
        mes_data = hoje - relativedelta(months=i)
        mes_num = mes_data.month
        ano = mes_data.year
        
        inicio_mes = datetime(ano, mes_num, 1)
        if mes_num == 12:
            fim_mes = datetime(ano + 1, 1, 1)
        else:
            fim_mes = datetime(ano, mes_num + 1, 1)
        
        valor_total = db.session.query(func.sum(Lote.valor_total)).filter(
            Lote.data_criacao >= inicio_mes,
            Lote.data_criacao < fim_mes,
            Lote.status == 'aprovado'
        ).scalar() or 0
        
        gastos_mensais_ultimos_6_meses.append({
            'mes': nomes_meses[mes_num],
            'valor': float(valor_total)
        })
    
    total_gasto_mes = sum([c['valor_mes'] for c in gastos_por_comprador])
    total_compras_mes = sum([c['qtd_compras'] for c in gastos_por_comprador])
    ticket_medio_geral = (total_gasto_mes / total_compras_mes) if total_compras_mes > 0 else 0
    
    return jsonify({
        'gastos_por_comprador': gastos_por_comprador,
        'gastos_mensais': gastos_mensais_ultimos_6_meses,
        'total_gasto_mes': float(total_gasto_mes),
        'total_compras_mes': total_compras_mes,
        'ticket_medio_geral': ticket_medio_geral
    }), 200

@bp.route('/logistica', methods=['GET'])
@admin_ou_auditor_required
def obter_metricas_logistica():
    """Retorna métricas de logística"""
    hoje = datetime.now()
    mes_atual = datetime(hoje.year, hoje.month, 1)
    
    motoristas = Motorista.query.filter(Motorista.ativo == True).all()
    
    metricas_motoristas = []
    for motorista in motoristas:
        total_os = OrdemServico.query.filter(
            OrdemServico.motorista_id == motorista.id,
            OrdemServico.criado_em >= mes_atual
        ).count()
        
        os_concluidas = OrdemServico.query.filter(
            OrdemServico.motorista_id == motorista.id,
            OrdemServico.status == 'FINALIZADA',
            OrdemServico.criado_em >= mes_atual
        ).count()
        
        km_total = 0  # OrdemServico não possui campo km_total
        
        tempo_medio_minutos = 0  # OrdemServico não possui campos data_conclusao e data_inicio
        
        taxa_conclusao = (os_concluidas / total_os * 100) if total_os > 0 else 0
        
        metricas_motoristas.append({
            'nome': motorista.nome,
            'total_os': total_os,
            'os_concluidas': os_concluidas,
            'km_total': float(km_total),
            'tempo_medio_horas': float(tempo_medio_minutos) / 60,
            'taxa_conclusao': round(taxa_conclusao, 2)
        })
    
    total_km_mes = sum([m['km_total'] for m in metricas_motoristas])
    total_os_mes = sum([m['total_os'] for m in metricas_motoristas])
    media_km_por_os = (total_km_mes / total_os_mes) if total_os_mes > 0 else 0
    
    return jsonify({
        'metricas_motoristas': metricas_motoristas,
        'total_km_mes': float(total_km_mes),
        'total_os_mes': total_os_mes,
        'media_km_por_os': float(media_km_por_os)
    }), 200

@bp.route('/analise-fornecedores', methods=['GET'])
@admin_ou_auditor_required
def obter_analise_fornecedores():
    """Retorna análise detalhada de fornecedores"""
    hoje = datetime.now()
    mes_atual = datetime(hoje.year, hoje.month, 1)
    
    fornecedores_ativos = Fornecedor.query.filter(Fornecedor.ativo == True).all()
    
    analise_fornecedores = []
    for fornecedor in fornecedores_ativos:
        total_solicitacoes = Solicitacao.query.filter(
            Solicitacao.fornecedor_id == fornecedor.id,
            Solicitacao.data_envio >= mes_atual
        ).count()
        
        solicitacoes_aprovadas = Solicitacao.query.filter(
            Solicitacao.fornecedor_id == fornecedor.id,
            Solicitacao.status == 'aprovada',
            Solicitacao.data_envio >= mes_atual
        ).count()
        
        tempo_medio_aprovacao = db.session.query(
            func.avg(
                func.extract('epoch', Solicitacao.data_confirmacao - Solicitacao.data_envio) / 3600
            )
        ).filter(
            Solicitacao.fornecedor_id == fornecedor.id,
            Solicitacao.status == 'aprovada',
            Solicitacao.data_confirmacao.isnot(None),
            Solicitacao.data_envio >= mes_atual
        ).scalar() or 0
        
        peso_total = db.session.query(func.sum(Lote.peso_total_kg)).filter(
            Lote.fornecedor_id == fornecedor.id,
            Lote.status == 'aprovado',
            Lote.data_criacao >= mes_atual
        ).scalar() or 0
        
        valor_total = db.session.query(func.sum(Lote.valor_total)).filter(
            Lote.fornecedor_id == fornecedor.id,
            Lote.status == 'aprovado',
            Lote.data_criacao >= mes_atual
        ).scalar() or 0
        
        taxa_aprovacao = (solicitacoes_aprovadas / total_solicitacoes * 100) if total_solicitacoes > 0 else 0
        
        preco_medio_kg = (float(valor_total) / float(peso_total)) if float(peso_total) > 0 else 0
        
        analise_fornecedores.append({
            'nome': fornecedor.nome,
            'total_solicitacoes': total_solicitacoes,
            'solicitacoes_aprovadas': solicitacoes_aprovadas,
            'taxa_aprovacao': round(taxa_aprovacao, 2),
            'tempo_medio_aprovacao_horas': round(float(tempo_medio_aprovacao), 2),
            'peso_total_kg': float(peso_total),
            'valor_total': float(valor_total),
            'preco_medio_kg': round(preco_medio_kg, 2)
        })
    
    analise_fornecedores_ordenado = sorted(analise_fornecedores, key=lambda x: x['valor_total'], reverse=True)[:10]
    
    return jsonify({
        'top_fornecedores': analise_fornecedores_ordenado,
        'total_fornecedores': len(fornecedores_ativos)
    }), 200

@bp.route('/operacional', methods=['GET'])
@admin_ou_auditor_required
def obter_metricas_operacionais():
    """Retorna métricas de eficiência operacional"""
    hoje = datetime.now()
    mes_atual = datetime(hoje.year, hoje.month, 1)
    
    total_solicitacoes = Solicitacao.query.filter(
        Solicitacao.data_envio >= mes_atual
    ).count()
    
    solicitacoes_aprovadas = Solicitacao.query.filter(
        Solicitacao.data_envio >= mes_atual,
        Solicitacao.status == 'aprovada'
    ).count()
    
    solicitacoes_rejeitadas = Solicitacao.query.filter(
        Solicitacao.data_envio >= mes_atual,
        Solicitacao.status == 'rejeitada'
    ).count()
    
    solicitacoes_pendentes = Solicitacao.query.filter(
        Solicitacao.status == 'pendente'
    ).count()
    
    taxa_aprovacao = (solicitacoes_aprovadas / total_solicitacoes * 100) if total_solicitacoes > 0 else 0
    
    tempo_medio_aprovacao = db.session.query(
        func.avg(
            func.extract('epoch', Solicitacao.data_confirmacao - Solicitacao.data_envio) / 3600
        )
    ).filter(
        Solicitacao.status == 'aprovada',
        Solicitacao.data_confirmacao.isnot(None),
        Solicitacao.data_envio >= mes_atual
    ).scalar() or 0
    
    tempo_medio_ciclo_completo = db.session.query(
        func.avg(
            func.extract('epoch', EntradaEstoque.data_entrada - Solicitacao.data_envio) / (3600 * 24)
        )
    ).join(
        Lote, EntradaEstoque.lote_id == Lote.id
    ).join(
        Solicitacao, Lote.fornecedor_id == Solicitacao.fornecedor_id
    ).filter(
        Solicitacao.data_envio >= mes_atual,
        EntradaEstoque.data_entrada.isnot(None)
    ).scalar() or 0
    
    nomes_meses = ['', 'Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 
                  'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
    
    solicitacoes_por_mes = []
    for i in range(5, -1, -1):
        mes_data = hoje - relativedelta(months=i)
        mes_num = mes_data.month
        ano = mes_data.year
        
        inicio_mes = datetime(ano, mes_num, 1)
        if mes_num == 12:
            fim_mes = datetime(ano + 1, 1, 1)
        else:
            fim_mes = datetime(ano, mes_num + 1, 1)
        
        total_mes = Solicitacao.query.filter(
            Solicitacao.data_envio >= inicio_mes,
            Solicitacao.data_envio < fim_mes
        ).count()
        
        aprovadas_mes = Solicitacao.query.filter(
            Solicitacao.data_envio >= inicio_mes,
            Solicitacao.data_envio < fim_mes,
            Solicitacao.status == 'aprovada'
        ).count()
        
        solicitacoes_por_mes.append({
            'mes': nomes_meses[mes_num],
            'total': total_mes,
            'aprovadas': aprovadas_mes
        })
    
    return jsonify({
        'total_solicitacoes_mes': total_solicitacoes,
        'solicitacoes_aprovadas': solicitacoes_aprovadas,
        'solicitacoes_rejeitadas': solicitacoes_rejeitadas,
        'solicitacoes_pendentes': solicitacoes_pendentes,
        'taxa_aprovacao': round(taxa_aprovacao, 2),
        'tempo_medio_aprovacao_horas': round(float(tempo_medio_aprovacao), 2),
        'tempo_medio_ciclo_dias': round(float(tempo_medio_ciclo_completo), 2),
        'solicitacoes_por_mes': solicitacoes_por_mes
    }), 200

# Cache simples para cotações (evitar múltiplas requisições)
_cotacoes_cache = {
    'timestamp': None,
    'dados': None
}
CACHE_DURACAO_MINUTOS = 30

@bp.route('/indicadores-externos', methods=['GET'])
@admin_ou_auditor_required
def obter_indicadores_externos():
    """Retorna indicadores externos como cotação do dólar"""
    global _cotacoes_cache
    
    # Verificar se temos cache válido
    agora = datetime.now()
    if _cotacoes_cache['timestamp'] and _cotacoes_cache['dados']:
        tempo_decorrido = (agora - _cotacoes_cache['timestamp']).total_seconds() / 60
        if tempo_decorrido < CACHE_DURACAO_MINUTOS:
            print(f'✅ Usando cotações em cache ({tempo_decorrido:.1f} min atrás)')
            return jsonify(_cotacoes_cache['dados']), 200
    
    try:
        # Lista de APIs para tentar (fallback)
        apis = [
            {
                'url': 'https://economia.awesomeapi.com.br/last/USD-BRL,EUR-BRL',
                'parser': lambda data: {
                    'dolar': {
                        'valor': float(data['USDBRL']['bid']),
                        'variacao': float(data['USDBRL']['pctChange']),
                        'data_atualizacao': data['USDBRL']['create_date']
                    },
                    'euro': {
                        'valor': float(data['EURBRL']['bid']),
                        'variacao': float(data['EURBRL']['pctChange']),
                        'data_atualizacao': data['EURBRL']['create_date']
                    }
                }
            },
            {
                'url': 'https://api.exchangerate-api.com/v4/latest/USD',
                'parser': lambda data: {
                    'dolar': {
                        'valor': float(data['rates']['BRL']),
                        'variacao': 0,
                        'data_atualizacao': data.get('date', 'N/A')
                    },
                    'euro': {
                        'valor': float(data['rates']['BRL']) / float(data['rates']['EUR']),
                        'variacao': 0,
                        'data_atualizacao': data.get('date', 'N/A')
                    }
                }
            }
        ]
        
        cotacoes = None
        for api in apis:
            try:
                print(f'🔄 Tentando API: {api["url"]}')
                response = requests.get(
                    api['url'], 
                    timeout=5,
                    headers={'User-Agent': 'Mozilla/5.0'}
                )
                
                if response.status_code == 200:
                    dados = response.json()
                    cotacoes = api['parser'](dados)
                    print(f'✅ Cotações obtidas - Dólar: R$ {cotacoes["dolar"]["valor"]:.2f}')
                    break
                else:
                    print(f'⚠️ API retornou status {response.status_code}')
                    
            except Exception as e:
                print(f'⚠️ Erro ao tentar API: {e}')
                continue
        
        if not cotacoes:
            raise Exception('Todas as APIs falharam')
        
        # Buscar histórico
        historico_dolar = []
        hoje = datetime.now()
        
        try:
            resp_historico = requests.get(
                'https://economia.awesomeapi.com.br/json/daily/USD-BRL/30',
                timeout=5,
                headers={'User-Agent': 'Mozilla/5.0'}
            )
            
            if resp_historico.status_code == 200:
                dados_historico = resp_historico.json()
                if dados_historico and len(dados_historico) > 0:
                    for item in reversed(dados_historico[-30:]):
                        timestamp = int(item['timestamp'])
                        data_cotacao = datetime.fromtimestamp(timestamp)
                        historico_dolar.append({
                            'data': data_cotacao.strftime('%d/%m'),
                            'valor': float(item['bid'])
                        })
                    print(f'✅ Histórico obtido: {len(historico_dolar)} registros')
        except Exception as e_hist:
            print(f'⚠️ Erro ao buscar histórico: {e_hist}')
        
        # Se não conseguiu histórico, simular com cotação atual
        if len(historico_dolar) == 0:
            print('⚠️ Criando histórico simulado com cotação atual')
            import random
            for i in range(29, -1, -1):
                data = hoje - timedelta(days=i)
                # Simular variação mais realista
                variacao = random.uniform(-0.015, 0.015)  # ±1.5%
                valor_simulado = cotacoes['dolar']['valor'] * (1 + variacao)
                historico_dolar.append({
                    'data': data.strftime('%d/%m'),
                    'valor': valor_simulado
                })
        
        resultado = {
            'dolar': cotacoes['dolar'],
            'euro': cotacoes['euro'],
            'historico_dolar': historico_dolar[-30:]
        }
        
        # Salvar no cache
        _cotacoes_cache = {
            'timestamp': agora,
            'dados': resultado
        }
        
        return jsonify(resultado), 200
        
    except Exception as e:
        print(f'❌ Erro ao buscar indicadores externos: {e}')
        
        # Se temos cache antigo, retornar mesmo que expirado
        if _cotacoes_cache['dados']:
            print('⚠️ Retornando cotações em cache (expirado)')
            return jsonify(_cotacoes_cache['dados']), 200
        
        # Último recurso: valores fixos conhecidos (aprox.)
        return jsonify({
            'dolar': {'valor': 5.75, 'variacao': 0, 'data_atualizacao': 'Estimado'},
            'euro': {'valor': 6.20, 'variacao': 0, 'data_atualizacao': 'Estimado'},
            'historico_dolar': [
                {'data': (datetime.now() - timedelta(days=i)).strftime('%d/%m'), 'valor': 5.75 + (i % 3 - 1) * 0.05}
                for i in range(29, -1, -1)
            ],
            'erro': 'API temporariamente indisponível - usando valores estimados'
        }), 200
