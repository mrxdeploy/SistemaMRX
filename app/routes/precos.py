from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app.models import Fornecedor, Preco, db
from app.auth import admin_required

bp = Blueprint('precos', __name__, url_prefix='/api/precos')

@bp.route('', methods=['GET'])
@jwt_required()
def listar_precos():
    fornecedor_id = request.args.get('fornecedor_id', type=int)
    
    if fornecedor_id:
        precos = Preco.query.filter_by(fornecedor_id=fornecedor_id).all()
    else:
        precos = Preco.query.all()
    
    return jsonify([preco.to_dict() for preco in precos]), 200

@bp.route('/<int:id>', methods=['GET'])
@jwt_required()
def obter_preco(id):
    preco = Preco.query.get(id)
    
    if not preco:
        return jsonify({'erro': 'Preço não encontrado'}), 404
    
    return jsonify(preco.to_dict()), 200

@bp.route('', methods=['POST'])
@admin_required
def criar_preco():
    data = request.get_json()
    
    if not data or not data.get('fornecedor_id') or not data.get('tipo_placa') or not data.get('preco_por_kg'):
        return jsonify({'erro': 'Fornecedor, tipo de placa e preço por kg são obrigatórios'}), 400
    
    fornecedor = Fornecedor.query.get(data['fornecedor_id'])
    if not fornecedor:
        return jsonify({'erro': 'Fornecedor não encontrado'}), 404
    
    preco_existente = Preco.query.filter_by(
        fornecedor_id=data['fornecedor_id'],
        tipo_placa=data['tipo_placa']
    ).first()
    
    if preco_existente:
        return jsonify({'erro': 'Já existe um preço cadastrado para este tipo de placa neste fornecedor'}), 400
    
    preco = Preco(
        fornecedor_id=data['fornecedor_id'],
        tipo_placa=data['tipo_placa'],
        preco_por_kg=data['preco_por_kg']
    )
    
    db.session.add(preco)
    db.session.commit()
    
    return jsonify(preco.to_dict()), 201

@bp.route('/<int:id>', methods=['PUT'])
@admin_required
def atualizar_preco(id):
    preco = Preco.query.get(id)
    
    if not preco:
        return jsonify({'erro': 'Preço não encontrado'}), 404
    
    data = request.get_json()
    
    if data.get('preco_por_kg'):
        preco.preco_por_kg = data['preco_por_kg']
    
    db.session.commit()
    
    return jsonify(preco.to_dict()), 200

@bp.route('/<int:id>', methods=['DELETE'])
@admin_required
def deletar_preco(id):
    preco = Preco.query.get(id)
    
    if not preco:
        return jsonify({'erro': 'Preço não encontrado'}), 404
    
    db.session.delete(preco)
    db.session.commit()
    
    return jsonify({'mensagem': 'Preço deletado com sucesso'}), 200
