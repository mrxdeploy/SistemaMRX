from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import db, Veiculo
from app.auth import permission_required, admin_required
from app.utils.auditoria import registrar_criacao, registrar_atualizacao, registrar_exclusao

bp = Blueprint('veiculos', __name__)

@bp.route('', methods=['GET'])
@jwt_required()
def listar_veiculos():
    veiculos = Veiculo.query.all()
    return jsonify([v.to_dict() for v in veiculos]), 200

@bp.route('/<int:veiculo_id>', methods=['GET'])
@jwt_required()
def obter_veiculo(veiculo_id):
    veiculo = Veiculo.query.get(veiculo_id)
    if not veiculo:
        return jsonify({'erro': 'Veículo não encontrado'}), 404
    return jsonify(veiculo.to_dict()), 200

@bp.route('/placa/<placa>', methods=['GET'])
@jwt_required()
def buscar_por_placa(placa):
    placa_normalizada = placa.upper().replace('-', '')
    veiculo = Veiculo.query.filter_by(placa=placa_normalizada).first()
    if not veiculo:
        return jsonify({'erro': 'Veículo não encontrado'}), 404
    return jsonify(veiculo.to_dict()), 200

@bp.route('', methods=['POST'])
@permission_required('gerenciar_veiculos')
def criar_veiculo():
    data = request.get_json()
    
    if not data or not data.get('placa') or not data.get('tipo'):
        return jsonify({'erro': 'Placa e tipo são obrigatórios'}), 400
    
    placa = data['placa'].upper().replace('-', '')
    
    if Veiculo.query.filter_by(placa=placa).first():
        return jsonify({'erro': 'Já existe um veículo com esta placa'}), 400
    
    if data.get('renavam') and Veiculo.query.filter_by(renavam=data['renavam']).first():
        return jsonify({'erro': 'Já existe um veículo com este RENAVAM'}), 400
    
    try:
        usuario_id = int(get_jwt_identity())
        
        veiculo = Veiculo(
            placa=placa,
            renavam=data.get('renavam'),
            tipo=data['tipo'],
            capacidade=data.get('capacidade'),
            marca=data.get('marca'),
            modelo=data.get('modelo'),
            ano=data.get('ano'),
            ativo=data.get('ativo', True),
            criado_por=usuario_id
        )
        
        db.session.add(veiculo)
        db.session.commit()
        
        registrar_criacao(usuario_id, 'veiculo', veiculo.id, {'placa': veiculo.placa})
        
        return jsonify(veiculo.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': str(e)}), 400

@bp.route('/<int:veiculo_id>', methods=['PUT'])
@permission_required('gerenciar_veiculos')
def atualizar_veiculo(veiculo_id):
    veiculo = Veiculo.query.get(veiculo_id)
    if not veiculo:
        return jsonify({'erro': 'Veículo não encontrado'}), 404
    
    data = request.get_json()
    
    if data.get('placa'):
        placa = data['placa'].upper().replace('-', '')
        if placa != veiculo.placa:
            if Veiculo.query.filter_by(placa=placa).first():
                return jsonify({'erro': 'Já existe um veículo com esta placa'}), 400
    
    if data.get('renavam') and data['renavam'] != veiculo.renavam:
        if Veiculo.query.filter_by(renavam=data['renavam']).first():
            return jsonify({'erro': 'Já existe um veículo com este RENAVAM'}), 400
    
    try:
        alteracoes = {}
        
        if 'placa' in data:
            placa = data['placa'].upper().replace('-', '')
            if placa != veiculo.placa:
                alteracoes['placa_antiga'] = veiculo.placa
                veiculo.placa = placa
        if 'renavam' in data:
            veiculo.renavam = data['renavam']
        if 'tipo' in data:
            veiculo.tipo = data['tipo']
        if 'capacidade' in data:
            veiculo.capacidade = data['capacidade']
        if 'marca' in data:
            veiculo.marca = data['marca']
        if 'modelo' in data:
            veiculo.modelo = data['modelo']
        if 'ano' in data:
            veiculo.ano = data['ano']
        if 'ativo' in data:
            veiculo.ativo = data['ativo']
        
        db.session.commit()
        
        usuario_id = int(get_jwt_identity())
        registrar_atualizacao(usuario_id, 'veiculo', veiculo.id, alteracoes)
        
        return jsonify(veiculo.to_dict()), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': str(e)}), 400

@bp.route('/<int:veiculo_id>', methods=['DELETE'])
@admin_required
def deletar_veiculo(veiculo_id):
    veiculo = Veiculo.query.get(veiculo_id)
    if not veiculo:
        return jsonify({'erro': 'Veículo não encontrado'}), 404
    
    try:
        usuario_id = int(get_jwt_identity())
        
        veiculo.ativo = False
        db.session.commit()
        
        registrar_atualizacao(usuario_id, 'veiculo', veiculo.id, {'ativo': False, 'acao': 'desativado'})
        
        return jsonify({'mensagem': 'Veículo desativado com sucesso'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': str(e)}), 400
