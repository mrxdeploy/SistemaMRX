from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import db, OrdemServico, OrdemCompra, Fornecedor, Motorista, Veiculo, Usuario, Notificacao, GPSLog, ConferenciaRecebimento
from app.auth import admin_required
from datetime import datetime

bp = Blueprint('ordens_servico', __name__)

def gerar_numero_os():
    import uuid
    timestamp = datetime.now().strftime('%Y%m%d')
    random_str = uuid.uuid4().hex[:6].upper()
    return f"OS-{timestamp}-{random_str}"

def criar_snapshot_fornecedor(fornecedor):
    return {
        'id': fornecedor.id,
        'nome': fornecedor.nome,
        'cnpj': fornecedor.cnpj if hasattr(fornecedor, 'cnpj') else None,
        'endereco': fornecedor.endereco if hasattr(fornecedor, 'endereco') else None,
        'cidade': fornecedor.cidade if hasattr(fornecedor, 'cidade') else None,
        'estado': fornecedor.estado if hasattr(fornecedor, 'estado') else None,
        'telefone': fornecedor.telefone if hasattr(fornecedor, 'telefone') else None,
    }

def registrar_auditoria_os(os, acao, usuario_id, detalhes=None):
    entrada_auditoria = {
        'acao': acao,
        'usuario_id': usuario_id,
        'timestamp': datetime.utcnow().isoformat(),
        'detalhes': detalhes or {},
        'ip': request.remote_addr,
        'user_agent': request.headers.get('User-Agent')
    }
    
    if os.auditoria is None:
        os.auditoria = []
    os.auditoria.append(entrada_auditoria)

@bp.route('', methods=['GET'])
@jwt_required()
def listar_os():
    try:
        usuario_id = get_jwt_identity()
        usuario = Usuario.query.get(usuario_id)
        
        if not usuario:
            return jsonify({'erro': 'Usuário não encontrado'}), 404
        
        query = OrdemServico.query
        
        status = request.args.get('status')
        if status:
            query = query.filter_by(status=status)
        
        motorista_id = request.args.get('motorista_id', type=int)
        if motorista_id:
            query = query.filter_by(motorista_id=motorista_id)
        
        data_inicio = request.args.get('data_inicio')
        if data_inicio:
            query = query.filter(OrdemServico.criado_em >= datetime.fromisoformat(data_inicio))
        
        data_fim = request.args.get('data_fim')
        if data_fim:
            query = query.filter(OrdemServico.criado_em <= datetime.fromisoformat(data_fim))
        
        oc_id = request.args.get('oc_id', type=int)
        if oc_id:
            query = query.filter_by(oc_id=oc_id)
        
        perfil_nome = usuario.perfil.nome if usuario.perfil else None
        
        if perfil_nome == 'Motorista' or usuario.tipo == 'motorista':
            motorista = Motorista.query.filter_by(usuario_id=usuario_id).first()
            if motorista:
                query = query.filter_by(motorista_id=motorista.id)
            else:
                return jsonify([]), 200
        
        os_list = query.order_by(OrdemServico.criado_em.desc()).all()
        
        return jsonify([os.to_dict() for os in os_list]), 200
    
    except Exception as e:
        return jsonify({'erro': f'Erro ao listar OS: {str(e)}'}), 500

@bp.route('/<int:id>', methods=['GET'])
@jwt_required()
def obter_os(id):
    try:
        usuario_id = get_jwt_identity()
        usuario = Usuario.query.get(usuario_id)
        
        os = OrdemServico.query.get(id)
        
        if not os:
            return jsonify({'erro': 'Ordem de Serviço não encontrada'}), 404
        
        perfil_nome = usuario.perfil.nome if usuario.perfil else None
        if perfil_nome == 'Motorista' or usuario.tipo == 'motorista':
            motorista = Motorista.query.filter_by(usuario_id=usuario_id).first()
            if not motorista or os.motorista_id != motorista.id:
                return jsonify({'erro': 'Acesso negado'}), 403
        
        os_dict = os.to_dict()
        
        os_dict['ordem_compra'] = os.ordem_compra.to_dict() if os.ordem_compra else None
        os_dict['gps_eventos'] = [gps.to_dict() for gps in os.eventos_gps]
        os_dict['rotas'] = [rota.to_dict() for rota in os.rotas_operacionais]
        
        return jsonify(os_dict), 200
    
    except Exception as e:
        return jsonify({'erro': f'Erro ao obter OS: {str(e)}'}), 500

