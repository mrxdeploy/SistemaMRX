"""
Sistema Dinâmico de Permissões e RBAC - MRX Systems
Todas as permissões são armazenadas no campo JSON 'permissoes' do modelo Perfil.
Este módulo define o catálogo de permissões e gera configuração dinâmica.
"""

# ============================================================
# CATÁLOGO MASTER DE PERMISSÕES
# Organizado por módulos. Cada módulo tem:
#   nome, icone, cor, permissoes, paginas, apis, menu
# ============================================================

PERMISSOES_CATALOGO = {
    'dashboard': {
        'nome': 'Dashboard',
        'icone': 'fas fa-chart-pie',
        'cor': '#3b82f6',
        'permissoes': {
            'modulo_dashboard': 'Acesso ao Dashboard',
            'dashboard_visualizar_metricas': 'Visualizar métricas gerais',
            'dashboard_visualizar_graficos': 'Visualizar gráficos',
            'dashboard_exportar': 'Exportar dados do dashboard',
        },
        'paginas': ['/dashboard.html'],
        'apis': ['/api/dashboard'],
        'menu': {'id': 'dashboard', 'nome': 'Dashboard', 'url': '/dashboard.html', 'icone': 'dashboard'},
    },
    'fornecedores': {
        'nome': 'Fornecedores',
        'icone': 'fas fa-building',
        'cor': '#059669',
        'permissoes': {
            'modulo_fornecedores': 'Acesso ao módulo Fornecedores',
            'fornecedor_criar': 'Cadastrar fornecedor',
            'fornecedor_editar': 'Editar fornecedor',
            'fornecedor_excluir': 'Excluir/desativar fornecedor',
            'fornecedor_visualizar': 'Visualizar fornecedores',
            'fornecedor_tabela_precos': 'Acessar tabela de preços',
            'fornecedor_gerenciar_tabela_precos': 'Criar/editar tabela de preços',
            'fornecedor_atribuir_comprador': 'Atribuir comprador responsável',
        },
        'paginas': ['/fornecedores.html', '/fornecedores-lista.html', '/fornecedor-tabela-precos.html', '/revisao-tabela-precos.html'],
        'apis': ['/api/fornecedores', '/api/fornecedor-tabela-precos', '/api/materiais-base', '/api/vendedores', '/api/fornecedor-tipo-lote'],
        'menu': {'id': 'fornecedores', 'nome': 'Fornecedores', 'url': '/fornecedores.html', 'icone': 'business'},
    },
    'compras': {
        'nome': 'Compras (Solicitações)',
        'icone': 'fas fa-file-alt',
        'cor': '#059669',
        'permissoes': {
            'modulo_compras': 'Acesso ao módulo de Compras',
            'solicitacao_criar': 'Criar solicitação de compra',
            'solicitacao_editar': 'Editar solicitação',
            'solicitacao_aprovar': 'Aprovar solicitação',
            'solicitacao_rejeitar': 'Rejeitar solicitação',
            'solicitacao_visualizar': 'Visualizar solicitações',
            'solicitacao_excluir': 'Excluir solicitação',
        },
        'paginas': ['/solicitacoes.html', '/compras.html', '/compra-rapida.html', '/wizard-compra.html', '/consulta.html', '/funcionario.html'],
        'apis': ['/api/solicitacoes', '/api/ordens-compra', '/api/compras'],
        'menu': {'id': 'solicitacoes', 'nome': 'Compra', 'url': '/solicitacoes.html', 'icone': 'request_quote'},
    },
    'logistica': {
        'nome': 'Logística',
        'icone': 'fas fa-truck',
        'cor': '#10b981',
        'permissoes': {
            'modulo_logistica': 'Acesso ao módulo de Logística',
            'os_criar': 'Criar ordem de serviço',
            'os_editar': 'Editar ordem de serviço',
            'os_visualizar': 'Visualizar ordens de serviço',
            'os_atribuir_motorista': 'Atribuir motorista a OS',
        },
        'paginas': ['/logistica.html'],
        'apis': ['/api/os'],
        'menu': {'id': 'logistica', 'nome': 'Logística', 'url': '/logistica.html', 'icone': 'local_shipping'},
    },
    'conferencia': {
        'nome': 'Conferência',
        'icone': 'fas fa-clipboard-check',
        'cor': '#14b8a6',
        'permissoes': {
            'modulo_conferencia': 'Acesso ao módulo de Conferência',
            'conferencia_criar': 'Criar conferência',
            'conferencia_validar': 'Validar conferência',
            'conferencia_decisao_adm': 'Decisão administrativa',
            'conferencia_visualizar': 'Visualizar conferências',
        },
        'paginas': ['/conferencia.html', '/conferencia-form.html', '/conferencia-decisao-adm.html', '/conferencias.html'],
        'apis': ['/api/conferencia', '/api/conferencias'],
        'menu': {'id': 'conferencia', 'nome': 'Conferência', 'url': '/conferencia.html', 'icone': 'fact_check'},
    },
    'lotes': {
        'nome': 'Lotes / WMS',
        'icone': 'fas fa-boxes',
        'cor': '#3b82f6',
        'permissoes': {
            'modulo_lotes': 'Acesso ao módulo de Lotes',
            'lote_criar': 'Criar lote',
            'lote_editar': 'Editar lote',
            'lote_aprovar': 'Aprovar lote',
            'lote_visualizar': 'Visualizar lotes',
            'lote_bloquear': 'Bloquear/desbloquear lote',
            'lote_reservar': 'Reservar lote',
        },
        'paginas': ['/lotes.html', '/lotes_aprovados.html', '/lotes-recebidos.html'],
        'apis': ['/api/lotes', '/api/wms'],
        'menu': {'id': 'lotes', 'nome': 'Lotes', 'url': '/lotes.html', 'icone': 'inventory_2'},
    },
    'separacao': {
        'nome': 'Separação',
        'icone': 'fas fa-list-ol',
        'cor': '#ef4444',
        'permissoes': {
            'modulo_separacao': 'Acesso ao módulo de Separação',
            'separacao_fila': 'Acessar fila de separação',
            'separacao_workflow': 'Executar workflow de separação',
            'separacao_criar_sublote': 'Criar sublotes',
            'separacao_marcar_residuo': 'Marcar resíduos',
        },
        'paginas': ['/separacao-fila.html', '/separacao-workflow.html'],
        'apis': ['/api/separacao'],
        'menu': {'id': 'separacao-fila', 'nome': 'Separação', 'url': '/separacao-fila.html', 'icone': 'format_list_bulleted'},
    },
    'estoque_ativo': {
        'nome': 'Estoque Ativo',
        'icone': 'fas fa-warehouse',
        'cor': '#0891b2',
        'permissoes': {
            'modulo_estoque_ativo': 'Acesso ao Estoque Ativo',
            'estoque_visualizar': 'Visualizar estoque',
            'estoque_movimentar': 'Movimentar estoque',
            'estoque_entrada': 'Dar entrada no estoque',
            'estoque_historico': 'Ver histórico de movimentações',
        },
        'paginas': ['/estoque-ativo.html', '/entradas.html', '/validacao.html'],
        'apis': ['/api/estoque', '/api/estoque-ativo', '/api/entradas', '/api/producao'],
        'menu': {'id': 'estoque-ativo', 'nome': 'Estoque', 'url': '/estoque-ativo.html', 'icone': 'warehouse'},
    },
    'materiais': {
        'nome': 'Materiais e Preços',
        'icone': 'fas fa-tags',
        'cor': '#ec4899',
        'permissoes': {
            'modulo_materiais': 'Acesso ao módulo de Materiais',
            'material_criar': 'Criar material',
            'material_editar': 'Editar material',
            'material_precos': 'Gerenciar preços',
            'material_classificacao': 'Gerenciar classificações',
        },
        'paginas': ['/tipos-lote.html'],
        'apis': ['/api/tipos-lote', '/api/materiais-base', '/api/precos', '/api/tabelas-preco'],
        'menu': {'id': 'materiais', 'nome': 'Materiais', 'url': '/tipos-lote.html', 'icone': 'precision_manufacturing'},
    },
    'veiculos': {
        'nome': 'Veículos',
        'icone': 'fas fa-car',
        'cor': '#f97316',
        'permissoes': {
            'modulo_veiculos': 'Acesso ao módulo de Veículos',
            'veiculo_criar': 'Cadastrar veículo',
            'veiculo_editar': 'Editar veículo',
            'veiculo_visualizar': 'Visualizar frota',
        },
        'paginas': ['/veiculos.html'],
        'apis': ['/api/veiculos'],
        'menu': {'id': 'veiculos', 'nome': 'Veículos', 'url': '/veiculos.html', 'icone': 'directions_car'},
    },
    'motorista': {
        'nome': 'Motorista',
        'icone': 'fas fa-truck-moving',
        'cor': '#059669',
        'permissoes': {
            'modulo_motorista': 'Habilita funcionalidade de Motorista',
            'motorista_app': 'Acesso ao App Motorista',
            'motorista_visualizar_os': 'Visualizar OS atribuídas',
            'motorista_atualizar_os': 'Atualizar status de OS',
            'motorista_enviar_comprovante': 'Enviar comprovantes/fotos',
        },
        'paginas': ['/app-motorista.html'],
        'apis': ['/api/motoristas', '/api/os', '/api/solicitacoes'],
        'menu': {'id': 'app-motorista', 'nome': 'App Motorista', 'url': '/app-motorista.html', 'icone': 'local_shipping'},
    },
    'gestao_motoristas': {
        'nome': 'Gestão de Motoristas',
        'icone': 'fas fa-users-cog',
        'cor': '#059669',
        'permissoes': {
            'modulo_gestao_motoristas': 'Acesso à Gestão de Motoristas',
            'gestao_motorista_criar': 'Cadastrar motorista',
            'gestao_motorista_editar': 'Editar motorista',
            'gestao_motorista_visualizar': 'Visualizar motoristas',
        },
        'paginas': ['/gestao-motoristas.html', '/motoristas.html'],
        'apis': ['/api/motoristas'],
        'menu': {'id': 'gestao-motoristas', 'nome': 'Motoristas', 'url': '/gestao-motoristas.html', 'icone': 'local_shipping'},
    },
    'cotacoes_metais': {
        'nome': 'Cotações de Metais',
        'icone': 'fas fa-chart-line',
        'cor': '#f59e0b',
        'permissoes': {
            'modulo_cotacoes_metais': 'Acesso às Cotações de Metais',
        },
        'paginas': ['/cotacoes-metais.html'],
        'apis': ['/api/metais'],
        'menu': {'id': 'cotacoes', 'nome': 'Cotações', 'url': '/cotacoes-metais.html', 'icone': 'trending_up'},
    },
    'residuos': {
        'nome': 'Resíduos',
        'icone': 'fas fa-recycle',
        'cor': '#22c55e',
        'permissoes': {
            'modulo_residuos': 'Acesso à Aprovação de Resíduos',
            'residuo_aprovar': 'Aprovar descarte',
            'residuo_visualizar': 'Visualizar resíduos',
        },
        'paginas': ['/residuos-aprovacao.html'],
        'apis': ['/api/separacao', '/api/lotes'],
        'menu': None,
    },
    'autorizacoes_preco': {
        'nome': 'Autorizações de Preço',
        'icone': 'fas fa-dollar-sign',
        'cor': '#8b5cf6',
        'permissoes': {
            'modulo_autorizacoes_preco': 'Acesso às Autorizações de Preço',
            'autorizacao_preco_criar': 'Criar autorização',
            'autorizacao_preco_aprovar': 'Aprovar autorização',
            'autorizacao_preco_visualizar': 'Visualizar autorizações',
        },
        'paginas': ['/autorizacoes-preco.html'],
        'apis': ['/api/autorizacoes-preco'],
        'menu': None,
    },
    'assistente': {
        'nome': 'Assistente IA',
        'icone': 'fas fa-robot',
        'cor': '#6366f1',
        'permissoes': {
            'modulo_assistente': 'Acesso ao Assistente IA',
        },
        'paginas': ['/assistente.html'],
        'apis': ['/api/assistente'],
        'menu': {'id': 'assistente', 'nome': 'Assistente', 'url': '/assistente.html', 'icone': 'smart_toy'},
    },
    'conquistas': {
        'nome': 'Planejamento de Conquistas',
        'icone': 'fas fa-trophy',
        'cor': '#8b5cf6',
        'permissoes': {
            'modulo_conquistas': 'Acesso ao Planejamento de Conquistas',
        },
        'paginas': ['/planejamento-conquistas.html'],
        'apis': ['/api/conquistas'],
        'menu': None,
    },
    'scanner': {
        'nome': 'Scanner PCB',
        'icone': 'fas fa-microchip',
        'cor': '#0d9488',
        'permissoes': {
            'modulo_scanner': 'Acesso ao Scanner de PCB',
        },
        'paginas': ['/scanner.html', '/admin-scanner-config.html', '/consulta-placas.html'],
        'apis': ['/api/scanner', '/api/placas'],
        'menu': None,
    },
    'rh': {
        'nome': 'RH / Gestão de Usuários',
        'icone': 'fas fa-users-cog',
        'cor': '#8b5cf6',
        'permissoes': {
            'modulo_rh': 'Acesso ao RH Admin',
            'rh_criar_usuario': 'Criar usuário',
            'rh_editar_usuario': 'Editar usuário',
            'rh_excluir_usuario': 'Excluir usuário',
            'rh_gerenciar_perfis': 'Gerenciar perfis',
            'rh_visualizar_comissoes': 'Visualizar comissões',
            'rh_exportar_comissoes': 'Exportar relatórios',
            'rh_auditoria': 'Visualizar auditoria',
        },
        'paginas': ['/rh-admin.html', '/funcionarios.html'],
        'apis': ['/api/rh', '/api/usuarios', '/api/perfis'],
        'menu': None,
    },
    'auditoria': {
        'nome': 'Auditoria / BI',
        'icone': 'fas fa-shield-alt',
        'cor': '#6b7280',
        'permissoes': {
            'modulo_auditoria': 'Acesso ao modo Auditoria',
            'auditoria_somente_leitura': 'Modo somente leitura',
            'auditoria_exportar': 'Exportar relatórios',
        },
        'paginas': ['/dashboard.html'],
        'apis': ['/api/auditoria', '/api/dashboard', '/api/fornecedores', '/api/solicitacoes', '/api/lotes', '/api/entradas'],
        'menu': None,
    },
    'revisao_tabelas': {
        'nome': 'Revisão de Tabelas de Preço',
        'icone': 'fas fa-file-invoice-dollar',
        'cor': '#f97316',
        'permissoes': {
            'modulo_revisao_tabelas': 'Acesso à Revisão de Tabelas',
            'tabela_preco_revisar': 'Revisar tabelas de preço',
            'tabela_preco_aprovar': 'Aprovar tabela de preço',
        },
        'paginas': ['/revisao-tabelas-admin.html'],
        'apis': ['/api/fornecedor-tabela-precos'],
        'menu': None,
    },
    'notificacoes': {
        'nome': 'Notificações',
        'icone': 'fas fa-bell',
        'cor': '#f59e0b',
        'permissoes': {
            'modulo_notificacoes': 'Acesso às Notificações',
        },
        'paginas': ['/notificacoes.html'],
        'apis': ['/api/notificacoes'],
        'menu': {'id': 'notificacoes', 'nome': 'Notificações', 'url': '/notificacoes.html', 'icone': 'notifications'},
    },
    'configuracoes': {
        'nome': 'Configurações',
        'icone': 'fas fa-cog',
        'cor': '#6b7280',
        'permissoes': {
            'modulo_configuracoes': 'Acesso às Configurações',
        },
        'paginas': ['/configuracoes.html'],
        'apis': ['/api/configuracoes'],
        'menu': None,
    },
    'modelos_tabela': {
        'nome': 'Modelos de Tabela de Preço',
        'icone': 'fas fa-layer-group',
        'cor': '#6366f1',
        'permissoes': {
            'modulo_modelos_tabela': 'Acesso aos Modelos de Tabela',
            'modelo_tabela_criar': 'Criar modelo de tabela',
            'modelo_tabela_editar': 'Editar modelo de tabela',
            'modelo_tabela_excluir': 'Excluir modelo de tabela',
            'modelo_tabela_visualizar': 'Visualizar modelos de tabela',
            'modelo_tabela_aplicar': 'Aplicar modelo ao fornecedor',
        },
        'paginas': ['/modelos-tabela-preco.html'],
        'apis': ['/api/modelos-tabela-preco'],
        'menu': None,
    },
}

