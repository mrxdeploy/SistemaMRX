const API_URL = '/api';
let currentUser = null;
let socket = null;

function getToken() {
    return localStorage.getItem('token');
}

function setToken(token) {
    localStorage.setItem('token', token);
}

function removeToken() {
    localStorage.removeItem('token');
}

function initMobileMenu() {
    const menuToggle = document.querySelector('.menu-toggle');
    const nav = document.querySelector('nav');
    const navOverlay = document.querySelector('.nav-overlay');

    if (!menuToggle) return;

    menuToggle.addEventListener('click', () => {
        menuToggle.classList.toggle('active');
        nav.classList.toggle('active');
        if (navOverlay) {
            navOverlay.classList.toggle('active');
        }
    });

    if (navOverlay) {
        navOverlay.addEventListener('click', () => {
            menuToggle.classList.remove('active');
            nav.classList.remove('active');
            navOverlay.classList.remove('active');
        });
    }

    const navLinks = nav.querySelectorAll('a');
    navLinks.forEach(link => {
        link.addEventListener('click', () => {
            menuToggle.classList.remove('active');
            nav.classList.remove('active');
            if (navOverlay) {
                navOverlay.classList.remove('active');
            }
        });
    });
}

document.addEventListener('DOMContentLoaded', () => {
    initMobileMenu();
});

async function fetchAPI(endpoint, options = {}) {
    const token = getToken();

    const defaultHeaders = {
        'Content-Type': 'application/json',
        ...(token && { 'Authorization': `Bearer ${token}` })
    };

    const config = {
        ...options,
        headers: {
            ...defaultHeaders,
            ...(options.headers || {})
        }
    };

    try {
        const response = await fetch(`/api${endpoint}`, config);

        if (response.status === 401) {
            logout();
            return null;
        }

        // Retornar response diretamente para status 409 (conflito) ser tratado pelo caller
        if (response.status === 409) {
            return response;
        }

        if (!response.ok && response.status !== 404) {
            const error = await response.json();
            throw new Error(error.erro || error.message || 'Erro na requisição');
        }

        return response;
    } catch (error) {
        console.error('Erro na API:', error);
        throw error;
    }
}

async function login(email, senha) {
    const response = await fetchAPI('/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email, senha })
    });

    const data = await response.json();

    if (response.ok) {
        setToken(data.token);
        currentUser = data.usuario;
        return data.usuario;
    } else {
        throw new Error(data.erro || 'Erro ao fazer login');
    }
}

async function getCurrentUser() {
    try {
        const response = await fetchAPI('/auth/me');

        if (!response) {
            return null;
        }

        if (response.ok) {
            const data = await response.json();
            currentUser = data;
            return data;
        }

        return null;
    } catch (error) {
        console.error('Erro ao obter usuário atual:', error);
        return null;
    }
}

function logout() {
    removeToken();
    if (socket) {
        socket.disconnect();
    }
    window.location.href = '/';
}