@bp.route('/oc/<int:oc_id>/gerar', methods=['POST'])
@admin_required
def gerar_os_da_oc(oc_id):
    try:
        usuario_id = get_jwt_identity()
        
        oc = OrdemCompra.query.get(oc_id)
        
        if not oc:
            return jsonify({'erro': 'Ordem de Compra não encontrada'}), 404
        
        if oc.status != 'aprovada':
            return jsonify({'erro': 'Apenas OCs aprovadas podem gerar OS'}), 400
        
        os_existente = OrdemServico.query.filter_by(oc_id=oc_id).first()
        if os_existente:
            return jsonify({'erro': 'Já existe uma OS para esta OC', 'os': os_existente.to_dict()}), 400
        
        fornecedor = Fornecedor.query.get(oc.fornecedor_id)
        if not fornecedor:
            return jsonify({'erro': 'Fornecedor não encontrado'}), 404
        
        numero_os = gerar_numero_os()
        fornecedor_snap = criar_snapshot_fornecedor(fornecedor)
        
        data = request.get_json() or {}
        
        os = OrdemServico(
            oc_id=oc_id,
            numero_os=numero_os,
            fornecedor_snapshot=fornecedor_snap,
            tipo=data.get('tipo', 'COLETA'),
            janela_coleta_inicio=datetime.fromisoformat(data['janela_coleta_inicio']) if data.get('janela_coleta_inicio') else None,
            janela_coleta_fim=datetime.fromisoformat(data['janela_coleta_fim']) if data.get('janela_coleta_fim') else None,
            rota=data.get('rota'),
            status='PENDENTE',
            created_by=usuario_id
        )
        
        db.session.add(os)
        registrar_auditoria_os(os, 'CRIACAO', usuario_id, {
            'oc_id': oc_id,
            'fornecedor': fornecedor.nome
        })
        
        db.session.commit()
        
        return jsonify({
            'mensagem': 'Ordem de Serviço criada com sucesso',
            'os': os.to_dict()
        }), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': f'Erro ao gerar OS: {str(e)}'}), 500

@bp.route('/<int:id>/atribuir-motorista', methods=['PUT'])
@admin_required
def atribuir_motorista(id):
    try:
        usuario_id = get_jwt_identity()
        data = request.get_json()
        
        if not data or not data.get('motorista_id'):
            return jsonify({'erro': 'motorista_id é obrigatório'}), 400
        
        os = OrdemServico.query.get(id)
        if not os:
            return jsonify({'erro': 'Ordem de Serviço não encontrada'}), 404
        
        motorista = Motorista.query.get(data['motorista_id'])
        if not motorista:
            return jsonify({'erro': 'Motorista não encontrado'}), 404
        
        veiculo_id = data.get('veiculo_id')
        if veiculo_id:
            veiculo = Veiculo.query.get(veiculo_id)
            if not veiculo:
                return jsonify({'erro': 'Veículo não encontrado'}), 404
            os.veiculo_id = veiculo_id
        
        os.motorista_id = data['motorista_id']
        os.status = 'AGENDADA'
        
        registrar_auditoria_os(os, 'ATRIBUICAO_MOTORISTA', usuario_id, {
            'motorista_id': data['motorista_id'],
            'motorista_nome': motorista.usuario.nome if motorista.usuario else None,
            'veiculo_id': veiculo_id
        })
        
        notificacao = Notificacao(
            usuario_id=motorista.usuario_id,
            titulo='Nova Ordem de Serviço Atribuída',
            mensagem=f'Você foi atribuído à OS {os.numero_os}. Fornecedor: {os.fornecedor_snapshot.get("nome", "N/A")}',
            url='/logistica.html',
            lida=False
        )
        db.session.add(notificacao)
        
        db.session.commit()
        
        return jsonify({
            'mensagem': 'Motorista atribuído com sucesso',
            'os': os.to_dict()
        }), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': f'Erro ao atribuir motorista: {str(e)}'}), 500

