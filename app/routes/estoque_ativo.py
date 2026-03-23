from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import db, Lote, BagProducao, ItemSeparadoProducao, ClassificacaoGrade, ItemSolicitacao, MaterialBase, Usuario, Fornecedor, Solicitacao, OrdemCompra
from sqlalchemy.orm import joinedload, selectinload
from sqlalchemy import func
from datetime import datetime, timedelta
import uuid
import logging

logger = logging.getLogger(__name__)

bp = Blueprint('estoque_ativo', __name__, url_prefix='/api/estoque-ativo')

# Status de lotes ativos (incluindo sublotes criados na separação)
LOTES_ATIVOS_STATUS = ['em_estoque', 'disponivel', 'aprovado', 'em_producao', 'CRIADO_SEPARACAO', 'PROCESSADO', 'criado_separacao', 'processado', 'AGUARDANDO_SEPARACAO', 'EM_SEPARACAO']


def _calcular_preco_kg_sublote(sublote):
    """Calcula o preço por kg de um sublote seguindo a cadeia de prioridades:
    1. Observações do sublote (PRECO_KG:)
    2. valor_total / peso do sublote
    3. valor_total / peso do lote pai
    4. Pedido de Compra aprovado (OrdemCompra) → ItemSolicitacao.preco_por_kg_snapshot
       por tipo_lote_id específico do material
    5. Fallback: todos os itens da OC (média geral)
    """
    if not sublote:
        return 0
    
    peso_atual = float(sublote.peso_liquido or sublote.peso_total_kg or 0)
    
    # Prioridade 1: PRECO_KG nas observações
    if sublote.observacoes:
        for parte in sublote.observacoes.split('|'):
            if parte.strip().startswith('PRECO_KG:'):
                try:
                    preco = float(parte.replace('PRECO_KG:', '').strip())
                    if preco > 0:
                        return preco
                except:
                    pass
    
    # Prioridade 2: valor_total do sublote / peso
    val_sublote = float(sublote.valor_total or 0)
    if val_sublote > 0 and peso_atual > 0:
        return val_sublote / peso_atual
    
    # Prioridade 3: valor_total do lote pai / peso do pai  
    lote_pai = sublote.lote_pai if sublote.lote_pai_id else None
    if lote_pai:
        pai_val = float(lote_pai.valor_total or 0)
        pai_peso = float(lote_pai.peso_liquido or lote_pai.peso_total_kg or 0)
        if pai_val > 0 and pai_peso > 0:
            return pai_val / pai_peso
    
    # Prioridade 4: Buscar no Pedido de Compra Aprovado (OrdemCompra → ItemSolicitacao)
    # Encontrar a solicitação de origem (OC) do lote
    solicitacao_id = None
    if lote_pai and lote_pai.solicitacao_origem_id:
        solicitacao_id = lote_pai.solicitacao_origem_id
    elif sublote.solicitacao_origem_id:
        solicitacao_id = sublote.solicitacao_origem_id
    
    if solicitacao_id:
        # Verificar se existe um Pedido de Compra aprovado para esta Solicitação
        oc_aprovada = OrdemCompra.query.filter_by(
            solicitacao_id=solicitacao_id
        ).filter(
            OrdemCompra.status.in_(['aprovada', 'aprovada_adm', 'concluido', 'APROVADA', 'APROVADA_ADM', 'concluida', 'em_conferencia', 'conferida', 'conferido'])
        ).first()
        
        # Se não encontrou com status aprovado, pegar qualquer OC desta solicitação
        if not oc_aprovada:
            oc_aprovada = OrdemCompra.query.filter_by(
                solicitacao_id=solicitacao_id
            ).first()
        
        if oc_aprovada:
            # Buscar itens da solicitação vinculada ao pedido de compra aprovado
            tipo_lote_id = sublote.tipo_lote_id
            
            # Prioridade 4a: Buscar item específico por tipo_lote_id
            if tipo_lote_id:
                itens_especificos = ItemSolicitacao.query.filter_by(
                    solicitacao_id=solicitacao_id,
                    tipo_lote_id=tipo_lote_id
                ).all()
                if itens_especificos:
                    # Usar preco_por_kg_snapshot (preço aprovado no pedido de compra)
                    for item in itens_especificos:
                        preco_snap = float(item.preco_por_kg_snapshot or 0)
                        if preco_snap > 0:
                            return preco_snap
                    # Fallback: calcular do valor_calculado
                    total_val = sum(float(i.valor_calculado or 0) for i in itens_especificos)
                    total_peso = sum(float(i.peso_kg or 0) for i in itens_especificos)
                    if total_peso > 0 and total_val > 0:
                        return total_val / total_peso
            
            # Prioridade 4b: Tentar buscar por material_id via nome do material
            nome_material = None
            if sublote.observacoes:
                for parte in sublote.observacoes.split('|'):
                    p = parte.strip()
                    if p.startswith('MATERIAL:') or p.startswith('MATERIAL_MANUAL:'):
                        nome_material = p.replace('MATERIAL_MANUAL:', '').replace('MATERIAL:', '').strip()
                        break
            elif sublote.tipo_lote:
                nome_material = sublote.tipo_lote.nome
            
            if nome_material:
                # Buscar material base pelo nome
                material_base = MaterialBase.query.filter(
                    func.lower(MaterialBase.nome) == func.lower(nome_material)
                ).first()
                if material_base:
                    item_especifico = ItemSolicitacao.query.filter_by(
                        solicitacao_id=solicitacao_id,
                        material_id=material_base.id
                    ).first()
                    if item_especifico:
                        preco_snap = float(item_especifico.preco_por_kg_snapshot or 0)
                        if preco_snap > 0:
                            return preco_snap
                        val_calc = float(item_especifico.valor_calculado or 0)
                        peso_item = float(item_especifico.peso_kg or 0)
                        if val_calc > 0 and peso_item > 0:
                            return val_calc / peso_item
            
            # Prioridade 5: Média geral de todos os itens do pedido de compra
            itens_todos = ItemSolicitacao.query.filter_by(
                solicitacao_id=solicitacao_id
            ).all()
            if itens_todos:
                # Tentar usar preco_por_kg_snapshot primeiro
                precos_snap = [float(i.preco_por_kg_snapshot or 0) for i in itens_todos if float(i.preco_por_kg_snapshot or 0) > 0]
                if precos_snap:
                    # Média ponderada por peso
                    total_val = sum(float(i.preco_por_kg_snapshot or 0) * float(i.peso_kg or 0) for i in itens_todos if float(i.preco_por_kg_snapshot or 0) > 0)
                    total_peso = sum(float(i.peso_kg or 0) for i in itens_todos if float(i.preco_por_kg_snapshot or 0) > 0)
                    if total_peso > 0:
                        return total_val / total_peso
                
                # Fallback: valor_calculado
                total_val = sum(float(i.valor_calculado or 0) for i in itens_todos)
                total_peso = sum(float(i.peso_kg or 0) for i in itens_todos)
                if total_peso > 0 and total_val > 0:
                    return total_val / total_peso
    
    return 0

@bp.route('/dashboard', methods=['GET'])
@jwt_required()
def dashboard_estoque_ativo():
    try:
        # Contar APENAS lotes PRINCIPAIS ativos (sem lote_pai_id)
        lotes_ativos = Lote.query.filter(
            Lote.status.in_(LOTES_ATIVOS_STATUS),
            Lote.bloqueado == False,
            Lote.lote_pai_id.is_(None)
        ).count()

        # Contar lotes principais em produção
        em_producao = Lote.query.filter(
            Lote.status == 'em_producao',
            Lote.bloqueado == False,
            Lote.lote_pai_id.is_(None)
        ).count()

        bags_estoque = BagProducao.query.filter(
            BagProducao.status.in_(['devolvido_estoque', 'cheio', 'aberto'])
        ).count()

        # Somar peso de TODOS os lotes ativos (principais e sublotes)
        peso_total_lotes = db.session.query(
            db.func.sum(db.func.coalesce(Lote.peso_liquido, Lote.peso_total_kg))
        ).filter(
            Lote.status.in_(LOTES_ATIVOS_STATUS),
            Lote.bloqueado == False
        ).scalar() or 0

        peso_total_bags = db.session.query(
            db.func.sum(BagProducao.peso_acumulado)
        ).filter(
            BagProducao.status.in_(['devolvido_estoque', 'cheio'])
        ).scalar() or 0

        return jsonify({
            'lotes_ativos': lotes_ativos,
            'em_producao': em_producao,
            'bags_estoque': bags_estoque,
            'peso_total': float(peso_total_lotes) + float(peso_total_bags)
        })
    except Exception as e:
        logger.error(f'Erro ao carregar dashboard estoque ativo: {str(e)}')
        return jsonify({'erro': str(e)}), 500


