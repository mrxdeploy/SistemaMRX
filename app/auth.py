import bcrypt
from functools import wraps
from flask import jsonify, request
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity, get_jwt
from app.models import db, Usuario, Perfil
from app.rbac_config import check_rota_api_permitida, perfil_tem_motorista

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
PERFIL_ADMIN = 'Administrador'

def admin_ou_auditor_required(fn):
    """
    Decorator que permite acesso para usuários com permissão ao dashboard (antigo Admin e Auditor)
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

        # Agora checamos dinamicamente a permissão ao invés do nome de perfil fixo
        if usuario.has_permission('modulo_dashboard'):
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

        # Se for um usuário não-admin acessando métodos de escrita e estivermos limitando a leitura
        if request.method in ['POST', 'PUT', 'PATCH', 'DELETE']:
            # Aqui no novo RBAC as permissões de edição garantem quem pode escrever,
            # porém se um endpoint explícito demandar isso (como logs ou listagens amplas protegidas),
            # bloqueamos de forma genérica para usuários que apenas "tem permissão de ler o dashboard"
            # e queríamos prevenir modificações em massa.
            if usuario.has_permission('modulo_dashboard') and not usuario.has_permission('configuracoes_gerenciar'):
                pass # Por hora, a rota específica que devia validar vai gerenciar. Mas vamos manter um log de consistência.
                # Como essa função foi depreciada por causa dos claims de RBAC mais granulares, vamos deixar passar se for admin, senão checar.
            
            # Para não quebrar a lógica original: se o usuário SÓ tinha leitura:
            if usuario.perfil and usuario.perfil.nome == PERFIL_AUDITORIA:
                return jsonify({'erro': 'Perfil de Auditoria possui apenas acesso de leitura'}), 403

        return fn(*args, **kwargs)
    return wrapper

def get_user_jwt_claims(usuario):
    """
    Gera claims adicionais do JWT para incluir perfil e permissões do usuário
    """
    perfil_nome = None
    permissoes = {}
    permissoes_lista = []

    if usuario.tipo == 'admin':
        perfil_nome = 'Administrador'
        # Admin tem todas as permissões - serão geradas dinamicamente
        from app.rbac_config import PERMISSOES_CATALOGO
        for modulo_config in PERMISSOES_CATALOGO.values():
            for perm_key in modulo_config['permissoes']:
                permissoes[perm_key] = True
    elif usuario.perfil:
        perfil_nome = usuario.perfil.nome
        permissoes = usuario.perfil.permissoes or {}

    permissoes_lista = [k for k, v in permissoes.items() if v and k != 'menus_inferiores']

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
    from app.rbac_config import PERMISSOES_CATALOGO
    
    # Gerar permissões completas de admin dinamicamente
    admin_permissoes = {}
    for modulo_config in PERMISSOES_CATALOGO.values():
        for perm_key in modulo_config['permissoes']:
            admin_permissoes[perm_key] = True
    admin_permissoes['menus_inferiores'] = [
        {'id': 'dashboard', 'nome': 'Dashboard', 'url': '/dashboard.html', 'icone': 'dashboard'},
        {'id': 'solicitacoes', 'nome': 'Compra', 'url': '/solicitacoes.html', 'icone': 'request_quote'},
        {'id': 'fornecedores', 'nome': 'Fornecedores', 'url': '/fornecedores.html', 'icone': 'business'},
        {'id': 'estoque-ativo', 'nome': 'Estoque', 'url': '/estoque-ativo.html', 'icone': 'warehouse'},
    ]

    perfis = [
        {
            'nome': 'Administrador',
            'descricao': 'Acesso total ao sistema. Define limites, aprova exceções, gerencia usuários e perfis.',
            'permissoes': admin_permissoes
        },
        {
            'nome': 'Comprador (PJ)',
            'descricao': 'Abre solicitações de compra, cadastra fornecedores, gerencia tabelas de preço.',
            'permissoes': {
                'modulo_compras': True, 'solicitacao_criar': True, 'solicitacao_editar': True,
                'solicitacao_visualizar': True,
                'modulo_fornecedores': True, 'fornecedor_criar': True, 'fornecedor_editar': True,
                'fornecedor_visualizar': True, 'fornecedor_tabela_precos': True,
                'fornecedor_gerenciar_tabela_precos': True,
                'modulo_notificacoes': True,
                'menus_inferiores': [
                    {'id': 'solicitacoes', 'nome': 'Compra', 'url': '/solicitacoes.html', 'icone': 'request_quote'},
                    {'id': 'fornecedores', 'nome': 'Fornecedores', 'url': '/fornecedores.html', 'icone': 'business'},
                ]
            }
        },
        {
            'nome': 'Conferente / Estoque',
            'descricao': 'Valida chegada, confere qualidade, cria lotes e dá entrada no estoque.',
            'permissoes': {
                'modulo_conferencia': True, 'conferencia_criar': True, 'conferencia_validar': True,
                'conferencia_visualizar': True,
                'modulo_lotes': True, 'lote_criar': True, 'lote_visualizar': True,
                'modulo_estoque_ativo': True, 'estoque_entrada': True, 'estoque_visualizar': True,
                'modulo_dashboard': True, 'dashboard_visualizar_metricas': True,
                'modulo_notificacoes': True,
                'menus_inferiores': [
                    {'id': 'conferencia', 'nome': 'Conferência', 'url': '/conferencia.html', 'icone': 'fact_check'},
                    {'id': 'lotes', 'nome': 'Lotes', 'url': '/lotes.html', 'icone': 'inventory_2'},
                    {'id': 'estoque-ativo', 'nome': 'Estoque', 'url': '/estoque-ativo.html', 'icone': 'warehouse'},
                    {'id': 'dashboard', 'nome': 'Dashboard', 'url': '/dashboard.html', 'icone': 'dashboard'},
                ]
            }
        },
        {
            'nome': 'Separação',
            'descricao': 'Separa lotes por material/condição; gera sublotes e resíduos.',
            'permissoes': {
                'modulo_separacao': True, 'separacao_fila': True, 'separacao_workflow': True,
                'separacao_criar_sublote': True, 'separacao_marcar_residuo': True,
                'modulo_lotes': True, 'lote_visualizar': True,
                'modulo_dashboard': True, 'dashboard_visualizar_metricas': True,
                'modulo_notificacoes': True,
                'menus_inferiores': [
                    {'id': 'separacao-fila', 'nome': 'Separação', 'url': '/separacao-fila.html', 'icone': 'format_list_bulleted'},
                    {'id': 'lotes', 'nome': 'Lotes', 'url': '/lotes.html', 'icone': 'inventory_2'},
                    {'id': 'dashboard', 'nome': 'Dashboard', 'url': '/dashboard.html', 'icone': 'dashboard'},
                ]
            }
        },
        {
            'nome': 'Motorista',
            'descricao': 'Recebe rotas, realiza coletas e envia comprovantes/fotos.',
            'permissoes': {
                'modulo_motorista': True, 'motorista_app': True,
                'motorista_visualizar_os': True, 'motorista_atualizar_os': True,
                'motorista_enviar_comprovante': True,
                'modulo_notificacoes': True,
                'menus_inferiores': [
                    {'id': 'app-motorista', 'nome': 'Meu App', 'url': '/app-motorista.html', 'icone': 'local_shipping'},
                    {'id': 'notificacoes', 'nome': 'Notificações', 'url': '/notificacoes.html', 'icone': 'notifications'},
                ]
            }
        },
        {
            'nome': 'Financeiro',
            'descricao': 'Visualiza solicitações, fornecedores e lotes para controle financeiro.',
            'permissoes': {
                'modulo_dashboard': True, 'dashboard_visualizar_metricas': True,
                'dashboard_visualizar_graficos': True,
                'modulo_compras': True, 'solicitacao_visualizar': True,
                'modulo_fornecedores': True, 'fornecedor_visualizar': True,
                'modulo_lotes': True, 'lote_visualizar': True,
                'modulo_notificacoes': True,
                'menus_inferiores': [
                    {'id': 'dashboard', 'nome': 'Dashboard', 'url': '/dashboard.html', 'icone': 'dashboard'},
                    {'id': 'solicitacoes', 'nome': 'Compra', 'url': '/solicitacoes.html', 'icone': 'request_quote'},
                    {'id': 'fornecedores', 'nome': 'Fornecedores', 'url': '/fornecedores.html', 'icone': 'business'},
                    {'id': 'lotes', 'nome': 'Lotes', 'url': '/lotes.html', 'icone': 'inventory_2'},
                ]
            }
        },
        {
            'nome': 'Auditoria / BI',
            'descricao': 'Acesso apenas leitura aos painéis e trilhas de auditoria.',
            'permissoes': {
                'modulo_auditoria': True, 'auditoria_somente_leitura': True,
                'auditoria_exportar': True,
                'modulo_dashboard': True, 'dashboard_visualizar_metricas': True,
                'dashboard_visualizar_graficos': True, 'dashboard_exportar': True,
                'menus_inferiores': []
            }
        },
        {
            'nome': 'Gestor',
            'descricao': 'Perfil de gestão com acesso amplo a compras, fornecedores, estoque e WMS.',
            'permissoes': {
                'modulo_compras': True, 'solicitacao_criar': True, 'solicitacao_editar': True,
                'solicitacao_visualizar': True, 'solicitacao_aprovar': True,
                'modulo_fornecedores': True, 'fornecedor_criar': True, 'fornecedor_editar': True,
                'fornecedor_visualizar': True, 'fornecedor_tabela_precos': True,
                'fornecedor_gerenciar_tabela_precos': True,
                'modulo_estoque_ativo': True, 'estoque_visualizar': True, 'estoque_movimentar': True,
                'modulo_lotes': True, 'lote_visualizar': True, 'lote_editar': True,
                'modulo_separacao': True, 'separacao_fila': True, 'separacao_workflow': True,
                'modulo_notificacoes': True,
                'menus_inferiores': [
                    {'id': 'solicitacoes', 'nome': 'Compra', 'url': '/solicitacoes.html', 'icone': 'request_quote'},
                    {'id': 'fornecedores', 'nome': 'Fornecedores', 'url': '/fornecedores.html', 'icone': 'business'},
                    {'id': 'estoque-ativo', 'nome': 'Estoque', 'url': '/estoque-ativo.html', 'icone': 'warehouse'},
                    {'id': 'lotes', 'nome': 'Lotes', 'url': '/lotes.html', 'icone': 'inventory_2'},
                ]
            }
        },
        {
            'nome': 'Producao',
            'descricao': 'Perfil para equipe de produção com acesso a compras, fornecedores e estoque.',
            'permissoes': {
                'modulo_compras': True, 'solicitacao_criar': True, 'solicitacao_editar': True,
                'solicitacao_visualizar': True,
                'modulo_fornecedores': True, 'fornecedor_criar': True, 'fornecedor_editar': True,
                'fornecedor_visualizar': True, 'fornecedor_tabela_precos': True,
                'fornecedor_gerenciar_tabela_precos': True,
                'modulo_estoque_ativo': True, 'estoque_visualizar': True,
                'modulo_notificacoes': True,
                'menus_inferiores': [
                    {'id': 'solicitacoes', 'nome': 'Compra', 'url': '/solicitacoes.html', 'icone': 'request_quote'},
                    {'id': 'fornecedores', 'nome': 'Fornecedores', 'url': '/fornecedores.html', 'icone': 'business'},
                    {'id': 'estoque-ativo', 'nome': 'Estoque', 'url': '/estoque-ativo.html', 'icone': 'warehouse'},
                ]
            }
        },
    ]

    perfis_existentes = {p.nome: p for p in Perfil.query.all()}

    for perfil_data in perfis:
        nome = perfil_data['nome']
        if nome in perfis_existentes:
            # Atualizar permissões do perfil existente para o novo formato
            perfil_existente = perfis_existentes[nome]
            perfil_existente.permissoes = perfil_data['permissoes']
            perfil_existente.descricao = perfil_data['descricao']
            perfil_existente.ativo = True
            print(f'Perfil atualizado: {nome}')
        else:
            perfil = Perfil(**perfil_data)
            db.session.add(perfil)
            print(f'Perfil criado: {nome}')

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