@bp.route('/<int:id>/reagendar', methods=['POST'])
@admin_required
def reagendar_os(id):
    try:
        usuario_id = get_jwt_identity()
        data = request.get_json()
        
        if not data or not data.get('janela_coleta_inicio') or not data.get('motivo'):
            return jsonify({'erro': 'janela_coleta_inicio e motivo são obrigatórios'}), 400
        
        os = OrdemServico.query.get(id)
        if not os:
            return jsonify({'erro': 'Ordem de Serviço não encontrada'}), 404
        
        janela_antiga_inicio = os.janela_coleta_inicio
        janela_antiga_fim = os.janela_coleta_fim
        
        os.janela_coleta_inicio = datetime.fromisoformat(data['janela_coleta_inicio'])
        if data.get('janela_coleta_fim'):
            os.janela_coleta_fim = datetime.fromisoformat(data['janela_coleta_fim'])
        
        registrar_auditoria_os(os, 'REAGENDAMENTO', usuario_id, {
            'motivo': data['motivo'],
            'janela_antiga_inicio': janela_antiga_inicio.isoformat() if janela_antiga_inicio else None,
            'janela_antiga_fim': janela_antiga_fim.isoformat() if janela_antiga_fim else None,
            'janela_nova_inicio': os.janela_coleta_inicio.isoformat(),
            'janela_nova_fim': os.janela_coleta_fim.isoformat() if os.janela_coleta_fim else None
        })
        
        if os.motorista and os.motorista.usuario_id:
            notificacao = Notificacao(
                usuario_id=os.motorista.usuario_id,
                titulo='OS Reagendada',
                mensagem=f'A OS {os.numero_os} foi reagendada. Motivo: {data["motivo"]}',
                url='/logistica.html',
                lida=False
            )
            db.session.add(notificacao)
        
        db.session.commit()
        
        return jsonify({
            'mensagem': 'OS reagendada com sucesso',
            'os': os.to_dict()
        }), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': f'Erro ao reagendar OS: {str(e)}'}), 500

@bp.route('/<int:id>/iniciar-rota', methods=['PUT'])
@jwt_required()
def iniciar_rota(id):
    try:
        usuario_id = get_jwt_identity()
        usuario = Usuario.query.get(usuario_id)
        data = request.get_json() or {}
        
        if not data.get('gps'):
            return jsonify({'erro': 'GPS é obrigatório para iniciar rota'}), 400
        
        os = OrdemServico.query.get(id)
        if not os:
            return jsonify({'erro': 'Ordem de Serviço não encontrada'}), 404
        
        motorista = Motorista.query.filter_by(usuario_id=usuario_id).first()
        if not motorista or os.motorista_id != motorista.id:
            return jsonify({'erro': 'Apenas o motorista atribuído pode iniciar a rota'}), 403
        
        if os.status not in ['AGENDADA', 'PENDENTE']:
            return jsonify({'erro': f'OS não pode ser iniciada no status {os.status}'}), 400
        
        os.status = 'EM_ROTA'
        
        gps_log = GPSLog(
            os_id=os.id,
            evento='INICIO_ROTA',
            latitude=data['gps']['latitude'],
            longitude=data['gps']['longitude'],
            precisao=data['gps'].get('precisao'),
            device_id=data.get('device_id'),
            ip=request.remote_addr,
            dados_adicionais=data.get('dados_adicionais')
        )
        db.session.add(gps_log)
        
        registrar_auditoria_os(os, 'INICIO_ROTA', usuario_id, {
            'gps': data['gps'],
            'device_id': data.get('device_id')
        })
        
        db.session.commit()
        
        return jsonify({
            'mensagem': 'Rota iniciada com sucesso',
            'os': os.to_dict()
        }), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': f'Erro ao iniciar rota: {str(e)}'}), 500