@bp.route('/lotes', methods=['GET'])
@jwt_required()
def listar_lotes_ativos():
    try:
        status = request.args.get('status')
        
        # Carregar apenas LOTES PRINCIPAIS (sem lote_pai_id)
        # Os sublotes serão carregados através do relacionamento
        query = Lote.query.options(
            joinedload(Lote.tipo_lote),
            joinedload(Lote.fornecedor),
            selectinload(Lote.sublotes).options(
                joinedload(Lote.tipo_lote),
                joinedload(Lote.fornecedor)
            )
        ).filter(
            Lote.bloqueado == False,
            Lote.lote_pai_id.is_(None)  # Apenas lotes principais
        )

        if status:
            query = query.filter(Lote.status == status)
        else:
            query = query.filter(Lote.status.in_(LOTES_ATIVOS_STATUS))

        lotes = query.order_by(Lote.data_criacao.desc()).limit(200).all()

        logger.info(f'📦 Encontrados {len(lotes)} lotes principais ativos')

        resultado = []
        for lote in lotes:
            lote_dict = lote.to_dict()
            
            # Carregar sublotes com informações completas
            sublotes_data = []
            peso_total_sublotes = 0
            
            if lote.sublotes:
                logger.info(f'   Lote {lote.numero_lote} tem {len(lote.sublotes)} sublotes')
                for sublote in lote.sublotes:
                    # Usar peso_liquido se disponível, senão peso_total_kg
                    peso_sublote = float(sublote.peso_liquido) if sublote.peso_liquido else float(sublote.peso_total_kg) if sublote.peso_total_kg else 0
                    
                    sublote_dict = {
                        'id': sublote.id,
                        'numero_lote': sublote.numero_lote,
                        'tipo_lote_id': sublote.tipo_lote_id,
                        'tipo_lote_nome': sublote.tipo_lote.nome if sublote.tipo_lote else 'N/A',
                        'peso_total_kg': float(sublote.peso_total_kg) if sublote.peso_total_kg else 0,
                        'peso_liquido': float(sublote.peso_liquido) if sublote.peso_liquido else 0,
                        'status': sublote.status,
                        'qualidade_recebida': sublote.qualidade_recebida,
                        'localizacao_atual': sublote.localizacao_atual,
                        'observacoes': sublote.observacoes,
                        'data_criacao': sublote.data_criacao.isoformat() if sublote.data_criacao else None
                    }
                    sublotes_data.append(sublote_dict)
                    peso_total_sublotes += peso_sublote
            
            lote_dict['sublotes'] = sublotes_data
            lote_dict['total_sublotes'] = len(sublotes_data)
            lote_dict['peso_total_sublotes'] = round(peso_total_sublotes, 2)
            
            logger.info(f'   → {lote.numero_lote}: {len(sublotes_data)} sublotes, {peso_total_sublotes:.2f} kg separados')
            
            resultado.append(lote_dict)

        logger.info(f'✅ Retornando {len(resultado)} lotes com sublotes')
        return jsonify(resultado)
        
    except Exception as e:
        logger.error(f'❌ Erro ao listar lotes ativos: {str(e)}')
        import traceback
        traceback.print_exc()
        return jsonify({'erro': str(e)}), 500


@bp.route('/bags', methods=['GET'])
@jwt_required()
def listar_bags_estoque():
    try:
        status = request.args.get('status')
        categoria = request.args.get('categoria')
        
        query = BagProducao.query.options(
            joinedload(BagProducao.classificacao_grade),
            joinedload(BagProducao.criado_por)
        )

        if status:
            query = query.filter(BagProducao.status == status)
        else:
            query = query.filter(BagProducao.status.in_(['devolvido_estoque', 'cheio', 'aberto', 'enviado_refinaria']))

        if categoria:
            # O frontend pode enviar 'HIGH_GRADE', 'MG1', etc. e o banco pode ter 'high', 'mid_grade_1', etc.
            cat_lower = categoria.lower()
            if cat_lower in ['high_grade', 'high']:
                query = query.join(ClassificacaoGrade).filter(func.lower(ClassificacaoGrade.categoria).like('%high%'))
            elif cat_lower in ['mg1', 'mid_grade', 'mid_grade_1']:
                query = query.join(ClassificacaoGrade).filter(
                    (func.lower(ClassificacaoGrade.categoria) == 'mg1') | 
                    (func.lower(ClassificacaoGrade.categoria).like('%mid_grade_1%')) |
                    (func.lower(ClassificacaoGrade.categoria).like('%mid_grade%'))
                )
            elif cat_lower in ['mg2', 'mid_grade_2']:
                query = query.join(ClassificacaoGrade).filter(
                    (func.lower(ClassificacaoGrade.categoria) == 'mg2') | 
                    (func.lower(ClassificacaoGrade.categoria).like('%mid_grade_2%'))
                )
            elif cat_lower in ['low_grade', 'low']:
                query = query.join(ClassificacaoGrade).filter(func.lower(ClassificacaoGrade.categoria).like('%low%'))
            else:
                query = query.join(ClassificacaoGrade).filter(func.lower(ClassificacaoGrade.categoria) == cat_lower)

        bags = query.order_by(BagProducao.data_criacao.desc()).limit(200).all()

        resultado = []
        for bag in bags:
            bag_dict = bag.to_dict()
            
            itens = ItemSeparadoProducao.query.filter_by(bag_id=bag.id).all()
            itens_data = []
            tem_lotes_origem = False
            
            # Agregar itens por classificação
            itens_por_classificacao = {}
            for item in itens:
                item_dict = item.to_dict()
                itens_data.append(item_dict)
                if item.ordem_producao_id:
                    tem_lotes_origem = True
                
                # Agregar por classificação
                classif_nome = item.classificacao_grade.nome if item.classificacao_grade else 'Sem classificação'
                if classif_nome not in itens_por_classificacao:
                    itens_por_classificacao[classif_nome] = {
                        'nome': classif_nome,
                        'peso_total_kg': 0,
                        'quantidade_itens': 0
                    }
                itens_por_classificacao[classif_nome]['peso_total_kg'] += float(item.peso_kg or 0)
                itens_por_classificacao[classif_nome]['quantidade_itens'] += 1
            
            bag_dict['itens'] = itens_data
            bag_dict['origem_lotes'] = tem_lotes_origem
            bag_dict['itens_por_classificacao'] = sorted(
                itens_por_classificacao.values(),
                key=lambda x: x['peso_total_kg'],
                reverse=True
            )
            
            # Determinar categoria exibição baseada nos itens
            categorias_presentes = set()
            for item in itens:
                if item.classificacao_grade and item.classificacao_grade.categoria:
                    categorias_presentes.add(item.classificacao_grade.categoria)
                else:
                    categorias_presentes.add('OUTROS')

            categoria_nomes_map = {
                'high_grade': 'High',
                'high': 'High',
                'mid_grade': 'MG1',
                'mid_grade_1': 'MG1',
                'mg1': 'MG1',
                'mid_grade_2': 'MG2',
                'mg2': 'MG2',
                'low_grade': 'Low',
                'low': 'Low',
                'residuo': 'Residuo',
                'diversos': 'Diversos'
            }

            if len(categorias_presentes) == 1:
                cat = list(categorias_presentes)[0]
                bag_dict['categoria_exibicao'] = cat
                bag_dict['categoria_nome'] = categoria_nomes_map.get(cat.lower(), cat.replace('_', ' ').title())
            elif len(categorias_presentes) > 1:
                bag_dict['categoria_exibicao'] = 'DIVERSOS'
                bag_dict['categoria_nome'] = 'Diversos'
            else:
                # Se não houver itens, mantém a lógica original do bag
                if bag.classificacao_grade:
                    cat = bag.classificacao_grade.categoria
                    cat_lower = cat.lower() if cat else ''
                    bag_dict['categoria_exibicao'] = cat
                    bag_dict['categoria_nome'] = categoria_nomes_map.get(cat_lower, cat.replace('_', ' ').title())
            
            resultado.append(bag_dict)

        return jsonify(resultado)
    except Exception as e:
        logger.error(f'Erro ao listar bags do estoque: {str(e)}')
        return jsonify({'erro': str(e)}), 500