function showAlert(message, type = 'error') {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type}`;
    alertDiv.textContent = message;

    const container = document.querySelector('.container') || document.body;
    container.insertBefore(alertDiv, container.firstChild);

    setTimeout(() => {
        alertDiv.remove();
    }, 5000);
}

function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleString('pt-BR');
}

function formatCurrency(value) {
    return new Intl.NumberFormat('pt-BR', {
        style: 'currency',
        currency: 'BRL'
    }).format(value);
}

function initWebSocket() {
    if (!getToken()) return;

    socket = io({
        auth: {
            token: getToken()
        }
    });

    socket.on('connect', () => {
        console.log('WebSocket conectado');
    });

    socket.on('nova_notificacao', async () => {
        await atualizarNotificacoes();
    });
}

async function atualizarNotificacoes() {
    const response = await fetchAPI('/notificacoes/nao-lidas');

    if (response.ok) {
        const data = await response.json();
        const badge = document.querySelector('.notification-count');

        if (badge) {
            if (data.count > 0) {
                badge.textContent = data.count;
                badge.style.display = 'flex';
            } else {
                badge.style.display = 'none';
            }
        }
    }
}

async function verificarAuth() {
    const token = getToken();

    if (!token) {
        if (window.location.pathname !== '/' && !window.location.pathname.includes('index.html')) {
            window.location.href = '/';
        }
        return null;
    }

    try {
        const user = await getCurrentUser();

        if (!user) {
            if (window.location.pathname !== '/' && !window.location.pathname.includes('index.html')) {
                window.location.href = '/';
            }
            return null;
        }

        // Não fazer verificação de acesso aqui - deixar o RBAC fazer isso
        // verificarAcessoPorPerfil(user);

        return user;
    } catch (error) {
        console.error('Erro ao verificar autenticação:', error);
        if (window.location.pathname !== '/' && !window.location.pathname.includes('index.html')) {
            window.location.href = '/';
        }
        return null;
    }
}

function hasPermission(permission) {
    if (!currentUser || !currentUser.permissoes) {
        return false;
    }
    return currentUser.permissoes[permission] === true || currentUser.tipo === 'admin';
}

function aplicarControleAcesso(user) {
    if (!user) return;

    // Administrador tem acesso total
    if (user.tipo === 'admin' || user.perfil_nome === 'Administrador') {
        console.log(' Usuário admin - acesso total');
        return;
    }

    const controlePorPerfil = {
        'Comprador (PJ)': {
            paginasPermitidas: ['/fornecedores.html', '/fornecedores-lista.html', '/fornecedor-tabela-precos.html', '/solicitacoes.html', '/notificacoes.html', '/compras.html', '/index.html', '/'],
            modulosVisiveis: ['fornecedores', 'solicitacoes']
        },
        'Conferente / Estoque': {
            paginasPermitidas: ['/dashboard.html', '/lotes.html', '/entradas.html', '/notificacoes.html', '/index.html', '/'],
            modulosVisiveis: ['lotes', 'entradas']
        },
        'Separação': {
            paginasPermitidas: ['/dashboard.html', '/lotes.html', '/notificacoes.html', '/index.html', '/'],
            modulosVisiveis: ['lotes']
        },
        'Motorista': {
            paginasPermitidas: ['/dashboard.html', '/solicitacoes.html', '/notificacoes.html', '/index.html', '/'],
            modulosVisiveis: ['solicitacoes']
        },
        'Financeiro': {
            paginasPermitidas: ['/dashboard.html', '/fornecedores.html', '/solicitacoes.html', '/notificacoes.html', '/index.html', '/'],
            modulosVisiveis: ['fornecedores', 'solicitacoes']
        },
        'Auditoria / BI': {
            paginasPermitidas: ['/dashboard.html'],
            modulosVisiveis: []
        }
    };

    const controle = controlePorPerfil[user.perfil_nome];

    if (!controle) {
        console.warn(' Perfil não mapeado:', user.perfil_nome);
        console.log('Permitindo acesso ao dashboard...');
        return;
    }

    const paginaAtual = window.location.pathname;
    console.log(' Página atual:', paginaAtual);
    console.log(' Páginas permitidas:', controle.paginasPermitidas);

    // Verificar se a página atual está na lista de permitidas
    const paginaPermitida = controle.paginasPermitidas.some(p => {
        return paginaAtual === p || paginaAtual.endsWith(p);
    });

    if (!paginaPermitida && paginaAtual !== '/' && paginaAtual !== '/index.html') {
        console.warn(' Acesso negado à página:', paginaAtual);
        console.log(' Redirecionando para:', user.tela_inicial);
        window.location.href = user.tela_inicial || '/dashboard.html';
        return;
    }

    console.log(' Acesso permitido - Perfil:', user.perfil_nome);
    ocultarModulosNaoPermitidos(controle.modulosVisiveis);
}

function ocultarModulosNaoPermitidos(modulosVisiveis) {
    const todosModulos = document.querySelectorAll('.card[onclick*="window.location"]');
    todosModulos.forEach(modulo => {
        const onclick = modulo.getAttribute('onclick');
        let visivel = false;

        modulosVisiveis.forEach(moduloPermitido => {
            if (onclick && onclick.includes(moduloPermitido)) {
                visivel = true;
            }
        });

        if (!visivel) {
            modulo.style.display = 'none';
        }
    });
}

if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('/static/js/sw.js')
            .then(registration => {
                console.log('Service Worker registrado:', registration);
            })
            .catch(error => {
                console.log('Erro ao registrar Service Worker:', error);
            });
    });
}

let deferredPrompt;

window.addEventListener('beforeinstallprompt', (e) => {
    e.preventDefault();
    deferredPrompt = e;

    const banner = document.querySelector('.pwa-install-banner');
    if (banner) {
        banner.classList.add('show');
    }
});

function instalarPWA() {
    if (deferredPrompt) {
        deferredPrompt.prompt();
        deferredPrompt.userChoice.then((choiceResult) => {
            if (choiceResult.outcome === 'accepted') {
                console.log('PWA instalado');
            }
            deferredPrompt = null;
            const banner = document.querySelector('.pwa-install-banner');
            if (banner) {
                banner.classList.remove('show');
            }
        });
    }
}

function fecharBannerPWA() {
    const banner = document.querySelector('.pwa-install-banner');
    if (banner) {
        banner.classList.remove('show');
    }
}

// Scanner Modal Functions
function openScanner() {
    const modal = document.getElementById('scannerModal');
    if (modal) {
        modal.classList.add('active');
        carregarEmpresasScanner();
        setupAutoCalculation();
    }
}

function closeScanner() {
    const modal = document.getElementById('scannerModal');
    if (modal) {
        modal.classList.remove('active');
        document.getElementById('formScanner').reset();
        document.getElementById('imagePreview').classList.remove('active');
    }
}

async function carregarEmpresasScanner() {
    try {
        const response = await fetchAPI('/fornecedores');
        if (!response) {
            console.error('Erro: Sem resposta do servidor');
            return;
        }

        if (!response.ok) {
            const errorData = await response.json();
            console.error('Erro ao carregar fornecedores:', errorData.mensagem || errorData.erro);
            return;
        }

        const data = await response.json();
        const select = document.getElementById('scannerFornecedor');
        if (select) {
            select.innerHTML = '<option value="">Escolha um fornecedor...</option>';
            data.forEach(fornecedor => {
                const option = document.createElement('option');
                option.value = fornecedor.id;
                option.textContent = fornecedor.nome;
                select.appendChild(option);
            });
        }
    } catch (error) {
        console.error('Erro ao carregar fornecedores:', error);
    }
}

let currentLocationData = {
    lat: null,
    lng: null,
    endereco: null
};

async function obterLocalizacaoAutomatica() {
    return new Promise((resolve, reject) => {
        if (!navigator.geolocation) {
            console.warn('Geolocalização não suportada');
            resolve(null);
            return;
        }

        navigator.geolocation.getCurrentPosition(async (position) => {
            const lat = position.coords.latitude;
            const lng = position.coords.longitude;

            try {
                const response = await fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lng}&addressdetails=1`);

                const data = await response.json();

                if (data && data.address) {
                    const addr = data.address;
                    const rua = addr.road || addr.street || addr.pedestrian || 'Rua não identificada';
                    const numero = addr.house_number || 's/n';
                    const bairro = addr.neighbourhood || addr.suburb || '';
                    const cidade = addr.city || addr.town || addr.village || '';
                    const estado = addr.state || '';
                    const cep = addr.postcode || 'CEP não disponível';

                    const enderecoCompleto = `${rua}, ${numero}${bairro ? ', ' + bairro : ''} - ${cidade}/${estado} - CEP: ${cep}`;

                    currentLocationData = {
                        lat: lat,
                        lng: lng,
                        endereco: enderecoCompleto
                    };

                    console.log(' Localização obtida:', enderecoCompleto);
                    resolve(currentLocationData);
                } else {
                    currentLocationData = {
                        lat: lat,
                        lng: lng,
                        endereco: `Coordenadas: ${lat.toFixed(6)}, ${lng.toFixed(6)}`
                    };
                    resolve(currentLocationData);
                }
            } catch (error) {
                console.error('Erro ao obter endereço:', error);
                currentLocationData = {
                    lat: lat,
                    lng: lng,
                    endereco: `Coordenadas: ${lat.toFixed(6)}, ${lng.toFixed(6)}`
                };
                resolve(currentLocationData);
            }
        }, (error) => {
            console.warn('Erro ao obter localização:', error);
            resolve(null);
        }, {
            enableHighAccuracy: true,
            timeout: 10000,
            maximumAge: 0
        });
    });
}

