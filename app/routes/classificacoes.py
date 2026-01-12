from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app.models import db, Classificacao
from app.auth import admin_required

bp = Blueprint('classificacoes', __name__, url_prefix='/api/classificacoes')

@bp.route('', methods=['GET'])
@jwt_required()
def listar_classificacoes():
    tipo_lote = request.args.get('tipo_lote')
    
    query = Classificacao.query
    
    if tipo_lote:
        query = query.filter_by(tipo_lote=tipo_lote)
    
    classificacoes = query.order_by(Classificacao.nome).all()
    return jsonify([classificacao.to_dict() for classificacao in classificacoes]), 200

@bp.route('/<int:id>', methods=['GET'])
@jwt_required()
def obter_classificacao(id):
    classificacao = Classificacao.query.get(id)
    
    if not classificacao:
        return jsonify({'erro': 'Classificação não encontrada'}), 404
    
    return jsonify(classificacao.to_dict()), 200

@bp.route('', methods=['POST'])
@admin_required
def criar_classificacao():
    data = request.get_json()
    
    if not data or not data.get('nome') or not data.get('tipo_lote'):
        return jsonify({'erro': 'Nome e tipo de lote são obrigatórios'}), 400
    
    classificacao_existente = Classificacao.query.filter_by(nome=data['nome']).first()
    if classificacao_existente:
        return jsonify({'erro': 'Já existe uma classificação com este nome'}), 400
    
    classificacao = Classificacao(
        nome=data['nome'],
        tipo_lote=data['tipo_lote'],
        peso_minimo=data.get('peso_minimo', 0.0),
        peso_maximo=data.get('peso_maximo', 999999.0),
        observacoes=data.get('observacoes')
    )
    
    db.session.add(classificacao)
    db.session.commit()
    
    return jsonify(classificacao.to_dict()), 201

@bp.route('/<int:id>', methods=['PUT'])
@admin_required
def atualizar_classificacao(id):
    classificacao = Classificacao.query.get(id)
    
    if not classificacao:
        return jsonify({'erro': 'Classificação não encontrada'}), 404
    
    data = request.get_json()
    
    if data.get('nome') and data['nome'] != classificacao.nome:
        classificacao_existente = Classificacao.query.filter_by(nome=data['nome']).first()
        if classificacao_existente:
            return jsonify({'erro': 'Já existe uma classificação com este nome'}), 400
    
    if data.get('nome'):
        classificacao.nome = data['nome']
    if data.get('tipo_lote'):
        classificacao.tipo_lote = data['tipo_lote']
    if 'peso_minimo' in data:
        classificacao.peso_minimo = data['peso_minimo']
    if 'peso_maximo' in data:
        classificacao.peso_maximo = data['peso_maximo']
    if 'observacoes' in data:
        classificacao.observacoes = data['observacoes']
    
    db.session.commit()
    
    return jsonify(classificacao.to_dict()), 200

@bp.route('/<int:id>', methods=['DELETE'])
@admin_required
def deletar_classificacao(id):
    classificacao = Classificacao.query.get(id)
    
    if not classificacao:
        return jsonify({'erro': 'Classificação não encontrada'}), 404
    
    db.session.delete(classificacao)
    db.session.commit()
    
    return jsonify({'mensagem': 'Classificação deletada com sucesso'}), 200

@bp.route('/classificar-lote', methods=['POST'])
@jwt_required()
def classificar_lote():
    data = request.get_json()
    
    if not data or not data.get('peso_total'):
        return jsonify({'erro': 'Peso total é obrigatório'}), 400
    
    peso_total = float(data['peso_total'])
    
    classificacao = Classificacao.query.filter(
        Classificacao.peso_minimo <= peso_total,
        Classificacao.peso_maximo >= peso_total
    ).first()
    
    if not classificacao:
        return jsonify({'tipo_lote': 'indefinido', 'mensagem': 'Nenhuma classificação encontrada para este peso'}), 200
    
    return jsonify(classificacao.to_dict()), 200