@bp.route('/lotes/<int:lote_id>/sublotes', methods=['GET'])
@jwt_required()
def obter_sublotes(lote_id):
    try:
        lote = Lote.query.get_or_404(lote_id)
        
        sublotes = Lote.query.options(
            joinedload(Lote.tipo_lote),
            joinedload(Lote.fornecedor)
        ).filter_by(lote_pai_id=lote_id).all()
        
        resultado = [sublote.to_dict() for sublote in sublotes]
        return jsonify(resultado)
    except Exception as e:
        logger.error(f'Erro ao obter sublotes do lote {lote_id}: {str(e)}')
        return jsonify({'erro': str(e)}), 500


@bp.route('/bags/<int:bag_id>/itens', methods=['GET'])
@jwt_required()
def obter_itens_bag(bag_id):
    try:
        bag = BagProducao.query.get_or_404(bag_id)
        
        itens = ItemSeparadoProducao.query.options(
            joinedload(ItemSeparadoProducao.classificacao_grade),
            joinedload(ItemSeparadoProducao.ordem_producao)
        ).filter_by(bag_id=bag_id).all()
        
        resultado = [item.to_dict() for item in itens]
        return jsonify(resultado)
    except Exception as e:
        logger.error(f'Erro ao obter itens do bag {bag_id}: {str(e)}')
        return jsonify({'erro': str(e)}), 500


@bp.route('/resumo', methods=['GET'])
@jwt_required()
def obter_resumo_estoque():
    """Resumo de estoque por categoria - dados de BAGS/OP (produção)"""
    try:
        # Verificar se usuário é admin ou gestor para retornar dados de preço
        current_user_id = get_jwt_identity()
        usuario = Usuario.query.get(current_user_id)
        
        # Verificar permissão (Admin, Gestor por tipo ou Perfil com nome Gestor)
        is_admin_or_gestor = False
        if usuario:
            is_tipo_ok = usuario.tipo in ['admin', 'gestor']
            is_perfil_ok = usuario.perfil and 'gestor' in usuario.perfil.nome.lower()
            is_admin_or_gestor = is_tipo_ok or is_perfil_ok
        
        # Calcular somatório por classificação/categoria
        # Filtra apenas bags ativos que contam como estoque
        bags_ativos = ['devolvido_estoque', 'cheio', 'aberto', 'enviado_refinaria']
        
        from sqlalchemy.orm import aliased
        from app.models import Fornecedor, Lote
        LotePai = aliased(Lote)
        
        # Query: Todos itens de bags ativos com suas classificações, e fornecedores dos lotes de origem
        resultados = db.session.query(
            ItemSeparadoProducao,
            ClassificacaoGrade,
            Lote,
            LotePai
        ).join(
            ClassificacaoGrade, ItemSeparadoProducao.classificacao_grade_id == ClassificacaoGrade.id
        ).join(
            BagProducao, ItemSeparadoProducao.bag_id == BagProducao.id
        ).outerjoin(
            Lote, ItemSeparadoProducao.entrada_estoque_id == Lote.id
        ).outerjoin(
            LotePai, Lote.lote_pai_id == LotePai.id
        ).filter(
            BagProducao.status.in_(bags_ativos)
        ).all()
        
        # Estruturar resposta
        dados = {}
        for item, classif, lote_filho, lote_pai in resultados:
            cat_key = classif.categoria or 'OUTROS'
            if cat_key not in dados:
                dados[cat_key] = {
                    'categoria': cat_key,
                    'peso_total': 0.0,
                    'total_valor': 0.0,
                    'itens': []
                }
            
            peso = float(item.peso_kg or 0)
            valor = float(item.valor_estimado or item.custo_proporcional or 0)
            
            # Buscar fornecedor
            fornecedor_nome = 'N/A'
            if lote_filho and lote_filho.fornecedor:
                fornecedor_nome = lote_filho.fornecedor.nome
            elif lote_pai and lote_pai.fornecedor:
                fornecedor_nome = lote_pai.fornecedor.nome
            elif item.observacoes and item.observacoes.startswith('Fornecedor:'):
                fornecedor_nome = item.observacoes.replace('Fornecedor: ', '').strip()
            
            preco_kg = round(valor / peso, 2) if peso > 0 else 0.0
            
            dados[cat_key]['peso_total'] += peso
            dados[cat_key]['total_valor'] += valor
            
            # Item individual
            item_data = {
                'id': item.id,
                'nome': item.nome_item,
                'classificacao': classif.nome,
                'fornecedor': fornecedor_nome,
                'peso_kg': peso
            }
            
            if is_admin_or_gestor:
                item_data['media_preco'] = preco_kg
                item_data['total_valor'] = round(valor, 2)
            
            dados[cat_key]['itens'].append(item_data)
            
        # Ordenar e formatar para lista (Categoria > Maior Peso Total)
        lista_final = []
        # Ordenar categorias por peso total decrescente
        for cat_key in sorted(dados.keys(), key=lambda k: dados[k]['peso_total'], reverse=True):
            cat_data = dados[cat_key]
            # Ordenar itens por peso dentro da categoria
            cat_data['itens'].sort(key=lambda x: x['peso_kg'], reverse=True)
            
            # Normalizar nome categoria para exibição (Labels amigáveis)
            cat_lower = cat_key.lower()
            labels = {
                'high_grade': 'High Grade', 'high': 'High Grade',
                'mg1': 'MG1', 'mid_grade': 'MG1',
                'mg2': 'MG2',
                'low_grade': 'Low Grade', 'low': 'Low Grade',
                'residuo': 'Resíduo'
            }
            cat_data['categoria_label'] = labels.get(cat_lower, cat_key.replace('_', ' ').title())
            
            # Adicionar flag de admin/gestor e calcular média geral da categoria
            cat_data['show_prices'] = is_admin_or_gestor
            if is_admin_or_gestor:
                cat_data['media_geral'] = round(cat_data['total_valor'] / cat_data['peso_total'], 2) if cat_data['peso_total'] > 0 else 0.0
            else:
                cat_data['media_geral'] = 0.0
            
            lista_final.append(cat_data)
            
        return jsonify(lista_final)

    except Exception as e:
        logger.error(f'Erro ao obter resumo: {str(e)}')
        import traceback
        traceback.print_exc()
        return jsonify({'erro': str(e)}), 500