function previewImage(input) {
    if (input.files && input.files[0]) {
        const reader = new FileReader();
        reader.onload = function(e) {
            const preview = document.getElementById('imagePreview');
            const img = document.getElementById('previewImg');
            if (preview && img) {
                img.src = e.target.result;
                preview.classList.add('active');
            }
        };
        reader.readAsDataURL(input.files[0]);
    }
}

async function capturarLocalizacaoScanner() {
    const btn = document.getElementById('btnCapturarLocalizacao');
    const locationInfo = document.getElementById('locationInfo');

    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Obtendo localização...';
    }

    const location = await obterLocalizacaoAutomatica();

    if (location && location.endereco) {
        currentLocationData = location;
        if (locationInfo) {
            locationInfo.innerHTML = `<i class="fas fa-map-marker-alt"></i> ${location.endereco}`;
            locationInfo.style.display = 'block';
        }
        showAlert(' Localização capturada com sucesso!', 'success');
        if (btn) {
            btn.innerHTML = '<i class="fas fa-check"></i> Localização Capturada';
        }
    } else {
        showAlert('Não foi possível obter a localização. Verifique as permissões.', 'error');
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-map-marker-alt"></i> Capturar Localização';
        }
    }
}

async function calcularValorAutomatico() {
    const fornecedorId = document.getElementById('scannerFornecedor')?.value;
    const tipoPlaca = document.getElementById('tipoPlaca')?.value;
    const pesoKg = parseFloat(document.getElementById('pesoPlaca')?.value);
    const valorDisplay = document.getElementById('valorCalculado');

    if (!fornecedorId || !tipoPlaca || !pesoKg || isNaN(pesoKg)) {
        if (valorDisplay) {
            valorDisplay.textContent = 'R$ 0,00';
            valorDisplay.setAttribute('data-valor', '0');
        }
        return;
    }

    try {
        const response = await fetchAPI(`/api/fornecedores/${fornecedorId}/preco/${tipoPlaca}`);

        if (response.ok) {
            const data = await response.json();
            const precoPorKg = data.preco_por_kg;
            const valorTotal = pesoKg * precoPorKg;

            if (valorDisplay) {
                valorDisplay.textContent = formatCurrency(valorTotal);
                valorDisplay.setAttribute('data-valor', valorTotal);
            }
        } else {
            if (valorDisplay) {
                valorDisplay.textContent = 'Preço não configurado';
                valorDisplay.setAttribute('data-valor', '0');
            }
        }
    } catch (error) {
        console.error('Erro ao calcular valor:', error);
        if (valorDisplay) {
            valorDisplay.textContent = 'Erro ao calcular';
            valorDisplay.setAttribute('data-valor', '0');
        }
    }
}

