from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token, 
    create_refresh_token,
    jwt_required, 
    get_jwt_identity,
    get_jwt
)
from app.models import db, Usuario
from app.auth import verificar_senha, get_user_jwt_claims
from app.utils.auditoria import registrar_login
from app.rbac_config import get_menus_by_perfil, get_tela_inicial_by_perfil, get_paginas_permitidas, get_ocultar_menu_inferior, get_ocultar_botao_adicionar

bp = Blueprint('auth', __name__, url_prefix='/api/auth')

@bp.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        
        if not data or not data.get('email') or not data.get('senha'):
            return jsonify({'erro': 'Email e senha são obrigatórios'}), 400
        
        usuario = Usuario.query.filter_by(email=data['email']).first()
        
        if not usuario:
            return jsonify({'erro': 'Email ou senha incorretos'}), 401
        
        # Tentar verificar senha com tratamento de erro
        try:
            senha_valida = verificar_senha(data['senha'], usuario.senha_hash)
        except (ValueError, Exception) as e:
            print(f'Erro ao verificar senha para {usuario.email}: {e}')
            registrar_login(usuario.id, sucesso=False)
            return jsonify({'erro': 'Erro ao verificar credenciais. Por favor, contate o administrador.'}), 500
        
        if not senha_valida:
            registrar_login(usuario.id, sucesso=False)
            return jsonify({'erro': 'Email ou senha incorretos'}), 401
    except Exception as e:
        print(f'Erro no login: {e}')
        return jsonify({'erro': 'Erro interno no servidor'}), 500
    
    if not usuario.ativo:
        return jsonify({'erro': 'Usuário inativo. Entre em contato com o administrador.'}), 403
    
    additional_claims = get_user_jwt_claims(usuario)
    access_token = create_access_token(identity=str(usuario.id), additional_claims=additional_claims)
    refresh_token = create_refresh_token(identity=str(usuario.id), additional_claims=additional_claims)
    
    registrar_login(usuario.id, sucesso=True)
    
    # Determinar o perfil do usuário
    if usuario.tipo == 'admin':
        perfil_nome = 'Administrador'
    elif usuario.tipo == 'motorista':
        perfil_nome = 'Motorista'
    elif usuario.perfil:
        perfil_nome = usuario.perfil.nome
    else:
        perfil_nome = 'Sem perfil'
    
    permissoes = {}
    if usuario.tipo == 'motorista':
        permissoes = {
            'visualizar_os': True,
            'atualizar_os': True
        }
    elif usuario.perfil:
        permissoes = usuario.perfil.permissoes or {}
    elif usuario.tipo == 'admin':
        permissoes = {
            'gerenciar_usuarios': True,
            'gerenciar_perfis': True,
            'gerenciar_fornecedores': True,
            'gerenciar_veiculos': True,
            'gerenciar_motoristas': True,
            'criar_solicitacao': True,
            'aprovar_solicitacao': True,
            'rejeitar_solicitacao': True,
            'criar_lote': True,
            'aprovar_lote': True,
            'processar_entrada': True,
            'visualizar_auditoria': True,
            'exportar_relatorios': True,
            'definir_limites': True,
            'autorizar_descarte': True
        }
    
    tela_inicial = get_tela_inicial_by_perfil(perfil_nome)
    
    usuario_dict = usuario.to_dict()
    usuario_dict['permissoes'] = permissoes
    usuario_dict['perfil'] = perfil_nome
    usuario_dict['tela_inicial'] = tela_inicial
    
    return jsonify({
        'token': access_token,
        'refresh_token': refresh_token,
        'usuario': usuario_dict
    }), 200

@bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    usuario_id = int(get_jwt_identity())
    usuario = Usuario.query.get(usuario_id)
    
    if not usuario or not usuario.ativo:
        return jsonify({'erro': 'Usuário não encontrado ou inativo'}), 404
    
    additional_claims = get_user_jwt_claims(usuario)
    access_token = create_access_token(identity=str(usuario.id), additional_claims=additional_claims)
    
    return jsonify({
        'token': access_token
    }), 200

@bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user_endpoint():
    usuario_id = int(get_jwt_identity())
    usuario = Usuario.query.get(usuario_id)
    
    if not usuario:
        return jsonify({'erro': 'Usuário não encontrado'}), 404
    
    claims = get_jwt()
    
    # Determinar o perfil do usuário
    if usuario.tipo == 'admin':
        perfil_nome = 'Administrador'
    elif usuario.tipo == 'motorista':
        perfil_nome = 'Motorista'
    elif usuario.perfil:
        perfil_nome = usuario.perfil.nome
    else:
        perfil_nome = claims.get('perfil', 'Sem perfil')
    
    permissoes = {}
    permissoes_lista = []
    
    if usuario.tipo == 'motorista':
        permissoes = {
            'visualizar_os': True,
            'atualizar_os': True
        }
        permissoes_lista = list(permissoes.keys())
    elif usuario.perfil:
        permissoes = usuario.perfil.permissoes or {}
        permissoes_lista = [k for k, v in permissoes.items() if v]
    elif usuario.tipo == 'admin':
        permissoes = {
            'gerenciar_usuarios': True,
            'gerenciar_perfis': True,
            'gerenciar_fornecedores': True,
            'gerenciar_veiculos': True,
            'gerenciar_motoristas': True,
            'criar_solicitacao': True,
            'aprovar_solicitacao': True,
            'rejeitar_solicitacao': True,
            'criar_lote': True,
            'aprovar_lote': True,
            'processar_entrada': True,
            'visualizar_auditoria': True,
            'exportar_relatorios': True,
            'definir_limites': True,
            'autorizar_descarte': True
        }
        permissoes_lista = list(permissoes.keys())
    
    tela_inicial = get_tela_inicial_by_perfil(perfil_nome)
    
    usuario_dict = usuario.to_dict()
    usuario_dict['perfil'] = perfil_nome
    usuario_dict['permissoes'] = permissoes_lista
    usuario_dict['permissoes_detalhadas'] = permissoes
    usuario_dict['tela_inicial'] = tela_inicial
    
    return jsonify(usuario_dict), 200

@bp.route('/menus', methods=['GET'])
@jwt_required()
def get_menus():
    claims = get_jwt()
    perfil_nome = claims.get('perfil')
    
    if not perfil_nome:
        return jsonify({'erro': 'Perfil não definido'}), 403
    
    menus = get_menus_by_perfil(perfil_nome)
    paginas_permitidas = get_paginas_permitidas(perfil_nome)
    ocultar_menu = get_ocultar_menu_inferior(perfil_nome)
    ocultar_botao = get_ocultar_botao_adicionar(perfil_nome)
    
    return jsonify({
        'perfil': perfil_nome,
        'menus': menus,
        'paginas_permitidas': paginas_permitidas,
        'ocultar_menu_inferior': ocultar_menu,
        'ocultar_botao_adicionar': ocultar_botao
    }), 200
