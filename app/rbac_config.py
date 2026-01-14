PERFIL_CONFIG = {
    'Administrador': {
        'tela_inicial': '/dashboard.html',
        'rotas_api_permitidas': [
            '/api/usuarios',
            '/api/perfis',
            '/api/fornecedores',
            '/api/veiculos',
            '/api/motoristas',
            '/api/solicitacoes',
            '/api/lotes',
            '/api/entradas',
            '/api/estoque',
            '/api/separacao',
            '/api/conferencia',
            '/api/auditoria',
            '/api/relatorios',
            '/api/tipos-lote',
            '/api/precos',
            '/api/rh'
        ],
        'paginas_permitidas': [
            '/dashboard.html',
            '/usuarios.html',
            '/perfis.html',
            '/fornecedores.html',
            '/fornecedores-lista.html',
            '/produtos.html',
            '/tipos-lote.html',
            '/solicitacoes.html',
            '/aprovar_solicitacoes.html',
            '/lotes.html',
            '/lotes_aprovados.html',
            '/estoque.html',
            '/entradas.html',
            '/veiculos.html',
            '/motoristas.html',
            '/financeiro.html',
            '/auditoria.html',
            '/administracao.html',
            '/configuracoes.html',
            '/notificacoes.html',
            '/funcionarios.html',
            '/cotacoes-metais.html',
            '/planejamento-conquistas.html',
            '/assistente.html',
            '/rh-admin.html'
        ],
        'menus': [
            {'id': 'usuarios', 'nome': 'Administração', 'url': '/administracao.html', 'icone': 'settings'},
            {'id': 'dashboard', 'nome': 'Dashboard', 'url': '/dashboard.html', 'icone': 'dashboard'},
            {'id': 'solicitacoes', 'nome': 'Compra', 'url': '/solicitacoes.html', 'icone': 'request_quote'},
            {'id': 'fornecedores', 'nome': 'Fornecedores', 'url': '/fornecedores.html', 'icone': 'business'}
        ]
    },
    'Comprador (PJ)': {
        'tela_inicial': '/solicitacoes.html',
        'rotas_api_permitidas': [
            '/api/solicitacoes',
            '/api/fornecedores',
            '/api/tipos-lote',
            '/api/notificacoes',
            '/api/fornecedor-tabela-precos',
            '/api/materiais-base'
        ],
        'paginas_permitidas': [
            '/solicitacoes.html',
            '/fornecedores.html',
            '/fornecedores-lista.html',
            '/notificacoes.html',
            '/compras.html',
            '/fornecedor-tabela-precos.html'
        ],
        'menus': [
            {'id': 'solicitacoes', 'nome': 'Compra', 'url': '/solicitacoes.html', 'icone': 'request_quote'},
            {'id': 'fornecedores', 'nome': 'Fornecedores', 'url': '/fornecedores.html', 'icone': 'business'}
        ]
    },
    'Gestor': {
        'tela_inicial': '/solicitacoes.html',
        'rotas_api_permitidas': [
            '/api/solicitacoes',
            '/api/fornecedores',
            '/api/tipos-lote',
            '/api/notificacoes',
            '/api/fornecedor-tabela-precos',
            '/api/materiais-base',
            '/api/lotes',
            '/api/estoque',
            '/api/estoque-ativo',
            '/api/producao',
            '/api/wms',
            '/api/entradas'
        ],
        'paginas_permitidas': [
            '/solicitacoes.html',
            '/fornecedores.html',
            '/fornecedores-lista.html',
            '/notificacoes.html',
            '/compras.html',
            '/fornecedor-tabela-precos.html',
            '/estoque-ativo.html',
            '/lotes.html',
            '/lotes-detalhes.html',
            '/separacao-workflow.html',
            '/producao.html',
            '/producao-ordem.html'
        ],
        'menus': [
            {'id': 'solicitacoes', 'nome': 'Compra', 'url': '/solicitacoes.html', 'icone': 'request_quote'},
            {'id': 'fornecedores', 'nome': 'Fornecedores', 'url': '/fornecedores.html', 'icone': 'business'},
            {'id': 'estoque-ativo', 'nome': 'Estoque Ativo', 'url': '/estoque-ativo.html', 'icone': 'warehouse'},
            {'id': 'wms', 'nome': 'WMS', 'url': '/lotes.html', 'icone': 'inventory_2'}
        ]
    },
    'Conferente / Estoque': {
        'tela_inicial': '/entradas.html',
        'rotas_api_permitidas': [
            '/api/lotes',
            '/api/entradas',
            '/api/estoque',
            '/api/conferencia',
            '/api/solicitacoes'
        ],
        'paginas_permitidas': [
            '/dashboard.html',
            '/lotes.html',
            '/lotes_aprovados.html',
            '/entradas.html',
            '/estoque.html',
            '/lotes-recebidos.html',
            '/validacao.html',
            '/notificacoes.html'
        ],
        'menus': [
            {'id': 'entradas', 'nome': 'Entrada Estoque', 'url': '/entradas.html', 'icone': 'input'},
            {'id': 'validacao', 'nome': 'Validação', 'url': '/validacao.html', 'icone': 'fact_check'},
            {'id': 'lotes', 'nome': 'Lotes', 'url': '/lotes.html', 'icone': 'inventory_2'},
            {'id': 'dashboard', 'nome': 'Dashboard', 'url': '/dashboard.html', 'icone': 'dashboard'}
        ]
    },
    'Separação': {
        'tela_inicial': '/separacao-fila.html',
        'rotas_api_permitidas': [
            '/api/lotes',
            '/api/entradas',
            '/api/separacao',
            '/api/estoque'
        ],
        'paginas_permitidas': [
            '/dashboard.html',
            '/lotes.html',
            '/lotes_aprovados.html',
            '/separacao-fila.html',
            '/separacao-workflow.html',
            '/notificacoes.html'
        ],
        'menus': [
            {'id': 'separacao-fila', 'nome': 'Fila Separação', 'url': '/separacao-fila.html', 'icone': 'format_list_bulleted'},
            {'id': 'lotes', 'nome': 'Lotes', 'url': '/lotes.html', 'icone': 'inventory_2'},
            {'id': 'dashboard', 'nome': 'Dashboard', 'url': '/dashboard.html', 'icone': 'dashboard'}
        ]
    },
    'Motorista': {
        'tela_inicial': '/app-motorista.html',
        'rotas_api_permitidas': [
            '/api/solicitacoes',
            '/api/motoristas'
        ],
        'paginas_permitidas': [
            '/app-motorista.html',
            '/notificacoes.html'
        ],
        'menus': [
            {'id': 'app-motorista', 'nome': 'Meu App', 'url': '/app-motorista.html', 'icone': 'local_shipping'},
            {'id': 'notificacoes', 'nome': 'Notificações', 'url': '/notificacoes.html', 'icone': 'notifications'}
        ]
    },
    'Financeiro': {
        'tela_inicial': '/dashboard.html',
        'rotas_api_permitidas': [
            '/api/solicitacoes',
            '/api/fornecedores',
            '/api/lotes'
        ],
        'paginas_permitidas': [
            '/dashboard.html',
            '/fornecedores.html',
            '/fornecedores-lista.html',
            '/solicitacoes.html',
            '/lotes.html',
            '/notificacoes.html'
        ],
        'menus': [
            {'id': 'dashboard', 'nome': 'Dashboard', 'url': '/dashboard.html', 'icone': 'dashboard'},
            {'id': 'solicitacoes', 'nome': 'Compra', 'url': '/solicitacoes.html', 'icone': 'receipt_long'},
            {'id': 'fornecedores', 'nome': 'Fornecedores', 'url': '/fornecedores.html', 'icone': 'business'},
            {'id': 'lotes', 'nome': 'Lotes', 'url': '/lotes.html', 'icone': 'inventory_2'}
        ]
    },
    'Auditoria / BI': {
        'tela_inicial': '/dashboard.html',
        'rotas_api_permitidas': [
            '/api/auditoria',
            '/api/relatorios',
            '/api/usuarios',
            '/api/fornecedores',
            '/api/solicitacoes',
            '/api/lotes',
            '/api/entradas',
            '/api/dashboard'
        ],
        'paginas_permitidas': [
            '/dashboard.html'
        ],
        'menus': [],
        'ocultar_menu_inferior': True
    },
    'Producao': {
        'tela_inicial': '/producao.html',
        'rotas_api_permitidas': [
            '/api/solicitacoes',
            '/api/fornecedores',
            '/api/tipos-lote',
            '/api/notificacoes',
            '/api/fornecedor-tabela-precos',
            '/api/materiais-base',
            '/api/producao',
            '/api/estoque-ativo',
            '/api/separacao',
            '/api/conferencia',
            '/api/lotes',
            '/api/estoque',
            '/api/entradas'
        ],
        'paginas_permitidas': [
            '/solicitacoes.html',
            '/fornecedores.html',
            '/fornecedores-lista.html',
            '/notificacoes.html',
            '/compras.html',
            '/fornecedor-tabela-precos.html',
            '/producao.html',
            '/producao-ordem.html',
            '/api/producao',
            '/estoque-ativo.html',
            '/separacao-fila.html',
            '/separacao-workflow.html',
            '/conferencia.html',
            '/lotes.html',
            '/lotes-recebidos.html',
            '/lotes_aprovados.html',
            '/lotes-detalhes.html',
            '/validacao.html'
        ],
        'menus': [
            {'id': 'producao', 'nome': 'Produção', 'url': '/producao.html', 'icone': 'precision_manufacturing'},
            {'id': 'estoque-ativo', 'nome': 'Estoque Ativo', 'url': '/estoque-ativo.html', 'icone': 'warehouse'},
            {'id': 'separacao', 'nome': 'Separação', 'url': '/separacao-fila.html', 'icone': 'format_list_bulleted'},
            {'id': 'solicitacoes', 'nome': 'Compra', 'url': '/solicitacoes.html', 'icone': 'request_quote'},
            {'id': 'fornecedores', 'nome': 'Fornecedores', 'url': '/fornecedores.html', 'icone': 'business'}
        ]
    }
}