@bp.route('/resumo-compra', methods=['GET'])
@jwt_required()
def obter_resumo_compra():
    """Resumo de compras - dados de OC aprovadas (materiais da tabela tipos-lote)"""
    try:
        # Verificar se usuário é admin ou gestor
        current_user_id = get_jwt_identity()
        usuario = Usuario.query.get(current_user_id)
        
        # Verificar permissão (Admin, Gestor por tipo ou Perfil com nome Gestor)
        is_admin_or_gestor = False
        if usuario:
            is_tipo_ok = usuario.tipo in ['admin', 'gestor']
            is_perfil_ok = usuario.perfil and 'gestor' in usuario.perfil.nome.lower()
            is_admin_or_gestor = is_tipo_ok or is_perfil_ok
        
        if not is_admin_or_gestor:
            return jsonify({'erro': 'Acesso não autorizado', 'show_tab': False}), 403
        
        from app.models import OrdemCompra, Solicitacao, TabelaPreco, TabelaPrecoItem
        
        # Buscar itens de solicitações com OC aprovadas (ou qualquer status que indique compra efetivada)
        # Status de OC que indicam compra aprovada/efetivada
        oc_status_aprovados = ['aprovada', 'em_transporte', 'recebida', 'conferida', 'finalizada']
        
        # Query: agrupar por MaterialBase (materiais da tela tipos-lote)
        resultados = db.session.query(
            MaterialBase.id,
            MaterialBase.codigo,
            MaterialBase.nome,
            MaterialBase.classificacao,
            func.sum(ItemSolicitacao.peso_kg).label('peso_total'),
            func.sum(ItemSolicitacao.preco_por_kg_snapshot * ItemSolicitacao.peso_kg).label('valor_total')
        ).join(
            ItemSolicitacao.material
        ).join(
            ItemSolicitacao.solicitacao
        ).join(
            Solicitacao.ordem_compra
        ).filter(
            OrdemCompra.status.in_(oc_status_aprovados),
            ItemSolicitacao.preco_por_kg_snapshot.isnot(None),
            ItemSolicitacao.peso_kg > 0
        ).group_by(
            MaterialBase.id,
            MaterialBase.codigo,
            MaterialBase.nome,
            MaterialBase.classificacao
        ).order_by(
            MaterialBase.classificacao,
            MaterialBase.nome
        ).all()
        
        from app.models import FornecedorTabelaPrecos
        
        # Buscar soma dos preços ativos nas tabelas PROPRIAS DOS FORNECEDORES (FornecedorTabelaPrecos)
        # Dicionário: material_id -> soma_precos_fornecedores
        soma_precos_por_material = {}
        
        # Filtrar apenas fornecedores que têm pelo menos uma OC aprovada para o material
        precos_fornecedores = db.session.query(
            FornecedorTabelaPrecos.material_id,
            func.sum(FornecedorTabelaPrecos.preco_fornecedor)
        ).join(
            Fornecedor, Fornecedor.id == FornecedorTabelaPrecos.fornecedor_id
        ).join(
            Solicitacao, Solicitacao.fornecedor_id == Fornecedor.id
        ).join(
            OrdemCompra, OrdemCompra.solicitacao_id == Solicitacao.id
        ).join(
            ItemSolicitacao, ItemSolicitacao.solicitacao_id == Solicitacao.id
        ).filter(
            FornecedorTabelaPrecos.status == 'ativo',
            OrdemCompra.status.in_(oc_status_aprovados),
            ItemSolicitacao.material_id == FornecedorTabelaPrecos.material_id
        ).group_by(
            FornecedorTabelaPrecos.material_id
        ).distinct().all()
        
        soma_precos_por_material = {pid: float(soma or 0) for pid, soma in precos_fornecedores}

        # Estruturar por classificação (high, mg1, mg2, low)
        dados = {}
        for row in resultados:
            # Unpacking manual para robustez (evita ValueError se houver colunas extras)
            if len(row) < 6:
                continue
                
            mat_id = row[0]
            mat_codigo = row[1]
            mat_nome = row[2]
            mat_classif = row[3]
            peso = row[4]
            valor = row[5]
            cat_key = mat_classif.upper() if mat_classif else 'OUTROS'
            
            if cat_key not in dados:
                dados[cat_key] = {
                    'categoria': cat_key,
                    'peso_total': 0.0,
                    'total_valor': 0.0,
                    'materiais': []
                }
            
            p = float(peso or 0)
            v = float(valor or 0)
            
            # Cálculo "Média R$": (Valor Total Pago) / (Soma dos Preços das Tabelas de Fornecedor Ativas)
            soma_tabelas = soma_precos_por_material.get(mat_id, 0.0)
            
            # Se soma_tabelas for 0, media sera 0 para nao dar erro.
            if soma_tabelas > 0:
                media = round(v / soma_tabelas, 2)
            else:
                media = 0.0
            
            dados[cat_key]['peso_total'] += p
            dados[cat_key]['total_valor'] += v
            
            dados[cat_key]['materiais'].append({
                'id': mat_id,
                'codigo': mat_codigo,
                'nome': mat_nome,
                'peso': round(p, 2),
                'valor': round(v, 2),
                'media_preco': media,
                'media_real': round(v / p, 2) if p > 0 else 0.0,  # Média Real R$/kg (Valor / Peso)
                'soma_tabelas_debug': soma_tabelas
            })
        
        # Ordenar e formatar resposta
        lista_final = []
        # Ordem de prioridade: high > mg1 > mg2 > low
        ordem_categorias = ['HIGH', 'MG1', 'MG2', 'LOW', 'OUTROS']
        
        for cat_key in ordem_categorias:
            if cat_key in dados:
                item = dados[cat_key]
                # Ordenar materiais por peso dentro da categoria
                item['materiais'].sort(key=lambda x: x['peso'], reverse=True)
                
                # Labels amigáveis
                labels = {
                    'HIGH': 'High Grade',
                    'MG1': 'MG1',
                    'MG2': 'MG2',
                    'LOW': 'Low Grade'
                }
                item['categoria_label'] = labels.get(cat_key, cat_key.title())
                
                # Calcular média geral da categoria
                item['media_geral'] = round(item['total_valor'] / item['peso_total'], 2) if item['peso_total'] > 0 else 0.0
                item['show_prices'] = True
                
                lista_final.append(item)
        
        return jsonify({
            'show_tab': True,
            'dados': lista_final
        })

    except Exception as e:
        logger.error(f'Erro ao obter resumo de compras: {str(e)}')
        import traceback
        traceback.print_exc()
        return jsonify({'erro': str(e), 'show_tab': False}), 500


# ============================
# PRODUÇÃO - Enviar para Produção (novo fluxo)
# ============================

@bp.route('/producao/enviar', methods=['POST'])
@jwt_required()
def enviar_para_producao():
    """Envia sublote(s) para produção - muda status para em_producao e reserva"""
    try:
        data = request.get_json()
        sublote_ids = data.get('sublote_ids', [])
        
        if not sublote_ids:
            return jsonify({'erro': 'Nenhum sublote selecionado'}), 400
        
        current_user_id = get_jwt_identity()
        sublotes_enviados = []
        
        for sid in sublote_ids:
            sublote = Lote.query.get(sid)
            if not sublote:
                continue
            if sublote.status == 'em_producao':
                continue
            
            sublote.status = 'em_producao'
            sublote.reservado = True
            sublote.reservado_para = 'Produção'
            sublote.reservado_por_id = current_user_id
            sublote.reservado_em = datetime.utcnow()
            sublotes_enviados.append(sublote.numero_lote)
        
        db.session.commit()
        
        return jsonify({
            'sucesso': True,
            'mensagem': f'{len(sublotes_enviados)} material(is) enviado(s) para produção',
            'sublotes': sublotes_enviados
        })
    except Exception as e:
        db.session.rollback()
        logger.error(f'Erro ao enviar para produção: {str(e)}')
        return jsonify({'erro': str(e)}), 500


