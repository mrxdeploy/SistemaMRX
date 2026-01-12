function toggleScannerWidget() {
    window.location.href = 'https://scanv1-production.up.railway.app/';
}

function initScannerWidget() {
    if (scannerWidgetInitialized) return;
    
    const token = getToken();
    if (!token) return;
    
    if (typeof currentUser === 'undefined' || !currentUser) {
        scannerInitAttempts++;
        const delay = Math.min(500 * Math.pow(1.5, scannerInitAttempts - 1), 5000);
        setTimeout(initScannerWidget, delay);
        return;
    }
    
    if (!isUserAdmin()) {
        return;
    }
    
    scannerWidgetInitialized = true;
    
    const widgetHTML = `
        <div id="scannerWidgetContainer" class="scanner-widget-container" style="position: fixed; bottom: 90px; right: 20px; z-index: 9999;">
            <div id="scannerWidgetBubble" class="scanner-widget-bubble" onclick="window.location.href='https://scanv1-production.up.railway.app/'" title="Abrir Scanner" style="width: 56px; height: 56px; border-radius: 50%; background: linear-gradient(135deg, #0d9488 0%, #14b8a6 100%); box-shadow: 0 4px 20px rgba(13, 148, 136, 0.4); display: flex; align-items: center; justify-content: center; cursor: pointer; transition: all 0.3s ease; color: white;">
                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M3 7V5a2 2 0 0 1 2-2h2"/>
                    <path d="M17 3h2a2 2 0 0 1 2 2v2"/>
                    <path d="M21 17v2a2 2 0 0 1-2 2h-2"/>
                    <path d="M7 21H5a2 2 0 0 1-2-2v-2"/>
                    <line x1="7" y1="12" x2="17" y2="12"/>
                    <line x1="12" y1="7" x2="12" y2="7.01"/>
                    <line x1="12" y1="17" x2="12" y2="17.01"/>
                </svg>
            </div>
        </div>
    `;
    
    document.body.insertAdjacentHTML('beforeend', widgetHTML);
}

let scannerWidgetInitialized = false;
let scannerInitAttempts = 0;

function isUserAdmin() {
    if (typeof currentUser !== 'undefined' && currentUser) {
        return currentUser.tipo === 'admin' || currentUser.perfil_nome === 'Administrador';
    }
    return false;
}

// Botão de Voltar "superficial" que aparece quando estamos na URL do scanner
// Nota: Como o sistema é externo, este botão só apareceria se injetado via extensão ou se o sistema externo permitisse.
// Para fins de demonstração no ambiente local, adicionamos um listener que detecta a URL.
if (window.location.href.includes('scanv1-production.up.railway.app')) {
    const backBtn = document.createElement('div');
    backBtn.innerHTML = '<button onclick="window.history.back()" style="position: fixed; top: 10px; left: 10px; z-index: 10001; padding: 10px 20px; background: #059669; color: white; border: none; border-radius: 5px; cursor: pointer; font-weight: bold; box-shadow: 0 2px 5px rgba(0,0,0,0.2);">← Voltar para MRX</button>';
    document.body.appendChild(backBtn);
}

document.addEventListener('DOMContentLoaded', () => {
    initScannerWidget();
});
