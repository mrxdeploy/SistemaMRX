from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app.models import db, Configuracao
from app.auth import admin_required

bp = Blueprint('tabelas', __name__, url_prefix='/api/tabelas')

@bp.route('/config', methods=['GET'])
@jwt_required()
def listar_configuracoes():
    tipo = request.args.get('tipo')
    
    query = Configuracao.query
    
    if tipo:
        query = query.filter_by(tipo=tipo)
    
    configuracoes = query.order_by(Configuracao.chave).all()
    return jsonify([config.to_dict() for config in configuracoes]), 200

@bp.route('/config/<string:chave>', methods=['GET'])
@jwt_required()
def obter_configuracao(chave):
    configuracao = Configuracao.query.filter_by(chave=chave).first()
    
    if not configuracao:
        return jsonify({'erro': 'Configuração não encontrada'}), 404
    
    return jsonify(configuracao.to_dict()), 200

@bp.route('/config', methods=['POST'])
@admin_required
def criar_configuracao():
    data = request.get_json()
    
    if not data or not data.get('chave') or not data.get('valor'):
        return jsonify({'erro': 'Chave e valor são obrigatórios'}), 400
    
    config_existente = Configuracao.query.filter_by(chave=data['chave']).first()
    if config_existente:
        return jsonify({'erro': 'Já existe uma configuração com esta chave'}), 400
    
    configuracao = Configuracao(
        chave=data['chave'],
        valor=data['valor'],
        descricao=data.get('descricao'),
        tipo=data.get('tipo', 'texto')
    )
    
    db.session.add(configuracao)
    db.session.commit()
    
    return jsonify(configuracao.to_dict()), 201

@bp.route('/config/<int:id>', methods=['PUT'])
@admin_required
def atualizar_configuracao(id):
    configuracao = Configuracao.query.get(id)
    
    if not configuracao:
        return jsonify({'erro': 'Configuração não encontrada'}), 404
    
    data = request.get_json()
    
    if data.get('valor'):
        configuracao.valor = data['valor']
    if data.get('descricao') is not None:
        configuracao.descricao = data['descricao']
    if data.get('tipo'):
        configuracao.tipo = data['tipo']
    
    db.session.commit()
    
    return jsonify(configuracao.to_dict()), 200

@bp.route('/config/<int:id>', methods=['DELETE'])
@admin_required
def deletar_configuracao(id):
    configuracao = Configuracao.query.get(id)
    
    if not configuracao:
        return jsonify({'erro': 'Configuração não encontrada'}), 404
    
    db.session.delete(configuracao)
    db.session.commit()
    
    return jsonify({'mensagem': 'Configuração deletada com sucesso'}), 200

@bp.route('/parametros', methods=['GET'])
@jwt_required()
def obter_parametros_padrao():
    parametros = {
        'formas_pagamento': ['pix', 'dinheiro', 'transferencia', 'boleto', 'cheque'],
        'condicoes_pagamento': ['avista', '7dias', '15dias', '30dias', '60dias'],
        'tipos_placa': ['leve', 'media', 'pesada'],
        'status_solicitacao': ['pendente', 'confirmada', 'aprovada', 'reprovada'],
        'status_entrada': ['pendente', 'aprovada', 'reprovada'],
        'status_compra': ['pendente', 'pago', 'cancelado'],
        'tipos_compra': ['compra', 'despesa'],
        'tipos_lote': ['leve', 'media', 'pesada']
    }
    
    return jsonify(parametros), 200

@bp.route('/inicializar', methods=['POST'])
@admin_required
def inicializar_configuracoes_padrao():
    configuracoes_padrao = [
        {'chave': 'sistema_nome', 'valor': 'MRX Systems', 'descricao': 'Nome do sistema', 'tipo': 'texto'},
        {'chave': 'peso_leve_max', 'valor': '50', 'descricao': 'Peso máximo para classificação leve (kg)', 'tipo': 'numero'},
        {'chave': 'peso_media_max', 'valor': '100', 'descricao': 'Peso máximo para classificação média (kg)', 'tipo': 'numero'},
        {'chave': 'email_notificacao', 'valor': 'admin@sistema.com', 'descricao': 'Email para notificações do sistema', 'tipo': 'email'},
    ]
    
    criados = []
    for config_data in configuracoes_padrao:
        existente = Configuracao.query.filter_by(chave=config_data['chave']).first()
        if not existente:
            config = Configuracao(**config_data)
            db.session.add(config)
            criados.append(config_data['chave'])
    
    db.session.commit()
    
    return jsonify({
        'mensagem': f'{len(criados)} configurações criadas com sucesso',
        'configuracoes_criadas': criados
    }), 201
