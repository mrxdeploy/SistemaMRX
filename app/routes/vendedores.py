from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app.models import db, Vendedor
from app.auth import admin_required

bp = Blueprint('vendedores', __name__, url_prefix='/api/vendedores')

@bp.route('', methods=['GET'])
@jwt_required()
def listar_vendedores():
    busca = request.args.get('busca', '')
    ativo = request.args.get('ativo', type=bool)
    
    query = Vendedor.query
    
    if busca:
        query = query.filter(
            db.or_(
                Vendedor.nome.ilike(f'%{busca}%'),
                Vendedor.email.ilike(f'%{busca}%'),
                Vendedor.cpf.ilike(f'%{busca}%')
            )
        )
    
    if ativo is not None:
        query = query.filter_by(ativo=ativo)
    
    vendedores = query.order_by(Vendedor.nome).all()
    return jsonify([vendedor.to_dict() for vendedor in vendedores]), 200

@bp.route('/<int:id>', methods=['GET'])
@jwt_required()
def obter_vendedor(id):
    vendedor = Vendedor.query.get(id)
    
    if not vendedor:
        return jsonify({'erro': 'Vendedor não encontrado'}), 404
    
    vendedor_dict = vendedor.to_dict()
    vendedor_dict['total_fornecedores'] = len(vendedor.fornecedores)
    vendedor_dict['fornecedores'] = [{'id': f.id, 'nome': f.nome} for f in vendedor.fornecedores]
    
    return jsonify(vendedor_dict), 200

@bp.route('', methods=['POST'])
@admin_required
def criar_vendedor():
    data = request.get_json()
    
    if not data or not data.get('nome'):
        return jsonify({'erro': 'Nome é obrigatório'}), 400
    
    if data.get('email'):
        vendedor_existente = Vendedor.query.filter_by(email=data['email']).first()
        if vendedor_existente:
            return jsonify({'erro': 'Email já cadastrado'}), 400
    
    if data.get('cpf'):
        vendedor_existente = Vendedor.query.filter_by(cpf=data['cpf']).first()
        if vendedor_existente:
            return jsonify({'erro': 'CPF já cadastrado'}), 400
    
    vendedor = Vendedor(
        nome=data['nome'],
        email=data.get('email', ''),
        telefone=data.get('telefone', ''),
        cpf=data.get('cpf', ''),
        ativo=data.get('ativo', True)
    )
    
    db.session.add(vendedor)
    db.session.commit()
    
    return jsonify(vendedor.to_dict()), 201

@bp.route('/<int:id>', methods=['PUT'])
@admin_required
def atualizar_vendedor(id):
    vendedor = Vendedor.query.get(id)
    
    if not vendedor:
        return jsonify({'erro': 'Vendedor não encontrado'}), 404
    
    data = request.get_json()
    
    if data.get('nome'):
        vendedor.nome = data['nome']
    if 'email' in data:
        vendedor.email = data['email']
    if 'telefone' in data:
        vendedor.telefone = data['telefone']
    if 'cpf' in data:
        vendedor.cpf = data['cpf']
    if 'ativo' in data:
        vendedor.ativo = data['ativo']
    
    db.session.commit()
    
    return jsonify(vendedor.to_dict()), 200

@bp.route('/<int:id>', methods=['DELETE'])
@admin_required
def deletar_vendedor(id):
    vendedor = Vendedor.query.get(id)
    
    if not vendedor:
        return jsonify({'erro': 'Vendedor não encontrado'}), 404
    
    if len(vendedor.fornecedores) > 0:
        return jsonify({'erro': 'Não é possível deletar vendedor com fornecedores associados'}), 400
    
    db.session.delete(vendedor)
    db.session.commit()
    
    return jsonify({'mensagem': 'Vendedor deletado com sucesso'}), 200