@bp.route('/<int:id>/evento', methods=['POST'])
@jwt_required()
def registrar_evento(id):
    try:
        usuario_id = get_jwt_identity()
        usuario = Usuario.query.get(usuario_id)
        data = request.get_json()
        
        if not data or not data.get('evento') or not data.get('gps'):
            return jsonify({'erro': 'evento e gps são obrigatórios'}), 400
        
        os = OrdemServico.query.get(id)
        if not os:
            return jsonify({'erro': 'Ordem de Serviço não encontrada'}), 404
        
        motorista = Motorista.query.filter_by(usuario_id=usuario_id).first()
        if not motorista or os.motorista_id != motorista.id:
            return jsonify({'erro': 'Apenas o motorista atribuído pode registrar eventos'}), 403
        
        evento = data['evento'].upper()
        eventos_validos = ['CHEGUEI', 'COLETEI', 'SAI', 'FINALIZEI', 'CHEGUEI_MRX', 'FORNECEDOR_FECHADO', 'FORNECEDOR_NAO_ENCONTRADO']
        
        if evento not in eventos_validos:
            return jsonify({'erro': f'Evento inválido. Valores aceitos: {", ".join(eventos_validos)}'}), 400
        
        gps_log = GPSLog(
            os_id=os.id,
            evento=evento,
            latitude=data['gps']['latitude'],
            longitude=data['gps']['longitude'],
            precisao=data['gps'].get('precisao'),
            device_id=data.get('device_id'),
            ip=request.remote_addr,
            dados_adicionais={
                'observacao': data.get('observacao'),
                'foto': data.get('foto'),
                'motivo': data.get('motivo')
            }
        )
        db.session.add(gps_log)
        
        if evento == 'CHEGUEI':
            os.status = 'NO_FORNECEDOR'
        elif evento == 'COLETEI':
            os.status = 'COLETADO'
        elif evento == 'SAI':
            os.status = 'A_CAMINHO_MATRIZ'
        elif evento == 'CHEGUEI_MRX':
            os.status = 'ENTREGUE'
        elif evento == 'FORNECEDOR_FECHADO':
            os.status = 'IMPEDIDO'
            admins = Usuario.query.filter(
                db.or_(
                    Usuario.tipo == 'admin',
                    Usuario.perfil.has(nome='Administrador')
                )
            ).all()
            for admin in admins:
                notificacao = Notificacao(
                    usuario_id=admin.id,
                    titulo='Fornecedor Fechado',
                    mensagem=f'OS {os.numero_os}: Motorista registrou que o fornecedor está fechado. Motivo: {data.get("motivo", "Não informado")}',
                    tipo='alerta_motorista',
                    url='/logistica.html',
                    lida=False
                )
                db.session.add(notificacao)
        elif evento == 'FORNECEDOR_NAO_ENCONTRADO':
            os.status = 'IMPEDIDO'
            admins = Usuario.query.filter(
                db.or_(
                    Usuario.tipo == 'admin',
                    Usuario.perfil.has(nome='Administrador')
                )
            ).all()
            for admin in admins:
                notificacao = Notificacao(
                    usuario_id=admin.id,
                    titulo='Fornecedor Não Encontrado',
                    mensagem=f'OS {os.numero_os}: Motorista não conseguiu localizar o fornecedor. Motivo: {data.get("motivo", "Não informado")}',
                    tipo='alerta_motorista',
                    url='/logistica.html',
                    lida=False
                )
                db.session.add(notificacao)
        elif evento == 'FINALIZEI':
            os.status = 'FINALIZADA'
            
            conferencia_existente = ConferenciaRecebimento.query.filter_by(os_id=os.id).first()
            if not conferencia_existente:
                oc = OrdemCompra.query.get(os.oc_id)
                if oc:
                    peso_previsto = 0
                    quantidade_prevista = 0
                    if oc.solicitacao and oc.solicitacao.itens:
                        for item in oc.solicitacao.itens:
                            peso_kg = item.peso_kg or 0
                            peso_previsto += peso_kg
                            quantidade_prevista += 1
                    
                    conferencia = ConferenciaRecebimento(
                        os_id=os.id,
                        oc_id=os.oc_id,
                        peso_fornecedor=peso_previsto,
                        quantidade_prevista=quantidade_prevista,
                        conferencia_status='PENDENTE',
                        auditoria=[{
                            'acao': 'CRIACAO_AUTOMATICA',
                            'usuario_id': usuario_id,
                            'timestamp': datetime.utcnow().isoformat(),
                            'detalhes': {'os_id': os.id, 'oc_id': os.oc_id, 'criado_por': 'FINALIZACAO_OS'},
                            'ip': request.remote_addr,
                            'user_agent': request.headers.get('User-Agent')
                        }]
                    )
                    db.session.add(conferencia)
                    
                    conferentes = Usuario.query.join(Usuario.perfil).filter(
                        db.or_(
                            db.text("perfis.nome = 'Conferente / Estoque'"),
                            db.text("perfis.nome = 'Administrador'")
                        )
                    ).all()
                    
                    for conferente in conferentes:
                        notificacao = Notificacao(
                            usuario_id=conferente.id,
                            titulo='Nova Conferência Pendente',
                            mensagem=f'OS {os.numero_os} foi finalizada. Conferência #{conferencia.id if conferencia.id else "nova"} criada e aguardando processamento.',
                            tipo='nova_conferencia',
                            url='/conferencias.html',
                            lida=False
                        )
                        db.session.add(notificacao)
        
        registrar_auditoria_os(os, f'EVENTO_{evento}', usuario_id, {
            'gps': data['gps'],
            'observacao': data.get('observacao')
        })
        
        db.session.commit()
        
        return jsonify({
            'mensagem': f'Evento {evento} registrado com sucesso',
            'os': os.to_dict()
        }), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': f'Erro ao registrar evento: {str(e)}'}), 500