@bp.route('/producao/sublote/<int:sublote_id>', methods=['GET'])
@jwt_required()
def obter_detalhes_producao(sublote_id):
    """Obtém detalhes de um sublote em produção para o modal"""
    try:
        sublote = Lote.query.options(
            joinedload(Lote.tipo_lote),
            joinedload(Lote.fornecedor),
            joinedload(Lote.lote_pai)
        ).get_or_404(sublote_id)
        
        peso_original = float(sublote.peso_liquido or sublote.peso_total_kg or 0)
        
        # Buscar itens já separados deste sublote (APENAS os da produção atual - sem bag)
        itens_separados = ItemSeparadoProducao.query.filter_by(
            entrada_estoque_id=sublote_id
        ).filter(
            ItemSeparadoProducao.bag_id.is_(None)
        ).all()
        
        peso_separado = sum(float(i.peso_kg or 0) for i in itens_separados)
        peso_restante = peso_original - peso_separado
        
        # Nome do material
        nome_material = 'Material'
        if sublote.observacoes:
            if sublote.observacoes.startswith('MATERIAL:'):
                nome_material = sublote.observacoes.split('|')[0].replace('MATERIAL:', '').strip()
            elif sublote.observacoes.startswith('MATERIAL_MANUAL:'):
                nome_material = sublote.observacoes.split('|')[0].replace('MATERIAL_MANUAL:', '').strip()
        elif sublote.tipo_lote:
            nome_material = sublote.tipo_lote.nome
        
        # Calcular valor/kg originais (da OC)
        valor_por_kg = 0
        valor_total_lote = float(sublote.valor_total or 0)
        if valor_total_lote > 0 and peso_original > 0:
            valor_por_kg = valor_total_lote / peso_original
        else:
            # Tentar de itens da solicitação
            if sublote.lote_pai and sublote.lote_pai.solicitacao_origem_id:
                itens_solic = ItemSolicitacao.query.filter_by(
                    solicitacao_id=sublote.lote_pai.solicitacao_origem_id,
                ).all()
                if itens_solic:
                    total_val = sum(float(i.valor_calculado or 0) for i in itens_solic)
                    total_peso = sum(float(i.peso_kg or 0) for i in itens_solic)
                    if total_peso > 0:
                        valor_por_kg = total_val / total_peso
        
        # Listar itens já separados
        itens_data = []
        for item in itens_separados:
            itens_data.append({
                'id': item.id,
                'nome_item': item.nome_item,
                'peso_kg': float(item.peso_kg),
                'classificacao_nome': item.classificacao_grade.nome if item.classificacao_grade else 'N/A',
                'classificacao_categoria': item.classificacao_grade.categoria if item.classificacao_grade else 'N/A',
                'valor_estimado': float(item.valor_estimado or 0),
                'data_separacao': item.data_separacao.isoformat() if item.data_separacao else None,
                'observacoes': item.observacoes
            })
        
        return jsonify({
            'sublote_id': sublote.id,
            'numero_lote': sublote.numero_lote,
            'nome_material': nome_material,
            'fornecedor_nome': sublote.fornecedor.nome if sublote.fornecedor else 'N/A',
            'peso_original': round(peso_original, 3),
            'peso_separado': round(peso_separado, 3),
            'peso_restante': round(max(0, peso_restante), 3),
            'valor_por_kg': round(valor_por_kg, 2),
            'valor_total_lote': round(valor_total_lote, 2),
            'status': sublote.status,
            'itens_separados': itens_data,
            'total_itens': len(itens_data)
        })
    except Exception as e:
        logger.error(f'Erro ao obter detalhes produção sublote {sublote_id}: {str(e)}')
        return jsonify({'erro': str(e)}), 500


@bp.route('/producao/sublote/<int:sublote_id>/adicionar-item', methods=['POST'])
@jwt_required()
def adicionar_item_separado(sublote_id):
    """Adiciona um item separado (quebrando material em partes)"""
    try:
        sublote = Lote.query.get_or_404(sublote_id)
        data = request.get_json()
        
        nome_item = data.get('nome_item', '').strip()
        peso_kg = float(data.get('peso_kg', 0))
        classificacao_id = data.get('classificacao_id')
        preco_kg = float(data.get('preco_kg', 0))
        observacoes = data.get('observacoes', '')
        
        if not nome_item:
            return jsonify({'erro': 'Nome do material é obrigatório'}), 400
        if peso_kg <= 0:
            return jsonify({'erro': 'Peso deve ser maior que zero'}), 400
        if not classificacao_id:
            return jsonify({'erro': 'Classificação é obrigatória'}), 400
        
        # Verificar peso disponível
        # Apenas contar itens que NÃO estão em bags (itens sendo separados na produção)
        # Itens já enviados para bags foram processados por outra rota e não devem contar aqui
        itens_existentes = ItemSeparadoProducao.query.filter(
            ItemSeparadoProducao.entrada_estoque_id == sublote_id,
            ItemSeparadoProducao.bag_id.is_(None)
        ).all()
        peso_ja_separado = sum(float(i.peso_kg or 0) for i in itens_existentes)
        peso_original = float(sublote.peso_liquido or sublote.peso_total_kg or 0)
        peso_restante = peso_original - peso_ja_separado
        
        if peso_kg > peso_restante + 0.01:  # margem de arredondamento
            return jsonify({'erro': f'Peso excede o disponível ({peso_restante:.3f} kg)'}), 400
        
        # Verificar classificação
        classificacao = ClassificacaoGrade.query.get(classificacao_id)
        if not classificacao:
            return jsonify({'erro': 'Classificação não encontrada'}), 400
        
        current_user_id = get_jwt_identity()
        
        # Criar item separado
        novo_item = ItemSeparadoProducao(
            classificacao_grade_id=classificacao_id,
            nome_item=nome_item,
            peso_kg=peso_kg,
            quantidade=1,
            valor_estimado=round(preco_kg * peso_kg, 2),
            custo_proporcional=round(preco_kg * peso_kg, 2),
            separado_por_id=current_user_id,
            data_separacao=datetime.utcnow(),
            observacoes=observacoes,
            entrada_estoque_id=sublote_id
        )
        db.session.add(novo_item)
        
        # Salvar nome do material para autocomplete futuro
        # (Classificações de grade já servem este propósito)
        
        db.session.commit()
        
        # Recalcular restante
        peso_ja_separado += peso_kg
        novo_restante = peso_original - peso_ja_separado
        
        return jsonify({
            'sucesso': True,
            'item': novo_item.to_dict(),
            'peso_separado_total': round(peso_ja_separado, 3),
            'peso_restante': round(max(0, novo_restante), 3)
        })
    except Exception as e:
        db.session.rollback()
        logger.error(f'Erro ao adicionar item separado: {str(e)}')
        return jsonify({'erro': str(e)}), 500


@bp.route('/producao/sublote/<int:sublote_id>/remover-item/<int:item_id>', methods=['DELETE'])
@jwt_required()
def remover_item_separado(sublote_id, item_id):
    """Remove um item separado"""
    try:
        item = ItemSeparadoProducao.query.filter_by(
            id=item_id,
            entrada_estoque_id=sublote_id
        ).first_or_404()
        
        db.session.delete(item)
        db.session.commit()
        
        return jsonify({'sucesso': True, 'mensagem': 'Item removido'})
    except Exception as e:
        db.session.rollback()
        logger.error(f'Erro ao remover item separado: {str(e)}')
        return jsonify({'erro': str(e)}), 500