# Páginas SEMPRE permitidas para qualquer usuário autenticado
PAGINAS_SEMPRE_PERMITIDAS = [
    '/administracao.html',
    '/notificacoes.html',
    '/acesso-negado.html',
    '/funcionario.html',
]

# APIs SEMPRE permitidas para qualquer usuário autenticado
APIS_SEMPRE_PERMITIDAS = [
    '/api/auth',
    '/api/notificacoes',
]


def gerar_config_dinamica(permissoes_dict):
    """
    Dado um dict de permissões (do campo JSON do Perfil),
    gera a configuração dinâmica: páginas permitidas, APIs, menus.
    """
    paginas = list(PAGINAS_SEMPRE_PERMITIDAS)
    apis = list(APIS_SEMPRE_PERMITIDAS)

    for modulo_key, modulo_config in PERMISSOES_CATALOGO.items():
        chave_modulo = f'modulo_{modulo_key}'
        if permissoes_dict.get(chave_modulo, False):
            paginas.extend(modulo_config.get('paginas', []))
            apis.extend(modulo_config.get('apis', []))

    # Remover duplicatas preservando ordem
    paginas = list(dict.fromkeys(paginas))
    apis = list(dict.fromkeys(apis))

    # Menus do bottom nav - vem do campo menus_inferiores do perfil
    menus_inferiores = permissoes_dict.get('menus_inferiores', [])

    # Sempre adicionar Painel como primeiro item fixo
    menu_painel = {'id': 'administracao', 'nome': 'Painel', 'url': '/administracao.html', 'icone': 'settings'}
    menus = [menu_painel] + menus_inferiores[:4]

    return {
        'tela_inicial': '/administracao.html',
        'paginas_permitidas': paginas,
        'rotas_api_permitidas': apis,
        'menus': menus,
        'ocultar_menu_inferior': False,
        'ocultar_botao_adicionar': not permissoes_dict.get('modulo_compras', False),
    }


