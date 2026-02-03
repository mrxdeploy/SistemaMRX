from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import db, Lote, LoteSeparacao, Residuo, Usuario, Notificacao, MovimentacaoEstoque
from app.auth import admin_required
from datetime import datetime
from decimal import Decimal

bp = Blueprint('separacao', __name__, url_prefix='/api/separacao')

def registrar_auditoria_separacao(separacao, acao, usuario_id, detalhes=None, gps=None, device_id=None):
    entrada_auditoria = {
        'acao': acao,
        'usuario_id': usuario_id,
        'timestamp': datetime.utcnow().isoformat(),
        'detalhes': detalhes or {},
        'ip': request.remote_addr,
        'user_agent': request.headers.get('User-Agent'),
        'gps': gps,
        'device_id': device_id
    }

    if separacao.auditoria is None:
        separacao.auditoria = []
    separacao.auditoria.append(entrada_auditoria)

@bp.route('/fila', methods=['GET'])
@jwt_required()
def obter_fila_separacao():
    try:
        usuario_id = get_jwt_identity()
        usuario = Usuario.query.get(usuario_id)

        if not usuario:
            return jsonify({'erro': 'Usuário não encontrado'}), 404

        perfil_nome = usuario.perfil.nome if usuario.perfil else None
        if perfil_nome not in ['Separação', 'Administrador', 'Producao', 'Produção'] and usuario.tipo != 'admin':
            return jsonify({'erro': 'Acesso negado. Apenas operadores de separação podem acessar a fila'}), 403

        status_filtro = request.args.get('status', 'AGUARDANDO_SEPARACAO')

        query = LoteSeparacao.query.filter_by(status=status_filtro)

        separacoes = query.order_by(LoteSeparacao.id).all()

        resultado = []
        for separacao in separacoes:
            separacao_dict = separacao.to_dict()

            if separacao.lote:
                # Incluir informações dos materiais/itens do lote
                itens_info = []
                for item in separacao.lote.itens:
                    item_info = {
                        'id': item.id,
                        'peso_kg': item.peso_kg,
                        'material_id': item.material_id,
                        'material_nome': item.material.nome if item.material else None,
                        'material_codigo': item.material.codigo if item.material else None,
                        'tipo_lote_id': item.tipo_lote_id,
                        'tipo_lote_nome': item.tipo_lote.nome if item.tipo_lote else None,
                        'estrelas_final': item.estrelas_final,
                        'classificacao': item.classificacao if item.classificacao else (item.material.classificacao if item.material else None)
                    }
                    itens_info.append(item_info)
                
                separacao_dict['lote_detalhes'] = {
                    'id': separacao.lote.id,
                    'numero_lote': separacao.lote.numero_lote,
                    'peso_total_kg': separacao.lote.peso_total_kg,
                    'peso_bruto_recebido': separacao.lote.peso_bruto_recebido,
                    'peso_liquido': separacao.lote.peso_liquido,
                    'qualidade_recebida': separacao.lote.qualidade_recebida,
                    'fornecedor_nome': separacao.lote.fornecedor.nome if separacao.lote.fornecedor else None,
                    'tipo_lote_nome': separacao.lote.tipo_lote.nome if separacao.lote.tipo_lote else None,
                    'conferente_nome': separacao.lote.conferente.nome if separacao.lote.conferente else None,
                    'data_criacao': separacao.lote.data_criacao.isoformat() if separacao.lote.data_criacao else None,
                    'anexos': separacao.lote.anexos,
                    'itens_info': itens_info
                }

            resultado.append(separacao_dict)

        return jsonify(resultado), 200

    except Exception as e:
        return jsonify({'erro': f'Erro ao obter fila de separação: {str(e)}'}), 500

