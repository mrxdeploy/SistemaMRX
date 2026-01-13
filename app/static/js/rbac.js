let currentUserData = null;
let currentMenus = [];
let paginasPermitidas = [];
let ocultarBotaoAdicionar = false;
let rbacCarregado = false;

async function carregarUsuarioERBAC() {
    const token = getToken();
    
    if (!token) {
        if (window.location.pathname !== '/' && !window.location.pathname.includes('index.html') && window.location.pathname !== '/acesso-negado.html') {
            window.location.href = '/';
        }
        return null;
    }

    try {
        const [userResponse, menusResponse] = await Promise.all([
            fetchAPI('/auth/me'),
            fetchAPI('/auth/menus')
        ]);

        if (!userResponse || !userResponse.ok) {
            removeToken();
            window.location.href = '/';
            return null;
        }

        currentUserData = await userResponse.json();
        
        if (menusResponse && menusResponse.ok) {
            const menusData = await menusResponse.json();
            currentMenus = menusData.menus || [];
            paginasPermitidas = menusData.paginas_permitidas || [];
            ocultarBotaoAdicionar = menusData.ocultar_botao_adicionar || false;
        } else {
            currentMenus = [];
            paginasPermitidas = [];
            ocultarBotaoAdicionar = false;
        }

        rbacCarregado = true;
        return currentUserData;
    } catch (error) {
        console.error('Erro ao carregar dados do usuário:', error);
        currentMenus = [];
        paginasPermitidas = [];
        ocultarBotaoAdicionar = false;
        rbacCarregado = true;
        return currentUserData;
    }
}

function verificarPermissao(permissao) {
    if (!currentUserData) {
        return false;
    }

    if (currentUserData.tipo === 'admin') {
        return true;
    }

    return currentUserData.permissoes && currentUserData.permissoes.includes(permissao);
}

function verificarPerfil(...perfisPermitidos) {
    if (!currentUserData) {
        return false;
    }

    if (currentUserData.tipo === 'admin') {
        return true;
    }

    return perfisPermitidos.includes(currentUserData.perfil);
}

function renderizarMenus(containerId = 'navMenu') {
    const container = document.getElementById(containerId);
    
    if (!container) {
        console.warn('Container de menu não encontrado:', containerId);
        return;
    }

    if (!currentMenus || currentMenus.length === 0) {
        console.warn('Nenhum menu disponível para renderizar. Perfil:', currentUserData?.perfil);
        container.innerHTML = '';
        return;
    }

    container.innerHTML = '';

    currentMenus.forEach(menu => {
        const li = document.createElement('li');
        const a = document.createElement('a');
        a.href = menu.url || '#';
        a.textContent = menu.nome || 'Menu';
        a.dataset.menuId = menu.id || '';

        if (menu.url && (window.location.pathname === menu.url || window.location.pathname.includes(menu.url))) {
            a.classList.add('active');
        }

        li.appendChild(a);
        container.appendChild(li);
    });
    
    console.log(`✅ ${currentMenus.length} menu(s) renderizado(s) com sucesso`);
}

function renderizarMenusMobile(containerId = 'navMenuMobile') {
    const container = document.getElementById(containerId);
    
    if (!container) {
        return;
    }

    if (!currentMenus || currentMenus.length === 0) {
        console.warn('Nenhum menu disponível para renderizar (mobile)');
        return;
    }

    container.innerHTML = '';

    // Mapeamento de ícones Material Icons para Font Awesome
    const iconMap = {
        'settings': 'fas fa-cog',
        'dashboard': 'fas fa-chart-pie',
        'request_quote': 'fas fa-file-invoice',
        'business': 'fas fa-building',
        'input': 'fas fa-sign-in-alt',
        'fact_check': 'fas fa-check-double',
        'inventory_2': 'fas fa-warehouse',
        'format_list_bulleted': 'fas fa-list',
        'local_shipping': 'fas fa-truck',
        'notifications': 'fas fa-bell',
        'receipt_long': 'fas fa-receipt',
        'verified': 'fas fa-shield-alt',
        'warehouse': 'fas fa-warehouse',
        'precision_manufacturing': 'fas fa-industry'
    };

    currentMenus.forEach((menu, index) => {
        const a = document.createElement('a');
        a.href = menu.url || '#';
        a.className = 'bottom-nav-item';
        
        if (menu.url && (window.location.pathname === menu.url || window.location.pathname.includes(menu.url))) {
            a.classList.add('active');
        }

        // Usar Font Awesome ao invés de Material Icons
        const icon = document.createElement('i');
        const iconClass = iconMap[menu.icone] || 'fas fa-circle';
        icon.className = iconClass + ' icon';

        const span = document.createElement('span');
        span.textContent = menu.nome || 'Menu';

        a.appendChild(icon);
        a.appendChild(span);
        container.appendChild(a);

        // Adicionar FAB button no centro do menu (se não estiver oculto)
        if (!ocultarBotaoAdicionar) {
            // Calcular índice para inserir o FAB no meio
            // Para 2 menus: após índice 0 (1-FAB-1)
            // Para 4 menus: após índice 1 (2-FAB-2)
            // Para 5 menus: após índice 2 (3-FAB-2) - melhor balanceamento
            const fabIndex = Math.floor((currentMenus.length - 1) / 2);
            
            if (index === fabIndex) {
                const fabContainer = document.createElement('div');
                fabContainer.className = 'fab-container';
                
                const fabButton = document.createElement('button');
                fabButton.className = 'fab-button';
                fabButton.setAttribute('aria-label', 'Nova Compra');
                fabButton.onclick = function() {
                    if (typeof abrirModalNovaSolicitacao === 'function') {
                        abrirModalNovaSolicitacao();
                    } else {
                        window.location.href = '/solicitacoes.html';
                    }
                };
                
                const fabIcon = document.createElement('i');
                fabIcon.className = 'fas fa-plus icon';
                
                fabButton.appendChild(fabIcon);
                fabContainer.appendChild(fabButton);
                container.appendChild(fabContainer);
            }
        }
    });
}