def _gerar_config_admin():
    """Gera configuração completa para Administrador (acesso total)."""
    todas_permissoes = {}
    for modulo_config in PERMISSOES_CATALOGO.values():
        for perm_key in modulo_config['permissoes']:
            todas_permissoes[perm_key] = True
    config = gerar_config_dinamica(todas_permissoes)
    # Admin: menus padrão
    config['menus'] = [
        {'id': 'administracao', 'nome': 'Painel', 'url': '/administracao.html', 'icone': 'settings'},
        {'id': 'dashboard', 'nome': 'Dashboard', 'url': '/dashboard.html', 'icone': 'dashboard'},
        {'id': 'solicitacoes', 'nome': 'Compra', 'url': '/solicitacoes.html', 'icone': 'request_quote'},
        {'id': 'fornecedores', 'nome': 'Fornecedores', 'url': '/fornecedores.html', 'icone': 'business'},
    ]
    return config


def get_perfil_config(perfil_nome, perfil_obj=None):
    """
    Retorna a configuração para um perfil.
    Se perfil_obj for fornecido, usa as permissões do banco.
    """
    if perfil_nome == 'Administrador':
        return _gerar_config_admin()

    if perfil_obj and perfil_obj.permissoes:
        return gerar_config_dinamica(perfil_obj.permissoes)

    # Fallback seguro
    return {
        'tela_inicial': '/administracao.html',
        'rotas_api_permitidas': list(APIS_SEMPRE_PERMITIDAS),
        'paginas_permitidas': list(PAGINAS_SEMPRE_PERMITIDAS),
        'menus': [{'id': 'administracao', 'nome': 'Painel', 'url': '/administracao.html', 'icone': 'settings'}],
        'ocultar_menu_inferior': False,
        'ocultar_botao_adicionar': True,
    }