@bp.route('/producao/sublote/<int:sublote_id>/devolver-estoque', methods=['POST'])
@jwt_required()
def devolver_sublote_estoque(sublote_id):
    """Devolve material restante ao estoque e finaliza a produção do sublote"""
    try:
        sublote = Lote.query.get_or_404(sublote_id)
        
        # Calcular pesos - APENAS itens do modal de produção (sem bag)
        # Itens já enviados para bags NÃO devem ser contados nem duplicados
        itens_separados = ItemSeparadoProducao.query.filter(
            ItemSeparadoProducao.entrada_estoque_id == sublote_id,
            ItemSeparadoProducao.bag_id.is_(None)
        ).all()
        peso_separado = sum(float(i.peso_kg or 0) for i in itens_separados)
        peso_original = float(sublote.peso_liquido or sublote.peso_total_kg or 0)
        peso_restante = peso_original - peso_separado
        
        if peso_separado <= 0:
            # Nada foi separado, apenas devolver ao estoque
            sublote.status = 'em_estoque'
            sublote.reservado = False
            sublote.reservado_para = None
            sublote.reservado_por_id = None
            sublote.reservado_em = None
            db.session.commit()
            return jsonify({
                'sucesso': True,
                'mensagem': 'Material devolvido ao estoque sem separação',
                'peso_devolvido': round(peso_original, 3)
            })
        
        if peso_restante > 0.01:
            # Atualizar peso do sublote original com o que resta
            sublote.peso_liquido = peso_restante
            sublote.peso_total_kg = peso_restante
            sublote.status = 'em_estoque'
            sublote.reservado = False
            sublote.reservado_para = None
            sublote.reservado_por_id = None
            sublote.reservado_em = None
            
            # Recalcular valor proporcional do que ficou
            valor_total_original = float(sublote.valor_total or 0)
            if valor_total_original > 0 and peso_original > 0:
                sublote.valor_total = round((peso_restante / peso_original) * valor_total_original, 2)
            
            mensagem = f'Devolvido {peso_restante:.3f} kg ao estoque. {peso_separado:.3f} kg separado(s).'
        else:
            # Todo material foi separado - sublote "desaparece" (muda status)
            sublote.status = 'processado'
            sublote.reservado = False
            sublote.reservado_para = None
            sublote.reservado_por_id = None
            sublote.reservado_em = None
            sublote.peso_liquido = 0
            sublote.peso_total_kg = 0
            mensagem = f'Todo material ({peso_separado:.3f} kg) foi separado. Lote finalizado.'
        
        # Criar novos sublotes para itens separados (como novos materiais no estoque)
        lote_pai = sublote.lote_pai or sublote
        novos_sublotes = []
        
        for item in itens_separados:
            # Gerar novo número de lote
            ano = datetime.now().year
            novo_numero = f"{ano}-{str(uuid.uuid4().hex[:5]).upper()}"
            
            novo_sublote = Lote(
                numero_lote=novo_numero,
                fornecedor_id=sublote.fornecedor_id,
                tipo_lote_id=sublote.tipo_lote_id,
                solicitacao_origem_id=sublote.solicitacao_origem_id or (lote_pai.solicitacao_origem_id if lote_pai != sublote else None),
                oc_id=sublote.oc_id or (lote_pai.oc_id if lote_pai != sublote else None),
                peso_bruto_recebido=float(item.peso_kg),
                peso_liquido=float(item.peso_kg),
                peso_total_kg=float(item.peso_kg),
                valor_total=float(item.valor_estimado or 0),
                quantidade_itens=1,
                status='criado_separacao',
                lote_pai_id=lote_pai.id,
                observacoes=f"MATERIAL:{item.nome_item}|CLASSIFICACAO:{item.classificacao_grade.nome if item.classificacao_grade else 'N/A'}|PRECO_KG:{float(item.valor_estimado or 0) / float(item.peso_kg) if float(item.peso_kg) > 0 else 0:.2f}",
                classificacao_predominante=item.classificacao_grade.categoria if item.classificacao_grade else None,
                data_criacao=datetime.utcnow()
            )
            db.session.add(novo_sublote)
            novos_sublotes.append(novo_sublote)
            
            # Remover o item temporário da separação pois ele agora se tornou um Lote real no estoque
            db.session.delete(item)
        
        db.session.commit()
        
        return jsonify({
            'sucesso': True,
            'mensagem': mensagem,
            'peso_devolvido': round(max(0, peso_restante), 3),
            'peso_separado': round(peso_separado, 3),
            'novos_sublotes': [{'id': s.id, 'numero_lote': s.numero_lote} for s in novos_sublotes]
        })
    except Exception as e:
        db.session.rollback()
        logger.error(f'Erro ao devolver sublote {sublote_id} ao estoque: {str(e)}')
        return jsonify({'erro': str(e)}), 500


@bp.route('/producao/em-separacao', methods=['GET'])
@jwt_required()
def listar_em_separacao():
    """Lista materiais em processo de separação (para admin panel)"""
    try:
        lotes_em_producao = Lote.query.options(
            joinedload(Lote.tipo_lote),
            joinedload(Lote.fornecedor),
            joinedload(Lote.lote_pai)
        ).filter(
            Lote.status == 'em_producao'
        ).order_by(Lote.reservado_em.desc()).all()
        
        resultado = []
        for lote in lotes_em_producao:
            peso_original = float(lote.peso_liquido or lote.peso_total_kg or 0)
            
            # Contar itens separados (apenas os sem bag - mesmos da produção modal)
            itens = ItemSeparadoProducao.query.filter(
                ItemSeparadoProducao.entrada_estoque_id == lote.id,
                ItemSeparadoProducao.bag_id.is_(None)
            ).all()
            peso_separado = sum(float(i.peso_kg or 0) for i in itens)
            
            nome_material = 'Material'
            if lote.observacoes:
                if lote.observacoes.startswith('MATERIAL:'):
                    nome_material = lote.observacoes.split('|')[0].replace('MATERIAL:', '').strip()
                elif lote.observacoes.startswith('MATERIAL_MANUAL:'):
                    nome_material = lote.observacoes.split('|')[0].replace('MATERIAL_MANUAL:', '').strip()
            elif lote.tipo_lote:
                nome_material = lote.tipo_lote.nome
            
            resultado.append({
                'id': lote.id,
                'numero_lote': lote.numero_lote,
                'nome_material': nome_material,
                'fornecedor_nome': lote.fornecedor.nome if lote.fornecedor else 'N/A',
                'peso_original': round(peso_original, 2),
                'peso_separado': round(peso_separado, 2),
                'peso_restante': round(max(0, peso_original - peso_separado), 2),
                'quantidade_itens': len(itens),
                'status': lote.status,
                'reservado_em': lote.reservado_em.isoformat() if lote.reservado_em else None,
                'data_criacao': lote.data_criacao.isoformat() if lote.data_criacao else None
            })
        
        return jsonify(resultado)
    except Exception as e:
        logger.error(f'Erro ao listar materiais em separação: {str(e)}')
        return jsonify({'erro': str(e)}), 500


@bp.route('/classificacoes/autocomplete', methods=['GET'])
@jwt_required()
def autocomplete_classificacoes():
    """Lista classificações para autocomplete no modal de produção"""
    try:
        # Garantir que as 4 categorias fixas existam
        categorias_obrigatorias = [
            {'nome': 'High Grade', 'categoria': 'HIGH_GRADE'},
            {'nome': 'Low Grade', 'categoria': 'LOW_GRADE'},
            {'nome': 'MG1', 'categoria': 'MG1'},
            {'nome': 'MG2', 'categoria': 'MG2'},
        ]
        
        for cat_info in categorias_obrigatorias:
            existe = ClassificacaoGrade.query.filter_by(
                categoria=cat_info['categoria'], ativo=True
            ).first()
            if not existe:
                nova = ClassificacaoGrade(
                    nome=cat_info['nome'],
                    categoria=cat_info['categoria'],
                    ativo=True,
                    data_cadastro=datetime.utcnow()
                )
                db.session.add(nova)
        
        db.session.commit()
        
        classificacoes = ClassificacaoGrade.query.filter_by(ativo=True).order_by(
            ClassificacaoGrade.categoria,
            ClassificacaoGrade.nome
        ).all()
        
        return jsonify([{
            'id': c.id,
            'nome': c.nome,
            'categoria': c.categoria,
            'preco_estimado_kg': float(c.preco_estimado_kg) if c.preco_estimado_kg else 0
        } for c in classificacoes])
    except Exception as e:
        db.session.rollback()
        logger.error(f'Erro ao listar classificações: {str(e)}')
        return jsonify({'erro': str(e)}), 500


# ============================
# BAGS - Novo fluxo
# ============================

