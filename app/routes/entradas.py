from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import db, Entrada, Solicitacao, Placa, Usuario, Notificacao, Lote
from app.auth import admin_required
from app import socketio
from datetime import datetime
import uuid

bp = Blueprint('entradas', __name__, url_prefix='/api/entradas')

@bp.route('', methods=['GET'])
@admin_required
def listar_entradas():
    status = request.args.get('status')
    
    query = Entrada.query
    
    if status:
        query = query.filter_by(status=status)
    
    entradas = query.order_by(Entrada.data_entrada.desc()).all()
    
    result = []
    for entrada in entradas:
        entrada_dict = entrada.to_dict()
        entrada_dict['solicitacao'] = entrada.solicitacao.to_dict()
        entrada_dict['placas'] = [placa.to_dict() for placa in entrada.solicitacao.placas]
        result.append(entrada_dict)
    
    return jsonify(result), 200

@bp.route('/<int:id>', methods=['GET'])
@admin_required
def obter_entrada(id):
    entrada = Entrada.query.get(id)
    
    if not entrada:
        return jsonify({'erro': 'Entrada não encontrada'}), 404
    
    entrada_dict = entrada.to_dict()
    entrada_dict['solicitacao'] = entrada.solicitacao.to_dict()
    entrada_dict['placas'] = [placa.to_dict() for placa in entrada.solicitacao.placas]
    
    return jsonify(entrada_dict), 200

@bp.route('/<int:id>/aprovar', methods=['PUT'])
@admin_required
def aprovar_entrada(id):
    usuario_id = get_jwt_identity()
    
    entrada = Entrada.query.get(id)
    
    if not entrada:
        return jsonify({'erro': 'Entrada não encontrada'}), 404
    
    entrada.status = 'aprovada'
    entrada.data_processamento = datetime.utcnow()
    entrada.admin_id = usuario_id
    
    placas_por_tipo = {}
    for placa in entrada.solicitacao.placas:
        placa.status = 'aprovada'
        placa.data_aprovacao = datetime.utcnow()
        
        tipo = placa.tipo_placa
        if tipo not in placas_por_tipo:
            placas_por_tipo[tipo] = []
        placas_por_tipo[tipo].append(placa)
    
    entrada.solicitacao.status = 'aprovada'
    
    lotes_criados = []
    for tipo_placa, placas in placas_por_tipo.items():
        numero_lote = f"LOTE-{uuid.uuid4().hex[:8].upper()}"
        
        peso_total = sum(p.peso_kg for p in placas)
        valor_total = sum(p.valor for p in placas)
        
        lote = Lote(
            numero_lote=numero_lote,
            fornecedor_id=entrada.solicitacao.fornecedor_id,
            tipo_material=tipo_placa,
            peso_total_kg=peso_total,
            valor_total=valor_total,
            quantidade_placas=len(placas),
            status='aberto'
        )
        
        db.session.add(lote)
        db.session.flush()
        
        for placa in placas:
            placa.lote_id = lote.id
        
        lotes_criados.append(numero_lote)
    
    notificacao = Notificacao(
        usuario_id=entrada.solicitacao.funcionario_id,
        titulo='Entrada Aprovada',
        mensagem=f'A entrada referente à solicitação #{entrada.solicitacao_id} foi aprovada. Todas as {len(entrada.solicitacao.placas)} placas foram aprovadas e {len(lotes_criados)} lote(s) criado(s): {", ".join(lotes_criados)}.',
        url='/entradas.html'
    )
    db.session.add(notificacao)
    
    db.session.commit()
    
    socketio.emit('nova_notificacao', {'tipo': 'entrada_aprovada'}, room=f'user_{entrada.solicitacao.funcionario_id}')
    
    return jsonify(entrada.to_dict()), 200

@bp.route('/<int:id>/reprovar', methods=['PUT'])
@admin_required
def reprovar_entrada(id):
    usuario_id = get_jwt_identity()
    data = request.get_json()
    
    entrada = Entrada.query.get(id)
    
    if not entrada:
        return jsonify({'erro': 'Entrada não encontrada'}), 404
    
    entrada.status = 'reprovada'
    entrada.data_processamento = datetime.utcnow()
    entrada.admin_id = usuario_id
    entrada.observacoes = data.get('observacoes', '')
    
    for placa in entrada.solicitacao.placas:
        placa.status = 'reprovada'
    
    entrada.solicitacao.status = 'reprovada'
    
    notificacao = Notificacao(
        usuario_id=entrada.solicitacao.funcionario_id,
        titulo='Entrada Reprovada',
        mensagem=f'A entrada referente à solicitação #{entrada.solicitacao_id} foi reprovada. Motivo: {entrada.observacoes}',
        url='/entradas.html'
    )
    db.session.add(notificacao)
    
    db.session.commit()
    
    socketio.emit('nova_notificacao', {'tipo': 'entrada_reprovada'}, room=f'user_{entrada.solicitacao.funcionario_id}')
    
    return jsonify(entrada.to_dict()), 200

@bp.route('/estatisticas', methods=['GET'])
@admin_required
def obter_estatisticas():
    total_pendentes = Entrada.query.filter_by(status='pendente').count()
    total_aprovadas = Entrada.query.filter_by(status='aprovada').count()
    total_reprovadas = Entrada.query.filter_by(status='reprovada').count()
    
    placas_aprovadas = db.session.query(db.func.count(Placa.id)).filter_by(status='aprovada').scalar()
    peso_total_aprovado = db.session.query(db.func.sum(Placa.peso_kg)).filter_by(status='aprovada').scalar() or 0
    valor_total_aprovado = db.session.query(db.func.sum(Placa.valor)).filter_by(status='aprovada').scalar() or 0
    
    return jsonify({
        'entradas_pendentes': total_pendentes,
        'entradas_aprovadas': total_aprovadas,
        'entradas_reprovadas': total_reprovadas,
        'placas_aprovadas': placas_aprovadas,
        'peso_total_kg': float(peso_total_aprovado),
        'valor_total': float(valor_total_aprovado)
    }), 200