def get_menus_by_perfil(perfil_nome, perfil_obj=None):
    """Retorna os menus que devem ser exibidos para cada perfil"""
    config = get_perfil_config(perfil_nome, perfil_obj)
    return config.get('menus', [])


def get_tela_inicial_by_perfil(perfil_nome):
    """Retorna a tela inicial - sempre administracao.html"""
    return '/administracao.html'


def check_rota_api_permitida(perfil_nome, rota, perfil_obj=None):
    """Verifica se uma rota de API é permitida para um perfil"""
    if perfil_nome == 'Administrador':
        return True

    config = get_perfil_config(perfil_nome, perfil_obj)
    rotas_permitidas = config.get('rotas_api_permitidas', [])

    for rota_permitida in rotas_permitidas:
        if rota.startswith(rota_permitida):
            return True

    return False


def check_pagina_permitida(perfil_nome, pagina, perfil_obj=None):
    """Verifica se uma página HTML é permitida para um perfil"""
    if perfil_nome == 'Administrador':
        return True

    config = get_perfil_config(perfil_nome, perfil_obj)
    paginas_permitidas = config.get('paginas_permitidas', [])

    for pagina_permitida in paginas_permitidas:
        if pagina == pagina_permitida or pagina.endswith(pagina_permitida):
            return True
        if pagina_permitida.startswith('/') and not pagina_permitida.endswith('.html'):
            if pagina.startswith(pagina_permitida):
                return True

    return False


