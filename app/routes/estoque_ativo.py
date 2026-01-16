from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import db, Lote, BagProducao, ItemSeparadoProducao, ClassificacaoGrade, ItemSolicitacao, MaterialBase, Usuario
from sqlalchemy.orm import joinedload, selectinload
from sqlalchemy import func
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
        
        # Query principal: peso e custo por classificação (usando custo_proporcional dos itens separados)
        resultados = db.session.query(
            ClassificacaoGrade.categoria,
            ClassificacaoGrade.nome,
            ClassificacaoGrade.id,
            db.func.sum(ItemSeparadoProducao.peso_kg).label('peso_total'),
            db.func.sum(ItemSeparadoProducao.custo_proporcional).label('custo_total')
        ).join(
            ItemSeparadoProducao.classificacao_grade
        ).join(
            ItemSeparadoProducao.bag
        ).filter(
            BagProducao.status.in_(bags_ativos)
        ).group_by(
            ClassificacaoGrade.categoria,
            ClassificacaoGrade.nome,
            ClassificacaoGrade.id
        ).all()
        
        # Estruturar resposta
        dados = {}
        for cat, classif_nome, classif_id, peso, custo in resultados:
            cat_key = cat or 'OUTROS'
            if cat_key not in dados:
                dados[cat_key] = {
                    'categoria': cat_key,
                    'peso_total': 0.0,
                    'total_valor': 0.0,
                    'classificacoes': []
                }
            
            p = float(peso or 0)
            c = float(custo or 0)
            
            dados[cat_key]['peso_total'] += p
            dados[cat_key]['total_valor'] += c
            
            # Dados da classificação
            classif_data = {
                'nome': classif_nome,
                'peso': p
            }
            
            if is_admin_or_gestor:
                # Calcular média de preço usando lógica "Media Ponderada Real": 
                # (Total Valor) / (Peso Total)
                media_preco = round(c / p, 2) if p > 0 else 0.0
                classif_data['media_preco'] = media_preco
                classif_data['total_valor'] = round(c, 2)
            
            dados[cat_key]['classificacoes'].append(classif_data)
            
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
            
            # Adicionar flag de admin/gestor e calcular média geral da categoria
            item['show_prices'] = is_admin_or_gestor
            if is_admin_or_gestor:
                # Média Geral da Categoria = (Total Valor) / (Peso Total da Categoria)
                item['media_geral'] = round(item['total_valor'] / item['peso_total'], 2) if item['peso_total'] > 0 else 0.0
            else:
                item['media_geral'] = 0.0
            
            lista_final.append(item)
            
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
        
        # Buscar IDs das tabelas de preço ativas
        tabelas_ativas_ids = [t.id for t in db.session.query(TabelaPreco.id).filter_by(ativo=True).all()]
        
        # Buscar todos os preços de tabela para os materiais retornados
        # Dicionário: material_id -> soma_precos_tabelas
        soma_precos_por_material = {}
        if tabelas_ativas_ids:
            precos_itens = db.session.query(
                TabelaPrecoItem.material_id,
                func.sum(TabelaPrecoItem.preco_por_kg)
            ).filter(
                TabelaPrecoItem.tabela_preco_id.in_(tabelas_ativas_ids),
                TabelaPrecoItem.ativo == True
            ).group_by(
                TabelaPrecoItem.material_id
            ).all()
            
            soma_precos_por_material = {pid: float(soma or 0) for pid, soma in precos_itens}

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
            
            # Cálculo específico solicitado pelo usuário para "Média R$":
            # (Valor Total Pago) / (Soma dos Preços das Tabelas Ativas)
            soma_tabelas = soma_precos_por_material.get(mat_id, 0.0)
            
            # Filtrar conforme solicitado: "somente os que tem valor atribuidos"
            # Se não tem preço de tabela, ignorar o item para não exibir média 0 ou causar ruído
            # UPDATE: Usuário quer ver os itens mesmo se High Grade vier vazio. 
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
                'soma_tabelas_debug': soma_tabelas # Para debug se necessário
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
                
                # Calcular média geral da categoria conforme fórmula correta:
                # Média Geral = (Valor Total) / (Peso Total da Categoria)
                # O valor total já está somado corretamente em item['total_valor']
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

