from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app.models import db, Perfil
from app.auth import admin_required
from app.utils.auditoria import registrar_criacao, registrar_atualizacao, registrar_exclusao
from flask_jwt_extended import get_jwt_identity

bp = Blueprint('perfis', __name__, url_prefix='/api/perfis')

@bp.route('', methods=['GET'])
@jwt_required()
def listar_perfis():
    perfis = Perfil.query.filter_by(ativo=True).all()
    return jsonify([p.to_dict() for p in perfis]), 200

@bp.route('/<int:perfil_id>', methods=['GET'])
@jwt_required()
def obter_perfil(perfil_id):
    perfil = Perfil.query.get(perfil_id)
    if not perfil:
        return jsonify({'erro': 'Perfil não encontrado'}), 404
    return jsonify(perfil.to_dict()), 200

@bp.route('', methods=['POST'])
@admin_required
def criar_perfil():
    data = request.get_json()
    
    if not data or not data.get('nome'):
        return jsonify({'erro': 'Nome do perfil é obrigatório'}), 400
    
    if Perfil.query.filter_by(nome=data['nome']).first():
        return jsonify({'erro': 'Já existe um perfil com este nome'}), 400
    
    try:
        perfil = Perfil(
            nome=data['nome'],
            descricao=data.get('descricao'),
            permissoes=data.get('permissoes', {}),
            ativo=data.get('ativo', True)
        )
        
        db.session.add(perfil)
        db.session.commit()
        
        usuario_id = int(get_jwt_identity())
        registrar_criacao(usuario_id, 'perfil', perfil.id, {'nome': perfil.nome})
        
        return jsonify(perfil.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': str(e)}), 400

@bp.route('/<int:perfil_id>', methods=['PUT'])
@admin_required
def atualizar_perfil(perfil_id):
    perfil = Perfil.query.get(perfil_id)
    if not perfil:
        return jsonify({'erro': 'Perfil não encontrado'}), 404
    
    data = request.get_json()
    
    if data.get('nome') and data['nome'] != perfil.nome:
        if Perfil.query.filter_by(nome=data['nome']).first():
            return jsonify({'erro': 'Já existe um perfil com este nome'}), 400
    
    try:
        alteracoes = {}
        
        if 'nome' in data:
            alteracoes['nome_antigo'] = perfil.nome
            perfil.nome = data['nome']
        if 'descricao' in data:
            perfil.descricao = data['descricao']
        if 'permissoes' in data:
            alteracoes['permissoes_alteradas'] = True
            perfil.permissoes = data['permissoes']
        if 'ativo' in data:
            perfil.ativo = data['ativo']
        
        db.session.commit()
        
        usuario_id = int(get_jwt_identity())
        registrar_atualizacao(usuario_id, 'perfil', perfil.id, alteracoes)
        
        return jsonify(perfil.to_dict()), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': str(e)}), 400

@bp.route('/<int:perfil_id>', methods=['DELETE'])
@admin_required
def deletar_perfil(perfil_id):
    perfil = Perfil.query.get(perfil_id)
    if not perfil:
        return jsonify({'erro': 'Perfil não encontrado'}), 404
    
    if perfil.nome in ['Administrador', 'Comprador (PJ)', 'Conferente / Estoque', 
                       'Separação', 'Motorista', 'Financeiro', 'Auditoria / BI']:
        return jsonify({'erro': 'Não é possível deletar perfis padrão do sistema'}), 400
    
    if perfil.usuarios:
        return jsonify({'erro': 'Não é possível deletar perfil com usuários associados'}), 400
    
    try:
        usuario_id = int(get_jwt_identity())
        registrar_exclusao(usuario_id, 'perfil', perfil.id, {'nome': perfil.nome})
        
        db.session.delete(perfil)
        db.session.commit()
        
        return jsonify({'mensagem': 'Perfil deletado com sucesso'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': str(e)}), 400