def get_paginas_permitidas(perfil_nome, perfil_obj=None):
    """Retorna lista de páginas que o perfil pode acessar"""
    config = get_perfil_config(perfil_nome, perfil_obj)
    return config.get('paginas_permitidas', [])


def get_ocultar_menu_inferior(perfil_nome, perfil_obj=None):
    """Retorna se o perfil deve ocultar o menu inferior"""
    config = get_perfil_config(perfil_nome, perfil_obj)
    return config.get('ocultar_menu_inferior', False)


def get_ocultar_botao_adicionar(perfil_nome, perfil_obj=None):
    """Retorna se o perfil deve ocultar o botão de adicionar (+)"""
    config = get_perfil_config(perfil_nome, perfil_obj)
    return config.get('ocultar_botao_adicionar', False)


def get_menus_disponiveis():
    """Retorna todos os menus possíveis para seleção no bottom nav"""
    menus = []
    for modulo_key, modulo_config in PERMISSOES_CATALOGO.items():
        if modulo_config.get('menu'):
            menus.append({
                'modulo': modulo_key,
                'chave_modulo': f'modulo_{modulo_key}',
                **modulo_config['menu']
            })
    return menus


def get_catalogo_completo():
    """Retorna o catálogo completo de permissões para o frontend"""
    return PERMISSOES_CATALOGO


def perfil_tem_motorista(permissoes_dict):
    """Verifica se as permissões incluem funcionalidade de motorista"""
    if not permissoes_dict:
        return False
    return permissoes_dict.get('modulo_motorista', False)