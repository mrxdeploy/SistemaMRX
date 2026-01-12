from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app.models import db, Fornecedor, Compra
from app.auth import admin_required

bp = Blueprint('fornecedores', __name__, url_prefix='/api/fornecedores')

@bp.route('', methods=['GET'])
@jwt_required()
def listar_fornecedores():
    busca = request.args.get('busca', '')
    ativo = request.args.get('ativo', type=bool)
    
    query = Fornecedor.query
    
    if busca:
        query = query.filter(
            db.or_(
                Fornecedor.nome.ilike(f'%{busca}%'),
                Fornecedor.nome_social.ilike(f'%{busca}%'),
                Fornecedor.cnpj.ilike(f'%{busca}%'),
                Fornecedor.cpf.ilike(f'%{busca}%'),
                Fornecedor.email.ilike(f'%{busca}%')
            )
        )
    
    if ativo is not None:
        query = query.filter_by(ativo=ativo)
    
    fornecedores = query.order_by(Fornecedor.nome).all()
    return jsonify([fornecedor.to_dict() for fornecedor in fornecedores]), 200

@bp.route('/<int:id>', methods=['GET'])
@jwt_required()
def obter_fornecedor(id):
    fornecedor = Fornecedor.query.get(id)
    
    if not fornecedor:
        return jsonify({'erro': 'Fornecedor não encontrado'}), 404
    
    fornecedor_dict = fornecedor.to_dict()
    fornecedor_dict['total_compras'] = len(fornecedor.compras)
    fornecedor_dict['valor_total_compras'] = sum(c.valor_total for c in fornecedor.compras)
    
    return jsonify(fornecedor_dict), 200

@bp.route('', methods=['POST'])
@admin_required
def criar_fornecedor():
    data = request.get_json()
    
    if not data or not data.get('nome'):
        return jsonify({'erro': 'Nome é obrigatório'}), 400
    
    if not data.get('cnpj') and not data.get('cpf'):
        return jsonify({'erro': 'CNPJ ou CPF é obrigatório'}), 400
    
    if data.get('cnpj'):
        fornecedor_existente = Fornecedor.query.filter_by(cnpj=data['cnpj']).first()
        if fornecedor_existente:
            return jsonify({'erro': 'CNPJ já cadastrado'}), 400
    
    if data.get('cpf'):
        fornecedor_existente = Fornecedor.query.filter_by(cpf=data['cpf']).first()
        if fornecedor_existente:
            return jsonify({'erro': 'CPF já cadastrado'}), 400
    
    fornecedor = Fornecedor(
        nome=data['nome'],
        nome_social=data.get('nome_social'),
        cnpj=data.get('cnpj'),
        cpf=data.get('cpf'),
        endereco_coleta=data.get('endereco_coleta'),
        endereco_emissao=data.get('endereco_emissao'),
        telefone=data.get('telefone'),
        email=data.get('email'),
        conta_bancaria=data.get('conta_bancaria'),
        agencia=data.get('agencia'),
        chave_pix=data.get('chave_pix'),
        banco=data.get('banco'),
        condicao_pagamento=data.get('condicao_pagamento'),
        forma_pagamento=data.get('forma_pagamento'),
        observacoes=data.get('observacoes'),
        ativo=data.get('ativo', True)
    )
    
    db.session.add(fornecedor)
    db.session.commit()
    
    return jsonify(fornecedor.to_dict()), 201

@bp.route('/<int:id>', methods=['PUT'])
@admin_required
def atualizar_fornecedor(id):
    fornecedor = Fornecedor.query.get(id)
    
    if not fornecedor:
        return jsonify({'erro': 'Fornecedor não encontrado'}), 404
    
    data = request.get_json()
    
    if data.get('cnpj') and data['cnpj'] != fornecedor.cnpj:
        fornecedor_existente = Fornecedor.query.filter_by(cnpj=data['cnpj']).first()
        if fornecedor_existente:
            return jsonify({'erro': 'CNPJ já cadastrado'}), 400
    
    if data.get('cpf') and data['cpf'] != fornecedor.cpf:
        fornecedor_existente = Fornecedor.query.filter_by(cpf=data['cpf']).first()
        if fornecedor_existente:
            return jsonify({'erro': 'CPF já cadastrado'}), 400
    
    campos = ['nome', 'nome_social', 'cnpj', 'cpf', 'endereco_coleta', 'endereco_emissao',
              'telefone', 'email', 'conta_bancaria', 'agencia', 'chave_pix', 'banco',
              'condicao_pagamento', 'forma_pagamento', 'observacoes', 'ativo']
    
    for campo in campos:
        if campo in data:
            setattr(fornecedor, campo, data[campo])
    
    db.session.commit()
    
    return jsonify(fornecedor.to_dict()), 200

@bp.route('/<int:id>', methods=['DELETE'])
@admin_required
def deletar_fornecedor(id):
    fornecedor = Fornecedor.query.get(id)
    
    if not fornecedor:
        return jsonify({'erro': 'Fornecedor não encontrado'}), 404
    
    db.session.delete(fornecedor)
    db.session.commit()
    
    return jsonify({'mensagem': 'Fornecedor deletado com sucesso'}), 200

@bp.route('/<int:id>/historico', methods=['GET'])
@jwt_required()
def obter_historico_fornecedor(id):
    fornecedor = Fornecedor.query.get(id)
    
    if not fornecedor:
        return jsonify({'erro': 'Fornecedor não encontrado'}), 404
    
    compras = Compra.query.filter_by(fornecedor_id=id).order_by(Compra.data_compra.desc()).all()
    
    return jsonify({
        'fornecedor': fornecedor.to_dict(),
        'compras': [compra.to_dict() for compra in compras]
    }), 200