function ocultarElementosPorPermissao() {
    document.querySelectorAll('[data-permission]').forEach(elemento => {
        const permissaoNecessaria = elemento.dataset.permission;
        if (!verificarPermissao(permissaoNecessaria)) {
            elemento.style.display = 'none';
        }
    });
}

function ocultarElementosPorPerfil() {
    document.querySelectorAll('[data-perfil]').forEach(elemento => {
        const perfisPermitidos = elemento.dataset.perfil.split(',').map(p => p.trim());
        if (!verificarPerfil(...perfisPermitidos)) {
            elemento.style.display = 'none';
        }
    });
}

function verificarAcessoPagina() {
    const paginaAtual = window.location.pathname;

    // Páginas públicas sempre permitidas
    if (paginaAtual === '/' || paginaAtual === '/index.html' || paginaAtual === '/acesso-negado.html') {
        return true;
    }

    if (!rbacCarregado) {
        console.warn('RBAC ainda não foi carregado, aguardando...');
        return false;
    }

    if (!currentUserData) {
        console.warn('Usuário não autenticado, redirecionando para login');
        window.location.href = '/';
        return false;
    }

    // Admin tem acesso total
    if (currentUserData.tipo === 'admin' || currentUserData.perfil === 'Administrador') {
        console.log('✅ Acesso permitido - Admin tem acesso total');
        return true;
    }

    if (!currentUserData.perfil || currentUserData.perfil === 'Sem perfil') {
        console.error('ERRO: Usuário sem perfil definido:', currentUserData);
        showAlert('Seu usuário não possui perfil configurado. Entre em contato com o administrador.');
        window.location.href = '/acesso-negado.html';
        return false;
    }

    // PROTEÇÃO ESPECÍFICA: Perfil Auditoria / BI só pode acessar dashboard
    if (currentUserData.perfil === 'Auditoria / BI') {
        console.log('🔍 Verificando acesso para perfil Auditoria/BI');
        console.log('Página atual:', paginaAtual);
        
        if (paginaAtual === '/dashboard.html') {
            console.log('✅ Acesso permitido - Dashboard é permitido para Auditoria/BI');
            return true;
        } else {
            console.warn('⚠️ Perfil Auditoria/BI tentou acessar:', paginaAtual);
            console.warn('⚠️ Redirecionando para dashboard');
            window.location.href = '/dashboard.html';
            return false;
        }
    }

    if (!paginasPermitidas || paginasPermitidas.length === 0) {
        console.error('ERRO CRÍTICO: Nenhuma página permitida configurada para o perfil:', currentUserData.perfil);
        console.error('Usuário:', currentUserData);
        console.error('Negando acesso por segurança até que as permissões sejam carregadas');
        window.location.href = '/acesso-negado.html';
        return false;
    }

    const paginaPermitida = paginasPermitidas.some(pagPermitida => {
        // Verifica igualdade exata ou se termina com (ex: /dashboard.html)
        if (paginaAtual === pagPermitida || paginaAtual.endsWith(pagPermitida)) {
            return true;
        }
        // Verifica se é uma sub-rota (apenas se a permissão não for um arquivo .html)
        // Ex: pagPermitida='api/producao', paginaAtual='/api/producao/ordem/7'
        if ((!pagPermitida.endsWith('.html')) && paginaAtual.startsWith(pagPermitida)) {
            return true;
        }
        return false;
    });
    
    if (!paginaPermitida) {
        console.warn('🚫 Acesso negado à página:', paginaAtual);
        console.warn('Páginas permitidas:', paginasPermitidas);
        window.location.href = '/acesso-negado.html';
        return false;
    }

    console.log('✅ Acesso permitido à página:', paginaAtual);
    return true;
}

function redirecionarParaTelaInicial() {
    if (currentUserData && currentUserData.tela_inicial) {
        window.location.href = currentUserData.tela_inicial;
    } else {
        window.location.href = '/dashboard.html';
    }
}

async function inicializarRBAC() {
    try {
        await carregarUsuarioERBAC();
        
        if (!rbacCarregado) {
            console.error('RBAC não pôde ser carregado');
            return;
        }
        
        if (currentUserData) {
            renderizarMenus();
            renderizarMenusMobile();
            ocultarElementosPorPermissao();
            ocultarElementosPorPerfil();
            
            const acessoPermitido = verificarAcessoPagina();
            
            if (!acessoPermitido) {
                console.warn('Acesso não permitido, verificação bloqueada ou redirecionamento em andamento');
                return;
            }

            const userNameElements = document.querySelectorAll('[data-user-name]');
            if (userNameElements && userNameElements.length > 0) {
                userNameElements.forEach(el => {
                    if (el) {
                        el.textContent = currentUserData.nome || currentUserData.email || '';
                    }
                });
            }

            const userProfileElements = document.querySelectorAll('[data-user-profile]');
            if (userProfileElements && userProfileElements.length > 0) {
                userProfileElements.forEach(el => {
                    if (el) {
                        el.textContent = currentUserData.perfil || 'Sem perfil';
                    }
                });
            }
        } else {
            console.warn('Usuário não está autenticado');
        }
    } catch (error) {
        console.error('Erro ao inicializar RBAC:', error);
    }
}

if (typeof window !== 'undefined') {
    if (window.location.pathname !== '/' && !window.location.pathname.includes('index.html')) {
        document.addEventListener('DOMContentLoaded', inicializarRBAC);
    }
}