@bp.route('/<int:id>/iniciar', methods=['POST'])
@jwt_required()
def iniciar_separacao(id):
    try:
        usuario_id = get_jwt_identity()
        usuario = Usuario.query.get(usuario_id)

        if not usuario:
            return jsonify({'erro': 'Usuário não encontrado'}), 404

        perfil_nome = usuario.perfil.nome if usuario.perfil else None
        if perfil_nome not in ['Separação', 'Administrador', 'Producao', 'Produção'] and usuario.tipo != 'admin':
            return jsonify({'erro': 'Acesso negado. Apenas operadores de separação podem iniciar separação'}), 403

        data = request.get_json() or {}

        separacao = LoteSeparacao.query.get(id)
        if not separacao:
            return jsonify({'erro': 'Separação não encontrada'}), 404

        if separacao.status != 'AGUARDANDO_SEPARACAO':
            return jsonify({'erro': f'Separação não pode ser iniciada. Status atual: {separacao.status}'}), 400

        separacao.status = 'EM_SEPARACAO'
        separacao.operador_id = usuario_id
        separacao.data_inicio = datetime.utcnow()
        separacao.gps_inicio = data.get('gps')
        separacao.ip_inicio = request.remote_addr
        separacao.device_id = data.get('device_id')

        registrar_auditoria_separacao(
            separacao, 
            'SEPARACAO_INICIADA', 
            usuario_id, 
            detalhes={'data_inicio': separacao.data_inicio.isoformat()},
            gps=data.get('gps'),
            device_id=data.get('device_id')
        )

        lote = separacao.lote
        if lote:
            lote.status = 'EM_SEPARACAO'

        db.session.commit()

        return jsonify({
            'mensagem': 'Separação iniciada com sucesso',
            'separacao': separacao.to_dict()
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': f'Erro ao iniciar separação: {str(e)}'}), 500

@bp.route('/<int:id>/sublotes', methods=['POST'])
@jwt_required()
def criar_sublote(id):
    try:
        usuario_id = get_jwt_identity()
        usuario_atual = Usuario.query.get(usuario_id)

        if not usuario_atual:
            return jsonify({'erro': 'Usuário não encontrado'}), 404

        perfil_nome = usuario_atual.perfil.nome if usuario_atual.perfil else None
        if perfil_nome not in ['Separação', 'Administrador', 'Producao', 'Produção'] and usuario_atual.tipo != 'admin':
            return jsonify({'erro': 'Acesso negado'}), 403

        data = request.get_json()

        if not data or not data.get('peso'):
            return jsonify({'erro': 'peso é obrigatório'}), 400

        if not data.get('material_id') and not data.get('tipo_lote_id') and not data.get('tipo_lote_nome'):
            return jsonify({'erro': 'material_id ou tipo_lote_id ou tipo_lote_nome é obrigatório'}), 400

        separacao = LoteSeparacao.query.get(id)
        if not separacao:
            return jsonify({'erro': 'Separação não encontrada'}), 404

        if separacao.status != 'EM_SEPARACAO':
            return jsonify({'erro': 'Separação não está em andamento'}), 400

        # Verificar se o operador que está criando o sublote é o mesmo que iniciou a separação
        # Admin pode criar sublotes em qualquer separação
        if usuario_atual.tipo != 'admin' and separacao.operador_id != usuario_atual.id:
            return jsonify({'erro': 'Apenas o operador que iniciou a separação pode criar sublotes'}), 403

        lote_pai = separacao.lote
        if not lote_pai:
            return jsonify({'erro': 'Lote pai não encontrado'}), 404

        peso_sublote = Decimal(str(data['peso']))
        peso_lote_pai = Decimal(str(lote_pai.peso_total_kg or lote_pai.peso_liquido or 1))
        valor_total_pai = Decimal(str(lote_pai.valor_total or 0))
        
        # Cálculo proporcional do valor para o sublote
        valor_sublote = Decimal('0')
        if peso_lote_pai > 0:
            valor_sublote = (peso_sublote / peso_lote_pai) * valor_total_pai
        
        # Arredondar para 2 casas decimais para evitar problemas de precisão
        valor_sublote = valor_sublote.quantize(Decimal('0.01'))
        
        # LOG DE DEBUG - MUITO IMPORTANTE
        print(f"DEBUG VALOR SUBLOTE: peso_sublote={peso_sublote}, peso_pai={peso_lote_pai}, valor_pai={valor_total_pai}, RESULTADO={valor_sublote}")

        ano = datetime.now().year
        numero_sequencial = Lote.query.filter(
            Lote.numero_lote.like(f"{ano}-%")  # type: ignore
        ).count() + 1
        numero_lote = f"{ano}-{str(numero_sequencial).zfill(5)}"

        tipo_lote_id = data.get('tipo_lote_id')
        tipo_lote_nome = data.get('tipo_lote_nome')
        material_nome = data.get('material_nome') or tipo_lote_nome

        # NOVO FLUXO: Se material_id foi fornecido, usar para buscar um TipoLote correspondente
        if data.get('material_id'):
            from app.models import TipoLote, MaterialBase
            material = MaterialBase.query.get(data['material_id'])
            if material:
                material_nome = material.nome
                # Tenta encontrar um TipoLote com o mesmo nome do material
                tipo_lote = TipoLote.query.filter_by(nome=material.nome).first()
                if tipo_lote:
                    tipo_lote_id = tipo_lote.id
                else:
                    # Buscar tipo genérico como fallback
                    generico = TipoLote.query.filter(TipoLote.nome.ilike('%generico%')).first() or \
                               TipoLote.query.filter(TipoLote.nome.ilike('%outros%')).first()
                    if generico:
                        tipo_lote_id = generico.id
                    else:
                        tipo_lote_id = lote_pai.tipo_lote_id
            else:
                return jsonify({'erro': f'Material com ID {data["material_id"]} não encontrado'}), 404

        # FLUXO LEGADO: Se for material manual, tenta encontrar ou criar o tipo de material
        elif data.get('is_manual') and tipo_lote_nome:
            from app.models import TipoLote
            tipo_lote = TipoLote.query.filter_by(nome=tipo_lote_nome).first()
            if tipo_lote:
                tipo_lote_id = tipo_lote.id
            else:
                # Opcional: Criar um novo tipo de lote se não existir
                # Por enquanto, se não encontrar e for manual, vamos garantir que o ID não sobrescreva o nome depois
                pass

        # Se não informou ID mas informou nome, tenta encontrar
        if not tipo_lote_id and tipo_lote_nome:
            from app.models import TipoLote
            tipo_lote = TipoLote.query.filter_by(nome=tipo_lote_nome).first()
            if tipo_lote:
                tipo_lote_id = tipo_lote.id
        
        # Se ainda assim estiver nulo e NÃO for manual, tenta usar o tipo do lote pai
        if not tipo_lote_id and not data.get('is_manual') and not data.get('material_id'):
            tipo_lote_id = lote_pai.tipo_lote_id

        # Se for manual e ainda não tiver ID, precisamos de um ID válido para o modelo Lote
        # Vamos buscar um tipo de lote "Genérico" ou "Outros" se existir, ou usar o do pai como fallback técnico
        if not tipo_lote_id and (data.get('is_manual') or data.get('material_id')):
            # Tenta buscar um tipo genérico primeiro
            from app.models import TipoLote
            generico = TipoLote.query.filter(TipoLote.nome.ilike('%generico%')).first() or \
                       TipoLote.query.filter(TipoLote.nome.ilike('%outros%')).first()
            if generico:
                tipo_lote_id = generico.id
            else:
                tipo_lote_id = lote_pai.tipo_lote_id

        if not tipo_lote_id:
            return jsonify({'erro': 'Não foi possível determinar o tipo do lote (tipo_lote_id ausente)'}), 400

        sublote = Lote(
            numero_lote=numero_lote,
            fornecedor_id=lote_pai.fornecedor_id,
            tipo_lote_id=tipo_lote_id,
            peso_total_kg=float(peso_sublote),
            valor_total=float(valor_sublote),
            qualidade_recebida=data.get('qualidade'),
            status='CRIADO_SEPARACAO',
            lote_pai_id=lote_pai.id,  # Vincula ao lote pai
            quantidade_itens=data.get('quantidade', 1),
            observacoes=f"MATERIAL:{material_nome} | {data.get('observacoes', '')}" if material_nome else data.get('observacoes', ''),
            anexos=data.get('fotos', []),
            auditoria=[{
                'acao': 'SUBLOTE_CRIADO_NA_SEPARACAO',
                'usuario_id': usuario_id,
                'timestamp': datetime.utcnow().isoformat(),
                'ip': request.remote_addr,
                'user_agent': request.headers.get('User-Agent'),
                'gps': data.get('gps'),
                'device_id': data.get('device_id') or separacao.device_id,
                'separacao_id': separacao.id,
                'lote_pai_id': lote_pai.id,
                'lote_pai_numero': lote_pai.numero_lote,
                'valor_proporcional': float(valor_sublote)
            }],
            data_criacao=datetime.utcnow()
        )

        db.session.add(sublote)
        db.session.flush()  # Garantir que o sublote seja criado antes de continuar
        
        print(f'\n✅ Sublote criado: {sublote.numero_lote} (ID: {sublote.id})')
        print(f'   Lote pai: {lote_pai.numero_lote} (ID: {lote_pai.id})')
        print(f'   Campo lote_pai_id: {sublote.lote_pai_id}')

        separacao.peso_total_sublotes = (separacao.peso_total_sublotes or 0) + data['peso']

        registrar_auditoria_separacao(
            separacao, 
            'SUBLOTE_CRIADO', 
            usuario_id, 
            detalhes={
                'sublote_numero': numero_lote,
                'peso': data['peso'],
                'tipo_lote_id': tipo_lote_id,
                'tipo_lote_nome': data.get('tipo_lote_nome')
            },
            gps=data.get('gps'),
            device_id=data.get('device_id') or separacao.device_id
        )

        db.session.commit()

        return jsonify({
            'mensagem': 'Sublote criado com sucesso',
            'sublote': sublote.to_dict()
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': f'Erro ao criar sublote: {str(e)}'}), 500

@bp.route('/<int:id>/residuos', methods=['POST'])
@jwt_required()
def criar_residuo(id):
    try:
        usuario_id = get_jwt_identity()
        usuario_atual = Usuario.query.get(usuario_id)

        if not usuario_atual:
            return jsonify({'erro': 'Usuário não encontrado'}), 404

        perfil_nome = usuario_atual.perfil.nome if usuario_atual.perfil else None
        if perfil_nome not in ['Separação', 'Administrador', 'Producao', 'Produção'] and usuario_atual.tipo != 'admin':
            return jsonify({'erro': 'Acesso negado'}), 403

        data = request.get_json()

        if not data or not data.get('peso') or not data.get('material') or not data.get('justificativa'):
            return jsonify({'erro': 'peso, material e justificativa são obrigatórios'}), 400

        separacao = LoteSeparacao.query.get(id)
        if not separacao:
            return jsonify({'erro': 'Separação não encontrada'}), 404

        if separacao.status != 'EM_SEPARACAO':
            return jsonify({'erro': 'Separação não está em andamento'}), 400

        # Verificar se o operador que está criando o resíduo é o mesmo que iniciou a separação
        # Admin pode criar resíduos em qualquer separação
        if usuario_atual.tipo != 'admin' and separacao.operador_id != usuario_atual.id:
            return jsonify({'erro': 'Apenas o operador que iniciou a separação pode criar resíduos'}), 403

        residuo = Residuo(
            separacao_id=separacao.id,
            material=data['material'],
            peso=data['peso'],
            quantidade=data.get('quantidade'),
            classificacao=data.get('classificacao'),
            justificativa=data['justificativa'],
            fotos=data.get('fotos', []),
            status='AGUARDANDO_APROVACAO',
            auditoria=[{
                'acao': 'RESIDUO_CRIADO',
                'usuario_id': usuario_id,
                'timestamp': datetime.utcnow().isoformat(),
                'ip': request.remote_addr,
                'user_agent': request.headers.get('User-Agent'),
                'gps': data.get('gps'),
                'device_id': data.get('device_id') or separacao.device_id
            }],
            criado_em=datetime.utcnow()
        )

        db.session.add(residuo)

        separacao.peso_total_residuos = (separacao.peso_total_residuos or 0) + data['peso']

        registrar_auditoria_separacao(
            separacao, 
            'RESIDUO_CRIADO', 
            usuario_id, 
            detalhes={
                'material': data['material'],
                'peso': data['peso'],
                'justificativa': data['justificativa']
            },
            gps=data.get('gps'),
            device_id=data.get('device_id') or separacao.device_id
        )

        admins = Usuario.query.filter_by(tipo='admin').all()
        for admin in admins:
            notificacao = Notificacao(
                usuario_id=admin.id,
                titulo='Novo Resíduo Aguardando Aprovação',
                mensagem=f'Resíduo de {data["peso"]}kg ({data["material"]}) precisa de aprovação para descarte',
                tipo='residuo_aprovacao',
                url='/residuos-aprovacao.html',
                lida=False
            )
            db.session.add(notificacao)

        db.session.commit()

        return jsonify({
            'mensagem': 'Resíduo registrado com sucesso',
            'residuo': residuo.to_dict()
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': f'Erro ao criar resíduo: {str(e)}'}), 500

@bp.route('/<int:id>/finalizar', methods=['POST'])
@jwt_required()
def finalizar_separacao(id):
    try:
        usuario_id = get_jwt_identity()
        usuario_atual = Usuario.query.get(usuario_id)

        if not usuario_atual:
            return jsonify({'erro': 'Usuário não encontrado'}), 404

        perfil_nome = usuario_atual.perfil.nome if usuario_atual.perfil else None
        if perfil_nome not in ['Separação', 'Administrador', 'Producao', 'Produção'] and usuario_atual.tipo != 'admin':
            return jsonify({'erro': 'Acesso negado'}), 403

        data = request.get_json() or {}

        separacao = LoteSeparacao.query.get(id)
        if not separacao:
            return jsonify({'erro': 'Separação não encontrada'}), 404

        if separacao.status != 'EM_SEPARACAO':
            return jsonify({'erro': 'Separação não está em andamento'}), 400

        # Verificar se o operador que está finalizando é o mesmo que iniciou a separação
        # Admin pode finalizar qualquer separação
        if usuario_atual.tipo != 'admin' and separacao.operador_id != usuario_atual.id:
            return jsonify({'erro': 'Apenas o operador que iniciou a separação pode finalizá-la'}), 403

        lote_pai = separacao.lote
        if not lote_pai:
            return jsonify({'erro': 'Lote pai não encontrado'}), 404

        residuos_pendentes = Residuo.query.filter_by(
            separacao_id=separacao.id,
            status='AGUARDANDO_APROVACAO'
        ).count()

        if residuos_pendentes > 0:
            return jsonify({'erro': f'Existem {residuos_pendentes} resíduos aguardando aprovação. Finalize todos antes de concluir a separação'}), 400

        peso_total_processado = (separacao.peso_total_sublotes or 0) + (separacao.peso_total_residuos or 0)
        peso_lote = lote_pai.peso_total_kg or lote_pai.peso_liquido or 0

        if peso_lote > 0:
            percentual = (peso_total_processado / peso_lote) * 100
            separacao.percentual_aproveitamento = percentual

        separacao.status = 'FINALIZADA'
        separacao.data_finalizacao = datetime.utcnow()
        separacao.gps_fim = data.get('gps')
        separacao.observacoes = data.get('observacoes', '')

        lote_pai.status = 'PROCESSADO'

        registrar_auditoria_separacao(
            separacao, 
            'SEPARACAO_FINALIZADA', 
            usuario_id, 
            detalhes={
                'peso_total_sublotes': separacao.peso_total_sublotes,
                'peso_total_residuos': separacao.peso_total_residuos,
                'percentual_aproveitamento': separacao.percentual_aproveitamento,
                'data_finalizacao': separacao.data_finalizacao.isoformat()
            },
            gps=data.get('gps'),
            device_id=separacao.device_id
        )

        db.session.commit()

        return jsonify({
            'mensagem': 'Separação finalizada com sucesso',
            'separacao': separacao.to_dict(),
            'percentual_aproveitamento': separacao.percentual_aproveitamento
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': f'Erro ao finalizar separação: {str(e)}'}), 500

@bp.route('/residuos/<int:id>/aprovar-adm', methods=['POST'])
@admin_required
def aprovar_residuo(id):
    try:
        usuario_id = get_jwt_identity()
        data = request.get_json()

        if not data or not data.get('decisao'):
            return jsonify({'erro': 'decisao é obrigatória (APROVAR ou REJEITAR)'}), 400

        residuo = Residuo.query.get(id)
        if not residuo:
            return jsonify({'erro': 'Resíduo não encontrado'}), 404

        if residuo.status != 'AGUARDANDO_APROVACAO':
            return jsonify({'erro': 'Resíduo não está aguardando aprovação'}), 400

        decisao = data['decisao'].upper()
        if decisao not in ['APROVAR', 'REJEITAR']:
            return jsonify({'erro': 'Decisão inválida'}), 400

        residuo.status = 'APROVADO' if decisao == 'APROVAR' else 'REJEITADO'
        residuo.aprovado_por_id = usuario_id
        residuo.data_aprovacao = datetime.utcnow()
        residuo.motivo_decisao = data.get('motivo', '')

        if residuo.auditoria is None:
            residuo.auditoria = []
        residuo.auditoria.append({
            'acao': f'RESIDUO_{decisao}',
            'usuario_id': usuario_id,
            'timestamp': datetime.utcnow().isoformat(),
            'ip': request.remote_addr,
            'motivo': data.get('motivo', '')
        })

        if residuo.separacao and residuo.separacao.operador_id:
            notificacao = Notificacao(
                usuario_id=residuo.separacao.operador_id,
                titulo=f'Resíduo {decisao.title()}',
                mensagem=f'O resíduo de {residuo.peso}kg ({residuo.material}) foi {decisao.lower()} pelo administrador',
                tipo='residuo_decisao',
                url='/residuos-aprovacao.html',
                lida=False
            )
            db.session.add(notificacao)

        db.session.commit()

        return jsonify({
            'mensagem': f'Resíduo {decisao.lower()} com sucesso',
            'residuo': residuo.to_dict()
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': f'Erro ao aprovar resíduo: {str(e)}'}), 500

@bp.route('/residuos', methods=['GET'])
@admin_required
def listar_residuos():
    try:
        status = request.args.get('status', 'AGUARDANDO_APROVACAO')

        print(f'\n🔍 API /residuos - status={status}')
        
        # Se status='all', buscar todos os resíduos, caso contrário filtrar por status
        if status and status.lower() == 'all':
            query = Residuo.query
        else:
            query = Residuo.query.filter_by(status=status)
            
        residuos = query.order_by(Residuo.criado_em.desc()).all()
        
        print(f'   Total de resíduos encontrados: {len(residuos)}')

        resultado = []
        for residuo in residuos:
            residuo_dict = residuo.to_dict()

            if residuo.separacao and residuo.separacao.lote:
                residuo_dict['lote_numero'] = residuo.separacao.lote.numero_lote
                residuo_dict['operador_nome'] = residuo.separacao.operador.nome if residuo.separacao.operador else None

            resultado.append(residuo_dict)
        
        print(f'   Retornando {len(resultado)} resíduos')

        return jsonify(resultado), 200

    except Exception as e:
        return jsonify({'erro': f'Erro ao listar resíduos: {str(e)}'}), 500

@bp.route('/<int:separacao_id>/residuos', methods=['GET'])
@jwt_required()
def obter_residuos_separacao(separacao_id):
    """Endpoint específico para buscar apenas os resíduos de uma separação"""
    try:
        separacao = LoteSeparacao.query.get(separacao_id)
        if not separacao:
            return jsonify({'erro': 'Separação não encontrada'}), 404

        # Buscar apenas resíduos desta separação
        residuos = Residuo.query.filter_by(separacao_id=separacao_id).order_by(Residuo.criado_em.desc()).all()
        
        print(f'\n🔍 API /separacao/{separacao_id}/residuos')
        print(f'   Total de resíduos encontrados: {len(residuos)}')

        resultado = []
        for residuo in residuos:
            residuo_dict = residuo.to_dict()
            if separacao.lote:
                residuo_dict['lote_numero'] = separacao.lote.numero_lote
            if separacao.operador:
                residuo_dict['operador_nome'] = separacao.operador.nome
            resultado.append(residuo_dict)

        return jsonify(resultado), 200

    except Exception as e:
        return jsonify({'erro': f'Erro ao obter resíduos: {str(e)}'}), 500

@bp.route('/estatisticas', methods=['GET'])
@jwt_required()
def obter_estatisticas_separacao():
    try:
        total_separacoes = LoteSeparacao.query.count()
        aguardando = LoteSeparacao.query.filter_by(status='AGUARDANDO_SEPARACAO').count()
        em_andamento = LoteSeparacao.query.filter_by(status='EM_SEPARACAO').count()
        finalizadas = LoteSeparacao.query.filter_by(status='FINALIZADA').count()

        residuos_pendentes = Residuo.query.filter_by(status='AGUARDANDO_APROVACAO').count()
        residuos_aprovados = Residuo.query.filter_by(status='APROVADO').count()
        residuos_rejeitados = Residuo.query.filter_by(status='REJEITADO').count()

        return jsonify({
            'total_separacoes': total_separacoes,
            'aguardando_separacao': aguardando,
            'em_separacao': em_andamento,
            'finalizadas': finalizadas,
            'residuos_pendentes': residuos_pendentes,
            'residuos_aprovados': residuos_aprovados,
            'residuos_rejeitados': residuos_rejeitados
        }), 200

    except Exception as e:
        return jsonify({'erro': f'Erro ao obter estatísticas: {str(e)}'}), 500

@bp.route('/<int:id>/sync-sublotes', methods=['POST'])
@jwt_required()
def sincronizar_sublotes(id):
    """
    Sincroniza os sublotes com os itens do lote original (Pedido de Compra).
    Se não houver sublotes criados, cria automaticamente baseado nos itens do lote.
    """
    try:
        usuario_id = get_jwt_identity()
        separacao = LoteSeparacao.query.get(id)
        
        if not separacao:
            return jsonify({'erro': 'Separação não encontrada'}), 404
            
        if separacao.status not in ['AGUARDANDO_SEPARACAO', 'EM_SEPARACAO']:
             return jsonify({'erro': 'Status inválido para sincronização'}), 400

        lote_pai = separacao.lote
        if not lote_pai:
             return jsonify({'erro': 'Lote pai não encontrado'}), 404

        # Se já existem sublotes, verificar e corrigir qualidade se necessário (migração de dados em tempo real)
        sublotes_existentes_query = Lote.query.filter_by(lote_pai_id=lote_pai.id)
        sublotes_db = sublotes_existentes_query.all()
        
        if sublotes_db:
            correcoes = 0
            for sub in sublotes_db:
                # Se qualidade for uma classificação legacy ou vazia, força 'A'
                if sub.qualidade_recebida not in ['A', 'B', 'C']:
                    sub.qualidade_recebida = 'A'
                    correcoes += 1
            
            if correcoes > 0:
                db.session.commit()
                return jsonify({'mensagem': f'Qualidade corrigida em {correcoes} sublotes existentes.', 'sincronizado': True}), 200
            
            return jsonify({'mensagem': 'Sublotes já existem e estão corretos.', 'sincronizado': False}), 200

        # Buscar itens do lote (que vieram do Pedido de Compra ou Entrada Manual)
        # Se o lote tem itens, usamos eles.
        itens = lote_pai.itens
        
        if not itens:
             return jsonify({'mensagem': 'Lote não possui itens para sincronizar.', 'sincronizado': False}), 200

        novos_sublotes = []
        peso_total_criado = 0.0

        ano = datetime.now().year
        
        # Para sequencia do numero do lote, vamos pegar o count atual
        count_lotes = Lote.query.filter(Lote.numero_lote.like(f"{ano}-%")).count()

        for i, item in enumerate(itens):
            count_lotes += 1
            numero_lote = f"{ano}-{str(count_lotes).zfill(5)}"
            
            # Tenta determinar o tipo de lote
            tipo_lote_id = item.tipo_lote_id
            if not tipo_lote_id and item.material:
                # Tenta achar TipoLote pelo material, como feito na criação manual
                from app.models import TipoLote
                tipo = TipoLote.query.filter_by(nome=item.material.nome).first()
                if tipo:
                    tipo_lote_id = tipo.id
            
            if not tipo_lote_id:
                tipo_lote_id = lote_pai.tipo_lote_id # Fallback para o tipo do pai

            # Calcular valor proporcional
            peso_item = Decimal(str(item.peso_kg))
            peso_pai = Decimal(str(lote_pai.peso_total_kg or 1))
            valor_pai = Decimal(str(lote_pai.valor_total or 0))
            valor_proporcional = (peso_item / peso_pai) * valor_pai if peso_pai > 0 else Decimal(0)
            
            sublote = Lote(
                numero_lote=numero_lote,
                fornecedor_id=lote_pai.fornecedor_id,
                tipo_lote_id=tipo_lote_id,
                peso_total_kg=float(peso_item),
                valor_total=float(valor_proporcional),
                qualidade_recebida='A', # Default fixo 'A' conforme solicitado
                status='CRIADO_SEPARACAO',
                lote_pai_id=lote_pai.id,
                quantidade_itens=1,
                observacoes=f"MATERIAL:{item.material.nome}" if item.material else f"Item importado do lote {lote_pai.numero_lote}",
                auditoria=[{
                    'acao': 'SUBLOTE_AUTO_CRIADO',
                    'usuario_id': usuario_id,
                    'timestamp': datetime.utcnow().isoformat(),
                    'origem': 'SYNC_PEDIDO_COMPRA'
                }],
                data_criacao=datetime.utcnow()
            )
            
            db.session.add(sublote)
            novos_sublotes.append(sublote)
            peso_total_criado += float(peso_item)

        separacao.peso_total_sublotes = (separacao.peso_total_sublotes or 0) + peso_total_criado
        
        db.session.commit()
        
        return jsonify({
            'mensagem': f'{len(novos_sublotes)} sublotes criados automaticamente.',
            'sincronizado': True,
            'sublotes_criados': len(novos_sublotes)
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': f'Erro ao sincronizar sublotes: {str(e)}'}), 500

@bp.route('/sublotes/<int:id>', methods=['PUT'])
@jwt_required()
def editar_sublote(id):
    try:
        usuario_id = get_jwt_identity()
        data = request.get_json()
        
        sublote = Lote.query.get(id)
        if not sublote:
            return jsonify({'erro': 'Sublote não encontrado'}), 404
            
        # Verifica se é um sublote (tem pai)
        if not sublote.lote_pai_id:
             return jsonify({'erro': 'Este lote não é um sublote'}), 400

        # Atualiza campos
        peso_anterior = sublote.peso_total_kg
        
        if 'peso' in data:
            sublote.peso_total_kg = float(data['peso'])
            
            # Recalcula valor proporcional se o peso mudou
            if sublote.lote_pai:
                peso_pai = Decimal(str(sublote.lote_pai.peso_total_kg or 1))
                valor_pai = Decimal(str(sublote.lote_pai.valor_total or 0))
                novo_peso = Decimal(str(sublote.peso_total_kg))
                novo_valor = (novo_peso / peso_pai) * valor_pai if peso_pai > 0 else Decimal(0)
                sublote.valor_total = float(novo_valor)

        if 'qualidade' in data:
            sublote.qualidade_recebida = data['qualidade']
            
        if 'observacoes' in data:
             # Preserva prefixo de material se existir e não for sobrescrito intencionalmente
             # Aqui vamos assumir que a edição manda o texto completo ou tratamos
             sublote.observacoes = data['observacoes']

        # Atualiza peso total na separação
        separacao = LoteSeparacao.query.filter_by(lote_id=sublote.lote_pai_id).first()
        if separacao:
            # Recalcular peso total dos sublotes
            # Esta query soma todos os sublotes do pai, garantindo consistência
            total_sublotes = db.session.query(db.func.sum(Lote.peso_total_kg)).filter(Lote.lote_pai_id == sublote.lote_pai_id).scalar() or 0
            separacao.peso_total_sublotes = float(total_sublotes)

        # Auditoria
        auditoria = sublote.auditoria or []
        auditoria.append({
            'acao': 'EDICAO_SUBLOTE',
            'usuario_id': usuario_id,
            'timestamp': datetime.utcnow().isoformat(),
            'alteracoes': data
        })
        sublote.auditoria = auditoria

        db.session.commit()
        
        return jsonify({'mensagem': 'Sublote atualizado com sucesso', 'sublote': sublote.to_dict()}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': f'Erro ao editar sublote: {str(e)}'}), 500

@bp.route('/sublotes/<int:id>', methods=['DELETE'])
@jwt_required()
def excluir_sublote(id):
    try:
        usuario_id = get_jwt_identity()
        
        sublote = Lote.query.get(id)
        if not sublote:
            return jsonify({'erro': 'Sublote não encontrado'}), 404
            
        if not sublote.lote_pai_id:
             return jsonify({'erro': 'Este lote não é um sublote'}), 400
             
        # Guarda ID do pai para atualizar separação
        lote_pai_id = sublote.lote_pai_id
        
        # Remove do banco
        db.session.delete(sublote)
        
        # Commit parcial para efetivar deleção antes de recalcular
        db.session.flush()

        # Atualiza peso total na separação
        separacao = LoteSeparacao.query.filter_by(lote_id=lote_pai_id).first()
        if separacao:
            total_sublotes = db.session.query(db.func.sum(Lote.peso_total_kg)).filter(Lote.lote_pai_id == lote_pai_id).scalar() or 0
            separacao.peso_total_sublotes = float(total_sublotes)
            
        db.session.commit()
        
        return jsonify({'mensagem': 'Sublote excluído com sucesso'}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': f'Erro ao excluir sublote: {str(e)}'}), 500