@bp.route('/<int:id>/cancelar-impedido', methods=['PUT'])
@admin_required
def cancelar_os_impedido(id):
    """Cancela uma OS com status IMPEDIDO e a volta para PENDENTE para reatribuição"""
    try:
        usuario_id = get_jwt_identity()
        
        os = OrdemServico.query.get(id)
        if not os:
            return jsonify({'erro': 'Ordem de Serviço não encontrada'}), 404
        
        if os.status != 'IMPEDIDO':
            return jsonify({'erro': f'Esta ação só é permitida para OS com status IMPEDIDO. Status atual: {os.status}'}), 400
        
        status_anterior = os.status
        motorista_anterior_id = os.motorista_id
        motorista_anterior_nome = os.motorista.usuario.nome if os.motorista and os.motorista.usuario else 'Não atribuído'
        
        os.status = 'PENDENTE'
        os.motorista_id = None
        os.veiculo_id = None
        
        registrar_auditoria_os(os, 'CANCELAR_IMPEDIDO', usuario_id, {
            'status_anterior': status_anterior,
            'motorista_anterior_id': motorista_anterior_id,
            'motorista_anterior_nome': motorista_anterior_nome,
            'acao': 'OS retornada para pendente para reatribuição'
        })
        
        if motorista_anterior_id:
            motorista = Motorista.query.get(motorista_anterior_id)
            if motorista and motorista.usuario:
                notificacao = Notificacao(
                    usuario_id=motorista.usuario.id,
                    titulo='OS Cancelada e Reatribuída',
                    mensagem=f'A OS {os.numero_os} foi cancelada pelo administrador e será reatribuída a outro motorista.',
                    tipo='os_cancelada',
                    url='/logistica.html',
                    lida=False
                )
                db.session.add(notificacao)
        
        db.session.commit()
        
        return jsonify({
            'mensagem': 'OS cancelada e disponível para reatribuição',
            'os': os.to_dict()
        }), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': f'Erro ao cancelar OS impedida: {str(e)}'}), 500