function setupAutoCalculation() {
    const fornecedorSelect = document.getElementById('scannerFornecedor');
    const tipoPlacaSelect = document.getElementById('tipoPlaca');
    const pesoInput = document.getElementById('pesoPlaca');

    if (fornecedorSelect) {
        fornecedorSelect.addEventListener('change', calcularValorAutomatico);
    }

    if (tipoPlacaSelect) {
        tipoPlacaSelect.addEventListener('change', calcularValorAutomatico);
    }

    if (pesoInput) {
        pesoInput.addEventListener('input', calcularValorAutomatico);
    }
}

// Set active bottom nav item
function setActiveNavItem() {
    const currentPath = window.location.pathname;
    const navItems = document.querySelectorAll('.bottom-nav-item');

    navItems.forEach(item => {
        item.classList.remove('active');
        if (item.getAttribute('href') === currentPath) {
            item.classList.add('active');
        }
    });
}

// Submit Scanner Form
document.addEventListener('DOMContentLoaded', () => {
    const formScanner = document.getElementById('formScanner');
    if (formScanner) {
        formScanner.addEventListener('submit', async (e) => {
            e.preventDefault();

            const valorCalculado = document.getElementById('valorCalculado')?.getAttribute('data-valor');

            if (!valorCalculado || parseFloat(valorCalculado) <= 0) {
                alert('Por favor, preencha todos os campos para calcular o valor automaticamente.');
                return;
            }

            const formData = new FormData();
            formData.append('fornecedor_id', document.getElementById('scannerFornecedor').value);
            formData.append('tipo_placa', document.getElementById('tipoPlaca').value);
            formData.append('peso_kg', document.getElementById('pesoPlaca').value);
            formData.append('valor', valorCalculado);

            const fileInput = document.getElementById('fileInput');
            if (fileInput.files.length > 0) {
                formData.append('imagem', fileInput.files[0]);
            }

            if (currentLocationData.lat && currentLocationData.lng) {
                formData.append('localizacao_lat', currentLocationData.lat);
                formData.append('localizacao_lng', currentLocationData.lng);
                if (currentLocationData.endereco) {
                    formData.append('endereco_completo', currentLocationData.endereco);
                }
            }

            try {
                const token = getToken();
                // Ensure the endpoint starts with /api
                const apiEndpoint = endpoint && endpoint.startsWith('/api') ? endpoint : `/api${endpoint || '/placas'}`;
                const response = await fetch(apiEndpoint, {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${token}`
                    },
                    body: formData
                });

                if (response.ok) {
                    alert('Placa registrada com sucesso!');
                    closeScanner();
                    if (typeof carregarPlacas === 'function') {
                        carregarPlacas();
                    }
                } else {
                    const error = await response.json();
                    alert('Erro ao registrar placa: ' + (error.error || 'Erro desconhecido'));
                }
            } catch (error) {
                console.error('Erro:', error);
                alert('Erro ao registrar placa');
            }
        });
    }

    setActiveNavItem();
});