from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import db, ConfiguracaoPrecoEstrela, Usuario

bp = Blueprint('configuracoes', __name__, url_prefix='/api/configuracoes')

@bp.route('/precos-estrelas', methods=['GET'])
@jwt_required()
def listar_configuracoes():
    configuracoes = ConfiguracaoPrecoEstrela.query.all()
    return jsonify([c.to_dict() for c in configuracoes])

@bp.route('/precos-estrelas/<tipo_placa>', methods=['GET'])
@jwt_required()
def obter_configuracao(tipo_placa):
    config = ConfiguracaoPrecoEstrela.query.filter_by(tipo_placa=tipo_placa).first()
    if not config:
        return jsonify({'error': 'Configuração não encontrada'}), 404
    return jsonify(config.to_dict())

@bp.route('/precos-estrelas', methods=['POST'])
@jwt_required()
def criar_ou_atualizar_configuracao():
    usuario_id = get_jwt_identity()
    usuario = Usuario.query.get(usuario_id)
    
    if not usuario:
        return jsonify({'error': 'Usuário não encontrado'}), 401
    
    if usuario.tipo != 'admin':
        return jsonify({'error': 'Acesso negado'}), 403
    
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Dados inválidos ou ausentes'}), 400
    
    tipo_placa = data.get('tipo_placa')
    
    if not tipo_placa:
        return jsonify({'error': 'Tipo de placa é obrigatório'}), 400
    
    config = ConfiguracaoPrecoEstrela.query.filter_by(tipo_placa=tipo_placa).first()
    
    if config:
        # Atualizar existente
        config.valor_1_estrela = data.get('valor_1_estrela', config.valor_1_estrela)
        config.valor_2_estrelas = data.get('valor_2_estrelas', config.valor_2_estrelas)
        config.valor_3_estrelas = data.get('valor_3_estrelas', config.valor_3_estrelas)
        config.valor_4_estrelas = data.get('valor_4_estrelas', config.valor_4_estrelas)
        config.valor_5_estrelas = data.get('valor_5_estrelas', config.valor_5_estrelas)
    else:
        # Criar novo
        config = ConfiguracaoPrecoEstrela(
            tipo_placa=tipo_placa,
            valor_1_estrela=data.get('valor_1_estrela', 0.0),
            valor_2_estrelas=data.get('valor_2_estrelas', 0.0),
            valor_3_estrelas=data.get('valor_3_estrelas', 0.0),
            valor_4_estrelas=data.get('valor_4_estrelas', 0.0),
            valor_5_estrelas=data.get('valor_5_estrelas', 0.0)
        )
        db.session.add(config)
    
    db.session.commit()
    return jsonify(config.to_dict()), 200

@bp.route('/precos-estrelas/inicializar', methods=['POST'])
@jwt_required()
def inicializar_configuracoes():
    usuario_id = get_jwt_identity()
    usuario = Usuario.query.get(usuario_id)
    
    if not usuario:
        return jsonify({'error': 'Usuário não encontrado'}), 401
    
    if usuario.tipo != 'admin':
        return jsonify({'error': 'Acesso negado'}), 403
    
    tipos_placa = ['leve', 'pesada', 'media']
    
    for tipo in tipos_placa:
        config = ConfiguracaoPrecoEstrela.query.filter_by(tipo_placa=tipo).first()
        if not config:
            config = ConfiguracaoPrecoEstrela(
                tipo_placa=tipo,
                valor_1_estrela=0.50,
                valor_2_estrelas=0.75,
                valor_3_estrelas=1.00,
                valor_4_estrelas=1.25,
                valor_5_estrelas=1.50
            )
            db.session.add(config)
    
    db.session.commit()
    return jsonify({'message': 'Configurações inicializadas com sucesso'}), 200
