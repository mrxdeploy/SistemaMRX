import bcrypt
from functools import wraps
from flask import jsonify, request
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity, get_jwt
from app.models import db, Usuario, Perfil
from app.rbac_config import check_rota_api_permitida

def hash_senha(senha):
    return bcrypt.hashpw(senha.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verificar_senha(senha, senha_hash):
    return bcrypt.checkpw(senha.encode('utf-8'), senha_hash.encode('utf-8'))

def get_current_user():
    verify_jwt_in_request()
    usuario_id = get_jwt_identity()
    return Usuario.query.get(usuario_id)

def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        usuario = get_current_user()

        if not usuario or usuario.tipo != 'admin':
            return jsonify({'erro': 'Acesso negado. Apenas administradores podem acessar este recurso.'}), 403

        return fn(*args, **kwargs)
    return wrapper

def permission_required(permission: str):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            usuario = get_current_user()

            if not usuario:
                return jsonify({'erro': 'Usuário não autenticado'}), 401

            if usuario.tipo == 'admin':
                return fn(*args, **kwargs)

            if not usuario.has_permission(permission):
                return jsonify({'erro': f'Acesso negado. Permissão necessária: {permission}'}), 403

            return fn(*args, **kwargs)
        return wrapper
    return decorator

def perfil_required(*perfis_permitidos):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            usuario = get_current_user()

            if not usuario or not usuario.perfil:
                return jsonify({'erro': 'Usuário sem perfil definido'}), 403

            if usuario.perfil.nome not in perfis_permitidos and usuario.tipo != 'admin':
                return jsonify({'erro': f'Acesso negado. Perfis permitidos: {", ".join(perfis_permitidos)}'}), 403

            return fn(*args, **kwargs)
        return wrapper
    return decorator

PERFIL_AUDITORIA = 'Auditoria / BI'

def admin_ou_auditor_required(fn):
    """
    Decorator que permite acesso para Admin e Auditor
    Usado principalmente para rotas de dashboard e relatórios
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        usuario = get_current_user()

        if not usuario:
            return jsonify({'erro': 'Usuário não autenticado'}), 401

        # Admin tem acesso total
        if usuario.tipo == 'admin':
            return fn(*args, **kwargs)

        # Auditor também tem acesso total ao dashboard
        if usuario.perfil and usuario.perfil.nome == PERFIL_AUDITORIA:
            return fn(*args, **kwargs)

        return jsonify({'erro': 'Acesso negado. Apenas Administradores e Auditores podem acessar este recurso.'}), 403

    return wrapper

def somente_leitura_ou_admin(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        usuario = get_current_user()

        if not usuario:
            return jsonify({'erro': 'Usuário não autenticado'}), 401

        if usuario.tipo == 'admin':
            return fn(*args, **kwargs)

        if usuario.perfil and usuario.perfil.nome == PERFIL_AUDITORIA:
            if request.method in ['POST', 'PUT', 'PATCH', 'DELETE']:
                return jsonify({'erro': 'Perfil Auditoria / BI possui apenas acesso de leitura'}), 403

        return fn(*args, **kwargs)
    return wrapper

def get_user_jwt_claims(usuario):
    """
    Gera claims adicionais do JWT para incluir perfil e permissões do usuário
    """
    perfil_nome = None
    permissoes = {}
    permissoes_lista = []

    if usuario.perfil:
        perfil_nome = usuario.perfil.nome
        permissoes = usuario.perfil.permissoes or {}
    elif usuario.tipo == 'admin':
        perfil_nome = 'Administrador'
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

    permissoes_lista = [k for k, v in permissoes.items() if v]

    return {
        'perfil': perfil_nome,
        'tipo': usuario.tipo,
        'permissoes': permissoes_lista,
        'nome': usuario.nome,
        'email': usuario.email
    }

def rota_permitida_por_perfil(fn):
    """
    Decorator que valida se a rota é permitida para o perfil do usuário
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        usuario = get_current_user()

        if not usuario:
            return jsonify({'erro': 'Usuário não autenticado'}), 401

        if usuario.tipo == 'admin':
            return fn(*args, **kwargs)

        claims = get_jwt()
        perfil_nome = claims.get('perfil')

        if not perfil_nome:
            return jsonify({'erro': 'Perfil não definido no token'}), 403

        rota_atual = request.path

        if not check_rota_api_permitida(perfil_nome, rota_atual):
            return jsonify({
                'erro': 'Acesso negado',
                'mensagem': f'O perfil {perfil_nome} não tem permissão para acessar esta rota'
            }), 403

        return fn(*args, **kwargs)
    return wrapper

def criar_perfis_padrao():
    perfis_existentes = {p.nome for p in Perfil.query.all()}

    perfis = [
        {
            'nome': 'Administrador',
            'descricao': 'Acesso total; define limites; aprova exceções; autoriza descarte; fecha inventário; gerencia usuários e perfis.',
            'permissoes': {
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
        },
        {
            'nome': 'Comprador (PJ)',
            'descricao': 'Abre solicitações de compra, cadastra fornecedores, informa entregas/coletas e registra preço pago.',
            'permissoes': {
                'criar_fornecedor': True,
                'editar_fornecedor': True,
                'criar_solicitacao': True,
                'visualizar_solicitacao': True,
                'informar_entrega': True,
                'registrar_preco': True,
                'visualizar_fornecedores': True,
                'gerenciar_tabela_precos': True,
                'visualizar_materiais': True
            }
        },
        {
            'nome': 'Conferente / Estoque',
            'descricao': 'Valida chegada, pesa, confere itens e qualidade; cria lotes e dá entrada no estoque.',
            'permissoes': {
                'validar_chegada': True,
                'pesar_itens': True,
                'conferir_qualidade': True,
                'criar_lote': True,
                'dar_entrada_estoque': True,
                'visualizar_lotes': True,
                'visualizar_entradas': True
            }
        },
        {
            'nome': 'Separação',
            'descricao': 'Separa lotes por material/condição; gera sublotes e resíduos para descarte (com aprovação ADM).',
            'permissoes': {
                'separar_lotes': True,
                'criar_sublotes': True,
                'marcar_residuos': True,
                'visualizar_lotes': True,
                'solicitar_descarte': True
            }
        },
        {
            'nome': 'Motorista',
            'descricao': 'Recebe rotas, realiza coletas e envia comprovantes/fotos.',
            'permissoes': {
                'visualizar_rotas': True,
                'registrar_coleta': True,
                'enviar_comprovante': True,
                'enviar_fotos': True,
                'visualizar_dados_pessoais': True
            }
        },
        {
            'nome': 'Financeiro',
            'descricao': 'Emite notas, controla pagamentos e conciliação bancária.',
            'permissoes': {
                'emitir_notas': True,
                'controlar_pagamentos': True,
                'conciliacao_bancaria': True,
                'visualizar_fornecedores': True,
                'visualizar_solicitacoes': True,
                'exportar_relatorios': True
            }
        },
        {
            'nome': 'Auditoria / BI',
            'descricao': 'Acesso apenas leitura aos painéis e trilhas de auditoria.',
            'permissoes': {
                'visualizar_auditoria': True,
                'visualizar_paineis': True,
                'visualizar_relatorios': True,
                'exportar_relatorios': True,
                'visualizar_usuarios': True,
                'visualizar_fornecedores': True,
                'visualizar_solicitacoes': True,
                'visualizar_lotes': True,
                'visualizar_entradas': True,
                'somente_leitura': True
            }
        }
    ]

    for perfil_data in perfis:
        if perfil_data['nome'] not in perfis_existentes:
            perfil = Perfil(**perfil_data)
            db.session.add(perfil)
            print(f'Perfil criado: {perfil_data["nome"]}')

    db.session.commit()

def criar_admin_padrao():
    import os

    criar_perfis_padrao()

    admin_count = Usuario.query.filter_by(tipo='admin').count()

    if admin_count == 0:
        admin_email = os.getenv('ADMIN_EMAIL', 'admin@sistema.com')
        admin_password = os.getenv('ADMIN_PASSWORD', 'admin123')

        perfil_admin = Perfil.query.filter_by(nome='Administrador').first()

        admin = Usuario(
            nome='Administrador',
            email=admin_email,
            senha_hash=hash_senha(admin_password),
            tipo='admin',
            perfil_id=perfil_admin.id if perfil_admin else None
        )
        db.session.add(admin)
        db.session.commit()
        print(f'Usuário administrador criado: {admin_email}')

        if admin_password == 'admin123':
            print('AVISO: Usando senha padrão! Configure ADMIN_EMAIL e ADMIN_PASSWORD nas variáveis de ambiente.')