@bp.route('/<int:id>/retentar', methods=['PUT'])
@admin_required
def retentar_os(id):
    """Reenvia uma OS com status IMPEDIDO para o mesmo motorista tentar novamente"""
    try:
        usuario_id = get_jwt_identity()
        
        os = OrdemServico.query.get(id)
        if not os:
            return jsonify({'erro': 'Ordem de Serviço não encontrada'}), 404
        
        if os.status != 'IMPEDIDO':
            return jsonify({'erro': f'Esta ação só é permitida para OS com status IMPEDIDO. Status atual: {os.status}'}), 400
        
        if not os.motorista_id:
            return jsonify({'erro': 'Não há motorista atribuído a esta OS'}), 400
        
        status_anterior = os.status
        motorista = Motorista.query.get(os.motorista_id)
        
        os.status = 'AGENDADA'
        
        registrar_auditoria_os(os, 'RETENTAR_IMPEDIDO', usuario_id, {
            'status_anterior': status_anterior,
            'motorista_id': os.motorista_id,
            'motorista_nome': motorista.usuario.nome if motorista and motorista.usuario else 'Desconhecido',
            'acao': 'OS reenviada para o mesmo motorista tentar novamente'
        })
        
        if motorista and motorista.usuario:
            notificacao = Notificacao(
                usuario_id=motorista.usuario.id,
                titulo='Nova Tentativa - OS Reenviada',
                mensagem=f'A OS {os.numero_os} foi reenviada para você. Por favor, tente realizar a coleta novamente.',
                tipo='os_reenvio',
                url='/logistica.html',
                lida=False
            )
            db.session.add(notificacao)
        
        db.session.commit()
        
        return jsonify({
            'mensagem': 'OS reenviada para o motorista',
            'os': os.to_dict()
        }), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': f'Erro ao retentar OS: {str(e)}'}), 500

@bp.route('/<int:id>/cancelar', methods=['PUT'])
@admin_required
def cancelar_os(id):
    try:
        usuario_id = get_jwt_identity()
        data = request.get_json() or {}
        
        if not data.get('motivo'):
            return jsonify({'erro': 'motivo é obrigatório'}), 400
        
        os = OrdemServico.query.get(id)
        if not os:
            return jsonify({'erro': 'Ordem de Serviço não encontrada'}), 404
        
        if os.status in ['FINALIZADA', 'CANCELADA']:
            return jsonify({'erro': f'Não é possível cancelar OS no status {os.status}'}), 400
        
        status_anterior = os.status
        os.status = 'CANCELADA'
        
        registrar_auditoria_os(os, 'CANCELAMENTO', usuario_id, {
            'motivo': data['motivo'],
            'status_anterior': status_anterior
        })
        
        if os.motorista and os.motorista.usuario_id:
            notificacao = Notificacao(
                usuario_id=os.motorista.usuario_id,
                titulo='OS Cancelada',
                mensagem=f'A OS {os.numero_os} foi cancelada. Motivo: {data["motivo"]}',
                url='/logistica.html',
                lida=False
            )
            db.session.add(notificacao)
        
        db.session.commit()
        
        return jsonify({
            'mensagem': 'OS cancelada com sucesso',
            'os': os.to_dict()
        }), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': f'Erro ao cancelar OS: {str(e)}'}), 500

