function formatarCNPJ(cnpj) {
    if (!cnpj) return '';
    cnpj = cnpj.replace(/\D/g, '');
    return cnpj.replace(/^(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})$/, '$1.$2.$3/$4-$5');
}

function formatarCPF(cpf) {
    if (!cpf) return '';
    cpf = cpf.replace(/\D/g, '');
    return cpf.replace(/^(\d{3})(\d{3})(\d{3})(\d{2})$/, '$1.$2.$3-$4');
}

function formatarTelefone(telefone) {
    if (!telefone) return '';
    telefone = telefone.replace(/\D/g, '');
    if (telefone.length === 11) {
        return telefone.replace(/^(\d{2})(\d{5})(\d{4})$/, '($1) $2-$3');
    }
    return telefone.replace(/^(\d{2})(\d{4})(\d{4})$/, '($1) $2-$3');
}

function formatarMoeda(valor) {
    if (valor === null || valor === undefined) return 'R$ 0,00';
    return new Intl.NumberFormat('pt-BR', {
        style: 'currency',
        currency: 'BRL'
    }).format(valor);
}

function formatarData(data) {
    if (!data) return '';
    const date = new Date(data);
    return date.toLocaleDateString('pt-BR');
}

function formatarDataHora(data) {
    if (!data) return '';
    const date = new Date(data);
    return date.toLocaleString('pt-BR');
}

function showAlert(message) {
    const alertDiv = document.createElement('div');
    alertDiv.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: #ef4444;
        color: white;
        padding: 1rem 1.5rem;
        border-radius: 8px;
        z-index: 10000;
        animation: slideIn 0.3s ease;
        max-width: 400px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    `;
    alertDiv.textContent = message;
    document.body.appendChild(alertDiv);
    
    setTimeout(() => {
        alertDiv.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => alertDiv.remove(), 300);
    }, 4000);
}

function showSuccess(message) {
    const alertDiv = document.createElement('div');
    alertDiv.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: #10b981;
        color: white;
        padding: 1rem 1.5rem;
        border-radius: 8px;
        z-index: 10000;
        animation: slideIn 0.3s ease;
        max-width: 400px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    `;
    alertDiv.textContent = message;
    document.body.appendChild(alertDiv);
    
    setTimeout(() => {
        alertDiv.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => alertDiv.remove(), 300);
    }, 3000);
}

function showConfirm(message) {
    return new Promise((resolve) => {
        const overlay = document.createElement('div');
        overlay.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0,0,0,0.5);
            z-index: 10000;
            display: flex;
            align-items: center;
            justify-content: center;
        `;
        
        const modal = document.createElement('div');
        modal.style.cssText = `
            background: white;
            padding: 2rem;
            border-radius: 12px;
            max-width: 400px;
            text-align: center;
        `;
        
        modal.innerHTML = `
            <p style="margin-bottom: 1.5rem; font-size: 1rem;">${message}</p>
            <div style="display: flex; gap: 1rem; justify-content: center;">
                <button id="confirmNo" style="padding: 0.75rem 1.5rem; border: 1px solid #e5e7eb; border-radius: 8px; background: white; cursor: pointer;">Cancelar</button>
                <button id="confirmYes" style="padding: 0.75rem 1.5rem; border: none; border-radius: 8px; background: #059669; color: white; cursor: pointer;">Confirmar</button>
            </div>
        `;
        
        overlay.appendChild(modal);
        document.body.appendChild(overlay);
        
        modal.querySelector('#confirmNo').addEventListener('click', () => {
            overlay.remove();
            resolve(false);
        });
        
        modal.querySelector('#confirmYes').addEventListener('click', () => {
            overlay.remove();
            resolve(true);
        });
    });
}

const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    @keyframes slideOut {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(100%); opacity: 0; }
    }
`;
document.head.appendChild(style);
