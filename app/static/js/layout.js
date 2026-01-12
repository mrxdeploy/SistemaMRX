
function logout() {
    removeToken();
    if (typeof socket !== 'undefined' && socket) {
        socket.disconnect();
    }
    window.location.href = '/';
}

// Torna logout disponível globalmente
if (typeof window !== 'undefined') {
    window.logout = logout;
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

async function verificarAuth() {
    const token = getToken();
    
    if (!token) {
        if (window.location.pathname !== '/' && !window.location.pathname.includes('index.html')) {
            window.location.href = '/';
        }
        return null;
    }

    const user = await getCurrentUser();
    
    if (!user) {
        removeToken();
        window.location.href = '/';
        return null;
    }

    if (typeof initWebSocket === 'function') {
        initWebSocket();
    }
    return user;
}

async function getCurrentUser() {
    try {
        const response = await fetchAPI('/auth/me');
        
        if (!response) {
            return null;
        }
        
        if (response.ok) {
            const data = await response.json();
            return data;
        }
        
        return null;
    } catch (error) {
        console.error('Erro ao obter usuário atual:', error);
        return null;
    }
}

async function atualizarNotificacoes() {
    const response = await fetchAPI('/notificacoes/nao-lidas');
    
    if (response && response.ok) {
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