@bp.route('/<int:id>/marcar-recebido', methods=['PUT'])
@admin_required
def marcar_recebido(id):
    """Marca uma OS como recebida quando o tipo de retirada é 'entregar' (Fornecedor Entrega)"""
    try:
        usuario_id = get_jwt_identity()
        
        os = OrdemServico.query.get(id)
        if not os:
            return jsonify({'erro': 'Ordem de Serviço não encontrada'}), 404
        
        if os.status != 'PENDENTE':
            return jsonify({'erro': f'Esta ação só é permitida para OS com status PENDENTE. Status atual: {os.status}'}), 400
        
        oc = os.ordem_compra
        if not oc or not oc.solicitacao:
            return jsonify({'erro': 'Não foi possível verificar o tipo de retirada desta OS'}), 400
        
        tipo_retirada = oc.solicitacao.tipo_retirada
        if tipo_retirada != 'entregar':
            return jsonify({'erro': 'Esta ação só é permitida para pedidos com tipo de retirada "Fornecedor Entrega"'}), 400
        
        status_anterior = os.status
        os.status = 'FINALIZADA'
        
        registrar_auditoria_os(os, 'RECEBIMENTO_FORNECEDOR_ENTREGA', usuario_id, {
            'status_anterior': status_anterior,
            'tipo_retirada': tipo_retirada,
            'acao': 'Material recebido - Fornecedor realizou a entrega'
        })
        
        conferencia_existente = ConferenciaRecebimento.query.filter_by(os_id=os.id).first()
        if not conferencia_existente:
            peso_previsto = 0
            quantidade_prevista = 0
            if oc.solicitacao and oc.solicitacao.itens:
                for item in oc.solicitacao.itens:
                    peso_kg = item.peso_kg or 0
                    peso_previsto += peso_kg
                    quantidade_prevista += 1
            
            conferencia = ConferenciaRecebimento(
                os_id=os.id,
                oc_id=os.oc_id,
                peso_fornecedor=peso_previsto,
                quantidade_prevista=quantidade_prevista,
                conferencia_status='PENDENTE',
                auditoria=[{
                    'acao': 'CRIACAO_RECEBIMENTO_FORNECEDOR',
                    'usuario_id': usuario_id,
                    'timestamp': datetime.utcnow().isoformat(),
                    'detalhes': {'os_id': os.id, 'oc_id': os.oc_id, 'criado_por': 'RECEBIMENTO_FORNECEDOR_ENTREGA'},
                    'ip': request.remote_addr,
                    'user_agent': request.headers.get('User-Agent')
                }]
            )
            db.session.add(conferencia)
            
            conferentes = Usuario.query.join(Usuario.perfil).filter(
                db.or_(
                    db.text("perfis.nome = 'Conferente / Estoque'"),
                    db.text("perfis.nome = 'Administrador'")
                )
            ).all()
            
            for conferente in conferentes:
                notificacao = Notificacao(
                    usuario_id=conferente.id,
                    titulo='Nova Conferência - Entrega do Fornecedor',
                    mensagem=f'OS {os.numero_os} foi recebida (entrega do fornecedor). Conferência criada e aguardando processamento.',
                    tipo='nova_conferencia',
                    url='/conferencias.html',
                    lida=False
                )
                db.session.add(notificacao)
        
        db.session.commit()
        
        return jsonify({
            'mensagem': 'Material recebido com sucesso! OS finalizada.',
            'os': os.to_dict()
        }), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': f'Erro ao marcar como recebido: {str(e)}'}), 500

@bp.route('/estatisticas', methods=['GET'])
@jwt_required()
def obter_estatisticas():
    try:
        usuario_id = get_jwt_identity()
        usuario = Usuario.query.get(usuario_id)
        
        query = OrdemServico.query
        
        perfil_nome = usuario.perfil.nome if usuario.perfil else None
        if perfil_nome == 'Motorista' or usuario.tipo == 'motorista':
            motorista = Motorista.query.filter_by(usuario_id=usuario_id).first()
            if motorista:
                query = query.filter_by(motorista_id=motorista.id)
        
        total_os = query.count()
        pendentes = query.filter_by(status='PENDENTE').count()
        agendadas = query.filter_by(status='AGENDADA').count()
        em_rota = query.filter_by(status='EM_ROTA').count()
        impedidas = query.filter_by(status='IMPEDIDO').count()
        finalizadas = query.filter_by(status='FINALIZADA').count()
        canceladas = query.filter_by(status='CANCELADA').count()
        
        return jsonify({
            'total_os': total_os,
            'pendentes': pendentes,
            'agendadas': agendadas,
            'em_rota': em_rota,
            'impedidas': impedidas,
            'finalizadas': finalizadas,
            'canceladas': canceladas
        }), 200
    
    except Exception as e:
        return jsonify({'erro': f'Erro ao obter estatísticas: {str(e)}'}), 500