@bp.route('/bags/criar', methods=['POST'])
@jwt_required()
def criar_bag():
    """Cria um novo bag"""
    try:
        data = request.get_json()
        nome = data.get('nome', '').strip()
        classificacao_id = data.get('classificacao_id')
        
        current_user_id = get_jwt_identity()
        
        # Se não informou classificação, usar a primeira HIGH_GRADE por padrão
        if not classificacao_id:
            classif = ClassificacaoGrade.query.filter_by(categoria='HIGH_GRADE', ativo=True).first()
            if classif:
                classificacao_id = classif.id
            else:
                classif = ClassificacaoGrade.query.filter_by(ativo=True).first()
                classificacao_id = classif.id if classif else None
        
        if not classificacao_id:
            return jsonify({'erro': 'Nenhuma classificação disponível'}), 400
        
        classif = ClassificacaoGrade.query.get(classificacao_id)
        
        # Gerar código
        codigo = BagProducao.gerar_codigo_bag(nome or classif.nome)
        
        nova_bag = BagProducao(
            codigo=codigo,
            classificacao_grade_id=classificacao_id,
            peso_acumulado=0,
            quantidade_itens=0,
            status='aberto',
            criado_por_id=current_user_id,
            categoria_manual=nome if nome else None,
            data_criacao=datetime.utcnow()
        )
        db.session.add(nova_bag)
        db.session.commit()
        
        return jsonify({
            'sucesso': True,
            'bag': nova_bag.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        logger.error(f'Erro ao criar bag: {str(e)}')
        return jsonify({'erro': str(e)}), 500


@bp.route('/bags/abertos', methods=['GET'])
@jwt_required()
def listar_bags_abertos():
    """Lista bags abertos para seleção"""
    try:
        bags = BagProducao.query.options(
            joinedload(BagProducao.classificacao_grade)
        ).filter(
            BagProducao.status == 'aberto'
        ).order_by(BagProducao.data_criacao.desc()).all()
        
        return jsonify([{
            'id': b.id,
            'codigo': b.codigo,
            'classificacao_nome': b.classificacao_grade.nome if b.classificacao_grade else 'N/A',
            'categoria': b.classificacao_grade.categoria if b.classificacao_grade else 'N/A',
            'peso_acumulado': float(b.peso_acumulado or 0),
            'quantidade_itens': b.quantidade_itens or 0,
            'categoria_manual': b.categoria_manual,
            'data_criacao': b.data_criacao.isoformat() if b.data_criacao else None
        } for b in bags])
    except Exception as e:
        logger.error(f'Erro ao listar bags abertos: {str(e)}')
        return jsonify({'erro': str(e)}), 500


@bp.route('/bags/adicionar-materiais', methods=['POST'])
@jwt_required()
def adicionar_materiais_bag():
    """Adiciona materiais selecionados a um bag (com suporte a quantidades parciais)"""
    try:
        data = request.get_json()
        bag_id = data.get('bag_id')
        materiais = data.get('materiais', [])  # [{sublote_id, peso_enviar}]
        
        if not bag_id:
            return jsonify({'erro': 'Bag não selecionado'}), 400
        if not materiais:
            return jsonify({'erro': 'Nenhum material selecionado'}), 400
        
        bag = BagProducao.query.get_or_404(bag_id)
        
        if bag.status != 'aberto':
            return jsonify({'erro': 'Este bag está fechado e não aceita mais materiais'}), 400
        
        current_user_id = get_jwt_identity()
        total_peso_adicionado = 0
        total_itens_adicionados = 0
        
        for mat in materiais:
            sublote_id = mat.get('sublote_id')
            peso_enviar = float(mat.get('peso_enviar', 0))
            
            if not sublote_id or peso_enviar <= 0:
                continue
            
            sublote = Lote.query.get(sublote_id)
            if not sublote:
                continue
            
            peso_atual = float(sublote.peso_liquido or sublote.peso_total_kg or 0)
            
            if peso_enviar > peso_atual + 0.01:
                continue  # Skip if requested more than available
            
            # Extrair info do material
            nome_material = 'Material'
            preco_kg = 0
            classificacao_categoria = None
            
            if sublote.observacoes:
                partes = sublote.observacoes.split('|')
                for parte in partes:
                    if parte.startswith('MATERIAL:') or parte.startswith('MATERIAL_MANUAL:'):
                        nome_material = parte.replace('MATERIAL_MANUAL:', '').replace('MATERIAL:', '').strip()
                    elif parte.startswith('PRECO_KG:'):
                        try:
                            preco_kg = float(parte.replace('PRECO_KG:', '').strip())
                        except:
                            pass
                    elif parte.startswith('CLASSIFICACAO:'):
                        classificacao_categoria = parte.replace('CLASSIFICACAO:', '').strip()
            elif sublote.tipo_lote:
                nome_material = sublote.tipo_lote.nome
            
            # Calcular preço por kg se não veio das observações
            if preco_kg <= 0:
                preco_kg = _calcular_preco_kg_sublote(sublote)
            
            # Determinar classificação correta do item baseada no sublote
            item_classificacao_id = bag.classificacao_grade_id  # fallback
            
            # Prioridade 1: classificacao_predominante do sublote
            if sublote.classificacao_predominante:
                classif_match = ClassificacaoGrade.query.filter(
                    func.lower(ClassificacaoGrade.categoria) == sublote.classificacao_predominante.lower(),
                    ClassificacaoGrade.ativo == True
                ).first()
                if classif_match:
                    item_classificacao_id = classif_match.id
            
            # Prioridade 2: CLASSIFICACAO nas observações do sublote
            if item_classificacao_id == bag.classificacao_grade_id and classificacao_categoria:
                classif_match = ClassificacaoGrade.query.filter(
                    func.lower(ClassificacaoGrade.nome) == classificacao_categoria.lower(),
                    ClassificacaoGrade.ativo == True
                ).first()
                if not classif_match:
                    classif_match = ClassificacaoGrade.query.filter(
                        func.lower(ClassificacaoGrade.categoria).like(f'%{classificacao_categoria.lower()}%'),
                        ClassificacaoGrade.ativo == True
                    ).first()
                if classif_match:
                    item_classificacao_id = classif_match.id
            
            # Criar item no bag
            novo_item = ItemSeparadoProducao(
                classificacao_grade_id=item_classificacao_id,
                nome_item=nome_material,
                peso_kg=peso_enviar,
                quantidade=1,
                valor_estimado=round(preco_kg * peso_enviar, 2),
                custo_proporcional=round(preco_kg * peso_enviar, 2),
                separado_por_id=current_user_id,
                data_separacao=datetime.utcnow(),
                bag_id=bag_id,
                entrada_estoque_id=sublote_id,
                observacoes=f"Fornecedor: {sublote.fornecedor.nome if sublote.fornecedor else 'N/A'}"
            )
            db.session.add(novo_item)
            
            # Atualizar sublote
            if abs(peso_enviar - peso_atual) < 0.01:
                # Todo material enviado - sublote "desaparece"
                sublote.status = 'processado'
                sublote.peso_liquido = 0
                sublote.peso_total_kg = 0
            else:
                # Parcial - reduzir peso
                novo_peso = peso_atual - peso_enviar
                sublote.peso_liquido = novo_peso
                sublote.peso_total_kg = novo_peso
                
                # Recalcular valor proporcional
                valor_total_original = float(sublote.valor_total or 0)
                if valor_total_original > 0 and peso_atual > 0:
                    sublote.valor_total = round((novo_peso / peso_atual) * valor_total_original, 2)
            
            total_peso_adicionado += peso_enviar
            total_itens_adicionados += 1
        
        # Atualizar bag
        bag.peso_acumulado = float(bag.peso_acumulado or 0) + total_peso_adicionado
        bag.quantidade_itens = (bag.quantidade_itens or 0) + total_itens_adicionados
        bag.data_atualizacao = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'sucesso': True,
            'mensagem': f'{total_itens_adicionados} material(is) adicionado(s) ao bag',
            'peso_adicionado': round(total_peso_adicionado, 3),
            'bag': bag.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        logger.error(f'Erro ao adicionar materiais ao bag: {str(e)}')
        return jsonify({'erro': str(e)}), 500


@bp.route('/bags/<int:bag_id>/fechar', methods=['POST'])
@jwt_required()
def fechar_bag(bag_id):
    """Fecha um bag (não aceita mais adições)"""
    try:
        bag = BagProducao.query.get_or_404(bag_id)
        
        if bag.status != 'aberto':
            return jsonify({'erro': 'Bag já está fechado'}), 400
        
        # Generate ordem_exportacao - sequential per day
        hoje_br = datetime.utcnow() - timedelta(hours=3)
        ano = hoje_br.strftime('%Y')
        mes = hoje_br.strftime('%m')
        dia = hoje_br.strftime('%d')
        prefixo_dia = f"{ano}-{mes}-{dia}-"
        ultima_ordem = BagProducao.query.filter(
            BagProducao.ordem_exportacao.like(f'{prefixo_dia}%')
        ).order_by(BagProducao.ordem_exportacao.desc()).first()
        if ultima_ordem and ultima_ordem.ordem_exportacao:
            ultimo_seq = int(ultima_ordem.ordem_exportacao.split('-')[-1])
            seq = f"{ultimo_seq + 1:04d}"
        else:
            seq = "0001"
        ordem_ex = f"{prefixo_dia}{seq}"
        
        bag.status = 'cheio'
        bag.ordem_exportacao = ordem_ex
        bag.data_atualizacao = datetime.utcnow()
        db.session.commit()
        
        return jsonify({'sucesso': True, 'mensagem': 'Bag fechado com sucesso', 'bag': bag.to_dict()})
    except Exception as e:
        db.session.rollback()
        logger.error(f'Erro ao fechar bag {bag_id}: {str(e)}')
        return jsonify({'erro': str(e)}), 500


@bp.route('/bags/<int:bag_id>/reabrir', methods=['POST'])
@jwt_required()
def reabrir_bag(bag_id):
    """Reabre um bag fechado/devolvido ao estoque e limpa informações de exportação/rastreio"""
    try:
        bag = BagProducao.query.get_or_404(bag_id)
        
        if bag.status == 'aberto':
            return jsonify({'erro': 'Bag já está aberto'}), 400
            
        bag.status = 'aberto'
        bag.ordem_exportacao = None
        bag.numero_remessa = None
        bag.data_envio_refinaria = None
        bag.enviado_por_id = None
        bag.data_atualizacao = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'sucesso': True, 
            'mensagem': 'Bag reaberto com sucesso. Você pode adicionar/remover itens novamente.',
            'bag': bag.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        logger.error(f'Erro ao reabrir bag {bag_id}: {str(e)}')
        return jsonify({'erro': str(e)}), 500


@bp.route('/bags/<int:bag_id>/remover-item/<int:item_id>', methods=['DELETE'])
@jwt_required()
def remover_item_bag(bag_id, item_id):
    """Remove um item de um bag e devolve o respectivo peso ao Lote/Sublote de origem"""
    try:
        bag = BagProducao.query.get_or_404(bag_id)
        
        if bag.status != 'aberto':
            return jsonify({'erro': 'Só é possível remover itens de bags abertos'}), 400
            
        item = ItemSeparadoProducao.query.filter_by(id=item_id, bag_id=bag_id).first_or_404()
        
        # Devolver peso ao Lote de origem
        if item.entrada_estoque_id:
            sublote = Lote.query.get(item.entrada_estoque_id)
            if sublote:
                peso_kg = float(item.peso_kg or 0)
                peso_atual_sublote = float(sublote.peso_liquido or sublote.peso_total_kg or 0)
                novo_peso = peso_atual_sublote + peso_kg
                
                # Se o sublote estava processado (peso 0), reativar seu status para poder ser usado novamente
                if sublote.status == 'processado':
                    sublote.status = 'em_estoque'
                    
                sublote.peso_liquido = novo_peso
                sublote.peso_total_kg = novo_peso
                
                # Recalcular valor total do sublote
                preco_kg_item = float(item.valor_estimado or 0) / peso_kg if peso_kg > 0 else 0
                valor_adicionado = preco_kg_item * peso_kg
                sublote.valor_total = float(sublote.valor_total or 0) + valor_adicionado

        # Atualizar dados do Bag
        bag.peso_acumulado = max(0, float(bag.peso_acumulado or 0) - float(item.peso_kg or 0))
        bag.quantidade_itens = max(0, (bag.quantidade_itens or 1) - 1)
        bag.data_atualizacao = datetime.utcnow()
        
        # Deletar item do bag
        db.session.delete(item)
        db.session.commit()
        
        return jsonify({
            'sucesso': True,
            'mensagem': 'Item removido do bag e devolvido ao estoque original',
            'bag_info': {
                'peso_acumulado': bag.peso_acumulado,
                'quantidade_itens': bag.quantidade_itens
            }
        })
    except Exception as e:
        db.session.rollback()
        logger.error(f'Erro ao remover item {item_id} do bag {bag_id}: {str(e)}')
        return jsonify({'erro': str(e)}), 500


@bp.route('/bags/<int:bag_id>/detalhes', methods=['GET'])
@jwt_required()
def detalhes_bag(bag_id):
    """Detalhes completos do bag com cálculo de valor médio"""
    try:
        bag = BagProducao.query.options(
            joinedload(BagProducao.classificacao_grade),
            joinedload(BagProducao.criado_por)
        ).get_or_404(bag_id)
        
        # Buscar todos itens do bag
        itens = ItemSeparadoProducao.query.options(
            joinedload(ItemSeparadoProducao.classificacao_grade)
        ).filter_by(bag_id=bag_id).all()
        
        materiais = []
        total_peso = 0
        total_valor = 0
        
        for item in itens:
            peso = float(item.peso_kg or 0)
            # Usar valor já salvo no item (calculado quando adicionado ao bag)
            valor = float(item.valor_estimado or item.custo_proporcional or 0)
            
            # Se valor é zero, recalcular dinamicamente a partir do sublote de origem
            if valor <= 0 and peso > 0 and item.entrada_estoque_id:
                sublote_origem = Lote.query.options(
                    joinedload(Lote.lote_pai)
                ).get(item.entrada_estoque_id)
                if sublote_origem:
                    preco_encontrado = _calcular_preco_kg_sublote(sublote_origem)
                    if preco_encontrado > 0:
                        valor = round(preco_encontrado * peso, 2)
                        # Atualizar no banco para não precisar recalcular na próxima vez
                        item.valor_estimado = valor
                        item.custo_proporcional = valor
            
            preco_kg = round(valor / peso, 2) if peso > 0 else 0
            
            # Buscar fornecedor do lote de origem
            fornecedor_nome = 'N/A'
            if item.entrada_estoque_id:
                sublote_origem = Lote.query.options(
                    joinedload(Lote.fornecedor),
                    joinedload(Lote.lote_pai)
                ).get(item.entrada_estoque_id)
                if sublote_origem:
                    if sublote_origem.fornecedor:
                        fornecedor_nome = sublote_origem.fornecedor.nome
                    elif sublote_origem.lote_pai and sublote_origem.lote_pai.fornecedor:
                        fornecedor_nome = sublote_origem.lote_pai.fornecedor.nome
            
            # Fallback: observações do item
            if fornecedor_nome == 'N/A' and item.observacoes and item.observacoes.startswith('Fornecedor:'):
                fornecedor_nome = item.observacoes.replace('Fornecedor: ', '')
            
            materiais.append({
                'id': item.id,
                'nome': item.nome_item,
                'peso_kg': round(peso, 3),
                'preco_kg': preco_kg,
                'valor_total': round(valor, 2),
                'classificacao': item.classificacao_grade.nome if item.classificacao_grade else 'N/A',
                'categoria': item.classificacao_grade.categoria if item.classificacao_grade else 'N/A',
                'fornecedor': fornecedor_nome,
                'data': item.data_separacao.isoformat() if item.data_separacao else None
            })
            
            total_peso += peso
            total_valor += valor
        
        # Salvar atualizações de valor (se algum foi recalculado)
        try:
            db.session.commit()
        except:
            db.session.rollback()
        
        media_preco_kg = round(total_valor / total_peso, 2) if total_peso > 0 else 0
        
        bag_dict = bag.to_dict()
        bag_dict['materiais'] = materiais
        bag_dict['total_peso'] = round(total_peso, 3)
        bag_dict['total_valor'] = round(total_valor, 2)
        bag_dict['media_preco_kg'] = media_preco_kg
        bag_dict['total_materiais'] = len(materiais)
        
        return jsonify(bag_dict)
    except Exception as e:
        logger.error(f'Erro ao obter detalhes do bag {bag_id}: {str(e)}')
        return jsonify({'erro': str(e)}), 500


