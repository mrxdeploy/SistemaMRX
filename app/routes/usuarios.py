from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app.models import db, Usuario
from app.auth import admin_required, hash_senha

bp = Blueprint('usuarios', __name__, url_prefix='/api/usuarios')

@bp.route('', methods=['GET'])
@admin_required
def listar_usuarios():
    usuarios = Usuario.query.all()
    return jsonify([usuario.to_dict() for usuario in usuarios]), 200

@bp.route('/<int:id>', methods=['GET'])
@admin_required
def obter_usuario(id):
    usuario = Usuario.query.get(id)
    
    if not usuario:
        return jsonify({'erro': 'Usuário não encontrado'}), 404
    
    return jsonify(usuario.to_dict()), 200

@bp.route('', methods=['POST'])
@admin_required
def criar_usuario():
    from flask_jwt_extended import get_jwt_identity
    data = request.get_json()
    
    if not data or not data.get('nome') or not data.get('email') or not data.get('senha'):
        return jsonify({'erro': 'Nome, email e senha são obrigatórios'}), 400
    
    if not data.get('perfil_id'):
        return jsonify({'erro': 'Perfil é obrigatório'}), 400
    
    usuario_existente = Usuario.query.filter_by(email=data['email']).first()
    if usuario_existente:
        return jsonify({'erro': 'Email já cadastrado'}), 400
    
    from app.models import Perfil
    perfil = Perfil.query.get(data['perfil_id'])
    if not perfil:
        return jsonify({'erro': 'Perfil não encontrado'}), 404
    
    tipo = 'admin' if perfil.nome == 'Administrador' else 'funcionario'
    
    usuario = Usuario(
        nome=data['nome'],
        email=data['email'],
        senha_hash=hash_senha(data['senha']),
        tipo=tipo,
        perfil_id=data['perfil_id'],
        criado_por=get_jwt_identity()
    )
    
    db.session.add(usuario)
    db.session.commit()
    
    from app.utils.auditoria import registrar_criacao
    registrar_criacao(get_jwt_identity(), 'Usuario', usuario.id, {
        'nome': usuario.nome,
        'email': usuario.email,
        'perfil': perfil.nome
    })
    
    return jsonify(usuario.to_dict()), 201

@bp.route('/<int:id>', methods=['PUT'])
@admin_required
def atualizar_usuario(id):
    from flask_jwt_extended import get_jwt_identity
    usuario = Usuario.query.get(id)
    
    if not usuario:
        return jsonify({'erro': 'Usuário não encontrado'}), 404
    
    data = request.get_json()
    alteracoes = {}
    
    if data.get('nome'):
        alteracoes['nome_anterior'] = usuario.nome
        usuario.nome = data['nome']
        alteracoes['nome_novo'] = data['nome']
    
    if data.get('email'):
        alteracoes['email_anterior'] = usuario.email
        usuario.email = data['email']
        alteracoes['email_novo'] = data['email']
    
    if data.get('senha'):
        usuario.senha_hash = hash_senha(data['senha'])
        alteracoes['senha_alterada'] = True
    
    if data.get('perfil_id'):
        from app.models import Perfil
        perfil = Perfil.query.get(data['perfil_id'])
        if not perfil:
            return jsonify({'erro': 'Perfil não encontrado'}), 404
        
        alteracoes['perfil_anterior'] = usuario.perfil.nome if usuario.perfil else None
        usuario.perfil_id = data['perfil_id']
        usuario.tipo = 'admin' if perfil.nome == 'Administrador' else 'funcionario'
        alteracoes['perfil_novo'] = perfil.nome
    
    db.session.commit()
    
    from app.utils.auditoria import registrar_atualizacao
    registrar_atualizacao(get_jwt_identity(), 'Usuario', usuario.id, alteracoes)
    
    return jsonify(usuario.to_dict()), 200

@bp.route('/<int:id>', methods=['DELETE'])
@admin_required
def deletar_usuario(id):
    usuario = Usuario.query.get(id)
    
    if not usuario:
        return jsonify({'erro': 'Usuário não encontrado'}), 404
    
    if usuario.tipo == 'admin':
        admins = Usuario.query.filter_by(tipo='admin').count()
        if admins <= 1:
            return jsonify({'erro': 'Não é possível deletar o único administrador do sistema'}), 400
    
    db.session.delete(usuario)
    db.session.commit()
    
    return jsonify({'mensagem': 'Usuário deletado com sucesso'}), 200
