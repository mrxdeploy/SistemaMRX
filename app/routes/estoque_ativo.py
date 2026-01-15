from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import db, Lote, BagProducao, ItemSeparadoProducao, ClassificacaoGrade
from sqlalchemy.orm import joinedload, selectinload
import logging

logger = logging.getLogger(__name__)

bp = Blueprint('estoque_ativo', __name__, url_prefix='/api/estoque-ativo')

# Status de lotes ativos (incluindo sublotes criados na separação)
LOTES_ATIVOS_STATUS = ['em_estoque', 'disponivel', 'aprovado', 'em_producao', 'CRIADO_SEPARACAO', 'PROCESSADO', 'criado_separacao', 'processado']

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
            query = query.join(ClassificacaoGrade).filter(ClassificacaoGrade.categoria == categoria)

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
            
            # Determinar categoria exibição
            if bag.classificacao_grade:
                cat = bag.classificacao_grade.categoria
                cat_lower = cat.lower() if cat else ''
                bag_dict['categoria_exibicao'] = cat
                categoria_nomes = {
                    'high_grade': 'High',
                    'high': 'High',
                    'mid_grade': 'MG1',
                    'mid_grade_1': 'MG1',
                    'mg1': 'MG1',
                    'mid_grade_2': 'MG2',
                    'mg2': 'MG2',
                    'low_grade': 'Low',
                    'low': 'Low',
                    'residuo': 'Residuo'
                }
                bag_dict['categoria_nome'] = categoria_nomes.get(cat_lower, cat.replace('_', ' ').title())
            
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
    try:
        # Calcular somatório por classificação/categoria
        # Filtra apenas bags ativos que contam como estoque
        bags_ativos = ['devolvido_estoque', 'cheio', 'aberto', 'enviado_refinaria']
        
        resultados = db.session.query(
            ClassificacaoGrade.categoria,
            ClassificacaoGrade.nome,
            db.func.sum(ItemSeparadoProducao.peso_kg)
        ).join(
            ItemSeparadoProducao.classificacao_grade
        ).join(
            ItemSeparadoProducao.bag
        ).filter(
            BagProducao.status.in_(bags_ativos)
        ).group_by(
            ClassificacaoGrade.categoria,
            ClassificacaoGrade.nome
        ).all()
        
        # Estruturar resposta
        dados = {}
        for cat, classif, peso in resultados:
            cat_key = cat or 'OUTROS'
            if cat_key not in dados:
                dados[cat_key] = {
                    'categoria': cat_key,
                    'peso_total': 0.0,
                    'classificacoes': []
                }
            
            p = float(peso or 0)
            dados[cat_key]['peso_total'] += p
            dados[cat_key]['classificacoes'].append({
                'nome': classif,
                'peso': p
            })
            
        # Ordenar e formatar para lista (Categoria > Maior Peso Total)
        lista_final = []
        # Ordenar categorias por peso total decrescente
        for cat_key in sorted(dados.keys(), key=lambda k: dados[k]['peso_total'], reverse=True):
            item = dados[cat_key]
            # Ordenar classificações por peso dentro da categoria
            item['classificacoes'].sort(key=lambda x: x['peso'], reverse=True)
            
            # Normalizar nome categoria para exibição (Labels amigáveis)
            cat_lower = cat_key.lower()
            labels = {
                'high_grade': 'High Grade', 'high': 'High Grade',
                'mg1': 'MG1', 'mid_grade': 'MG1',
                'mg2': 'MG2',
                'low_grade': 'Low Grade', 'low': 'Low Grade',
                'residuo': 'Resíduo'
            }
            item['categoria_label'] = labels.get(cat_lower, cat_key.replace('_', ' ').title())
            
            lista_final.append(item)
            
        return jsonify(lista_final)

    except Exception as e:
        logger.error(f'Erro ao obter resumo: {str(e)}')
        return jsonify({'erro': str(e)}), 500
