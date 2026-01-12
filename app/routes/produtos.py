from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app.models import Produto, FornecedorProdutoPreco, db
from app.auth import admin_required

bp = Blueprint('produtos', __name__, url_prefix='/api/produtos')

@bp.route('', methods=['GET'])
@jwt_required()
def listar_produtos():
    busca = request.args.get('busca', '')
    ativo = request.args.get('ativo', type=str)
    
    query = Produto.query
    
    if busca:
        query = query.filter(
            db.or_(
                Produto.nome.ilike(f'%{busca}%'),
                Produto.descricao.ilike(f'%{busca}%')
            )
        )
    
    if ativo is not None:
        ativo_bool = ativo.lower() == 'true'
        query = query.filter_by(ativo=ativo_bool)
    
    produtos = query.order_by(Produto.nome).all()
    return jsonify([produto.to_dict() for produto in produtos]), 200

@bp.route('/<int:id>', methods=['GET'])
@jwt_required()
def obter_produto(id):
    produto = Produto.query.get(id)
    
    if not produto:
        return jsonify({'erro': 'Produto não encontrado'}), 404
    
    return jsonify(produto.to_dict()), 200

@bp.route('', methods=['POST'])
@admin_required
def criar_produto():
    data = request.get_json()
    
    if not data or not data.get('nome'):
        return jsonify({'erro': 'Nome é obrigatório'}), 400
    
    produto_existente = Produto.query.filter_by(nome=data['nome']).first()
    if produto_existente:
        return jsonify({'erro': 'Produto já cadastrado com este nome'}), 400
    
    produto = Produto(
        nome=data['nome'],
        descricao=data.get('descricao', ''),
        ativo=data.get('ativo', True)
    )
    
    db.session.add(produto)
    db.session.commit()
    
    return jsonify(produto.to_dict()), 201

@bp.route('/<int:id>', methods=['PUT'])
@admin_required
def atualizar_produto(id):
    produto = Produto.query.get(id)
    
    if not produto:
        return jsonify({'erro': 'Produto não encontrado'}), 404
    
    data = request.get_json()
    
    if 'nome' in data:
        produto_existente = Produto.query.filter(
            Produto.nome == data['nome'],
            Produto.id != id
        ).first()
        if produto_existente:
            return jsonify({'erro': 'Já existe outro produto com este nome'}), 400
        produto.nome = data['nome']
    
    if 'descricao' in data:
        produto.descricao = data['descricao']
    
    if 'ativo' in data:
        produto.ativo = data['ativo']
    
    db.session.commit()
    
    return jsonify(produto.to_dict()), 200

@bp.route('/<int:id>', methods=['DELETE'])
@admin_required
def deletar_produto(id):
    produto = Produto.query.get(id)
    
    if not produto:
        return jsonify({'erro': 'Produto não encontrado'}), 404
    
    db.session.delete(produto)
    db.session.commit()
    
    return jsonify({'mensagem': 'Produto deletado com sucesso'}), 200

@bp.route('/fornecedor/<int:fornecedor_id>', methods=['GET'])
@jwt_required()
def listar_produtos_fornecedor(fornecedor_id):
    produtos_precos = FornecedorProdutoPreco.query.filter_by(
        fornecedor_id=fornecedor_id,
        ativo=True
    ).all()
    
    return jsonify([pp.to_dict() for pp in produtos_precos]), 200

@bp.route('/fornecedor/<int:fornecedor_id>/produto/<int:produto_id>', methods=['POST'])
@admin_required
def adicionar_produto_fornecedor(fornecedor_id, produto_id):
    data = request.get_json()
    
    fpp_existente = FornecedorProdutoPreco.query.filter_by(
        fornecedor_id=fornecedor_id,
        produto_id=produto_id
    ).first()
    
    if fpp_existente:
        return jsonify({'erro': 'Produto já associado a este fornecedor'}), 400
    
    fpp = FornecedorProdutoPreco(
        fornecedor_id=fornecedor_id,
        produto_id=produto_id,
        preco_por_kg=data.get('preco_por_kg', 0.0),
        classificacao_estrelas=data.get('estrelas', 3)
    )
    
    db.session.add(fpp)
    db.session.commit()
    
    return jsonify(fpp.to_dict()), 201

@bp.route('/fornecedor/<int:fornecedor_id>/produto/<int:produto_id>', methods=['PUT'])
@admin_required
def atualizar_produto_fornecedor(fornecedor_id, produto_id):
    fpp = FornecedorProdutoPreco.query.filter_by(
        fornecedor_id=fornecedor_id,
        produto_id=produto_id
    ).first()
    
    if not fpp:
        return jsonify({'erro': 'Associação não encontrada'}), 404
    
    data = request.get_json()
    
    if 'preco_por_kg' in data:
        fpp.preco_por_kg = data['preco_por_kg']
    
    if 'estrelas' in data:
        fpp.classificacao_estrelas = data['estrelas']
    
    if 'ativo' in data:
        fpp.ativo = data['ativo']
    
    db.session.commit()
    
    return jsonify(fpp.to_dict()), 200

@bp.route('/fornecedor/<int:fornecedor_id>/produto/<int:produto_id>', methods=['DELETE'])
@admin_required
def remover_produto_fornecedor(fornecedor_id, produto_id):
    fpp = FornecedorProdutoPreco.query.filter_by(
        fornecedor_id=fornecedor_id,
        produto_id=produto_id
    ).first()
    
    if not fpp:
        return jsonify({'erro': 'Associação não encontrada'}), 404
    
    db.session.delete(fpp)
    db.session.commit()
    
    return jsonify({'mensagem': 'Produto removido do fornecedor com sucesso'}), 200