TIPOS_USUARIO = {
    'admin': {
        'nome': 'Administrador',
        'descricao': 'Acesso total ao sistema',
        'homepage': '/dashboard.html'
    },
    'funcionario': {
        'nome': 'Funcionário',
        'descricao': 'Acesso limitado baseado no perfil',
        'homepage': '/funcionario.html'
    },
    'motorista': {
        'nome': 'Motorista',
        'descricao': 'Acesso ao app de entregas',
        'homepage': '/app-motorista.html'
    }
}

def get_perfil_config(perfil_nome):
    """
    Retorna a configuração de um perfil específico
    """
    return PERFIL_CONFIG.get(perfil_nome, {
        'tela_inicial': '/acesso-negado.html',
        'rotas_api_permitidas': [],
        'paginas_permitidas': [],
        'menus': []
    })

def get_menus_by_perfil(perfil_nome):
    """Retorna os menus que devem ser exibidos para cada perfil"""
    config = get_perfil_config(perfil_nome)
    return config.get('menus', [])

def get_tela_inicial_by_perfil(perfil_nome):
    """Retorna a tela inicial baseada no perfil"""
    config = get_perfil_config(perfil_nome)
    return config.get('tela_inicial', '/acesso-negado.html')

def check_rota_api_permitida(perfil_nome, rota):
    """
    Verifica se uma rota de API é permitida para um perfil
    """
    config = get_perfil_config(perfil_nome)
    rotas_api_permitidas = config.get('rotas_api_permitidas', [])

    for rota_permitida in rotas_api_permitidas:
        if rota.startswith(rota_permitida):
            return True

    return False

def check_pagina_permitida(perfil_nome, pagina):
    """
    Verifica se uma página HTML é permitida para um perfil
    """
    config = get_perfil_config(perfil_nome)
    paginas_permitidas = config.get('paginas_permitidas', [])

    for pagina_permitida in paginas_permitidas:
        if pagina == pagina_permitida or pagina.endswith(pagina_permitida):
            return True
            
        # Suporte para sub-rotas como /api/producao/ordem/7
        if pagina_permitida.startswith('/') and not pagina_permitida.endswith('.html'):
             if pagina.startswith(pagina_permitida):
                 return True

    return False

def get_paginas_permitidas(perfil_nome):
    """Retorna lista de páginas que o perfil pode acessar"""
    config = get_perfil_config(perfil_nome)
    return config.get('paginas_permitidas', [])

def get_ocultar_menu_inferior(perfil_nome):
    """Retorna se o perfil deve ocultar o menu inferior"""
    config = get_perfil_config(perfil_nome)
    return config.get('ocultar_menu_inferior', False)

def get_ocultar_botao_adicionar(perfil_nome):
    """Retorna se o perfil deve ocultar o botão de adicionar (+)"""
    config = get_perfil_config(perfil_nome)
    return config.get('ocultar_botao_adicionar', False)