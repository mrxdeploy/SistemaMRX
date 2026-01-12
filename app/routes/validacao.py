from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from app.models import db, Solicitacao, Placa, Entrada, Notificacao
from app.auth import admin_required
from app import socketio

bp = Blueprint('validacao', __name__, url_prefix='/api/validacao')

@bp.route('/pendentes', methods=['GET'])
@admin_required
def listar_pendentes():
    solicitacoes = Solicitacao.query.filter_by(status='confirmada').all()
    
    result = []
    for solicitacao in solicitacoes:
        placas_pendentes = [p for p in solicitacao.placas if p.status == 'em_analise']
        if placas_pendentes:
            solicitacao_dict = solicitacao.to_dict()
            solicitacao_dict['placas'] = [placa.to_dict() for placa in placas_pendentes]
            solicitacao_dict['total_placas_pendentes'] = len(placas_pendentes)
            solicitacao_dict['peso_total'] = sum(p.peso_kg for p in placas_pendentes)
            solicitacao_dict['valor_total'] = sum(p.valor for p in placas_pendentes)
            result.append(solicitacao_dict)
    
    return jsonify(result), 200

@bp.route('/solicitacao/<int:id>/aprovar', methods=['PUT'])
@admin_required
def aprovar_solicitacao(id):
    usuario_id = get_jwt_identity()
    
    solicitacao = Solicitacao.query.get(id)
    
    if not solicitacao:
        return jsonify({'erro': 'Solicitação não encontrada'}), 404
    
    if solicitacao.status != 'confirmada':
        return jsonify({'erro': 'Apenas solicitações confirmadas podem ser validadas'}), 400
    
    entrada_existente = Entrada.query.filter_by(solicitacao_id=id).first()
    if not entrada_existente:
        entrada = Entrada(
            solicitacao_id=id,
            admin_id=usuario_id,
            status='aprovada',
            data_processamento=datetime.utcnow()
        )
        db.session.add(entrada)
    else:
        entrada_existente.status = 'aprovada'
        entrada_existente.admin_id = usuario_id
        entrada_existente.data_processamento = datetime.utcnow()
        entrada = entrada_existente
    
    for placa in solicitacao.placas:
        if placa.status == 'em_analise':
            placa.status = 'aprovada'
            placa.data_aprovacao = datetime.utcnow()
    
    solicitacao.status = 'aprovada'
    
    notificacao = Notificacao(
        usuario_id=solicitacao.funcionario_id,
        titulo='Solicitação Validada',
        mensagem=f'Sua solicitação #{solicitacao.id} foi validada e aprovada. Total de {len(solicitacao.placas)} placas inseridas no sistema.',
        url=f'/solicitacoes.html?id={solicitacao.id}'
    )
    db.session.add(notificacao)
    
    db.session.commit()
    
    socketio.emit('nova_notificacao', {
        'tipo': 'validacao_aprovada',
        'solicitacao_id': solicitacao.id
    }, room=f'user_{solicitacao.funcionario_id}')
    
    return jsonify({
        'mensagem': 'Solicitação aprovada com sucesso',
        'entrada': entrada.to_dict()
    }), 200

@bp.route('/solicitacao/<int:id>/reprovar', methods=['PUT'])
@admin_required
def reprovar_solicitacao(id):
    usuario_id = get_jwt_identity()
    data = request.get_json()
    
    solicitacao = Solicitacao.query.get(id)
    
    if not solicitacao:
        return jsonify({'erro': 'Solicitação não encontrada'}), 404
    
    if solicitacao.status != 'confirmada':
        return jsonify({'erro': 'Apenas solicitações confirmadas podem ser reprovadas'}), 400
    
    observacoes = data.get('observacoes', 'Solicitação reprovada na validação')
    
    entrada_existente = Entrada.query.filter_by(solicitacao_id=id).first()
    if not entrada_existente:
        entrada = Entrada(
            solicitacao_id=id,
            admin_id=usuario_id,
            status='reprovada',
            data_processamento=datetime.utcnow(),
            observacoes=observacoes
        )
        db.session.add(entrada)
    else:
        entrada_existente.status = 'reprovada'
        entrada_existente.admin_id = usuario_id
        entrada_existente.data_processamento = datetime.utcnow()
        entrada_existente.observacoes = observacoes
        entrada = entrada_existente
    
    for placa in solicitacao.placas:
        if placa.status == 'em_analise':
            placa.status = 'reprovada'
    
    solicitacao.status = 'reprovada'
    
    notificacao = Notificacao(
        usuario_id=solicitacao.funcionario_id,
        titulo='Solicitação Reprovada',
        mensagem=f'Sua solicitação #{solicitacao.id} foi reprovada. Motivo: {observacoes}',
        url=f'/solicitacoes.html?id={solicitacao.id}'
    )
    db.session.add(notificacao)
    
    db.session.commit()
    
    socketio.emit('nova_notificacao', {
        'tipo': 'validacao_reprovada',
        'solicitacao_id': solicitacao.id
    }, room=f'user_{solicitacao.funcionario_id}')
    
    return jsonify({
        'mensagem': 'Solicitação reprovada com sucesso',
        'entrada': entrada.to_dict()
    }), 200

@bp.route('/placa/<int:id>/aprovar', methods=['PUT'])
@admin_required
def aprovar_placa_individual(id):
    placa = Placa.query.get(id)
    
    if not placa:
        return jsonify({'erro': 'Placa não encontrada'}), 404
    
    placa.status = 'aprovada'
    placa.data_aprovacao = datetime.utcnow()
    
    db.session.commit()
    
    return jsonify({
        'mensagem': 'Placa aprovada com sucesso',
        'placa': placa.to_dict()
    }), 200

@bp.route('/placa/<int:id>/reprovar', methods=['PUT'])
@admin_required
def reprovar_placa_individual(id):
    placa = Placa.query.get(id)
    
    if not placa:
        return jsonify({'erro': 'Placa não encontrada'}), 404
    
    data = request.get_json()
    placa.status = 'reprovada'
    placa.observacoes = data.get('observacoes', 'Placa reprovada individualmente')
    
    db.session.commit()
    
    return jsonify({
        'mensagem': 'Placa reprovada com sucesso',
        'placa': placa.to_dict()
    }), 200
