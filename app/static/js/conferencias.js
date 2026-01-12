// CONFERENCIAS.JS - Versão NOVA - Completamente reconstruído
console.log('🚀 CONFERENCIAS.JS CARREGADO - Versão NOVA');

const CONFERENCIA_API_URL = '/api/conferencia';
let conferencias = [];

async function carregarEstatisticas() {
    console.log('📊 Carregando estatísticas...');
    try {
        const token = localStorage.getItem('token');
        const response = await fetch(`${CONFERENCIA_API_URL}/estatisticas`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        
        if (response.ok) {
            const stats = await response.json();
            document.getElementById('stat-pendentes').textContent = stats.pendentes || 0;
            document.getElementById('stat-divergentes').textContent = stats.divergentes || 0;
            document.getElementById('stat-aguardando').textContent = stats.aguardando_adm || 0;
            document.getElementById('stat-aprovadas').textContent = stats.aprovadas || 0;
            console.log('✅ Estatísticas carregadas:', stats);
        }
    } catch (error) {
        console.error('❌ Erro ao carregar estatísticas:', error);
    }
}

async function carregarConferencias(status = '') {
    console.log('📦 Carregando conferências... Status filtro:', status);
    try {
        const token = localStorage.getItem('token');
        const url = status ? `${CONFERENCIA_API_URL}?status=${status}` : CONFERENCIA_API_URL;
        const response = await fetch(url, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        
        if (response.ok) {
            conferencias = await response.json();
            console.log('✅ Conferências recebidas da API:', conferencias.length, conferencias);
            renderizarTabela();
        } else {
            console.error('❌ Erro na resposta da API:', response.status, response.statusText);
        }
    } catch (error) {
        console.error('❌ Erro ao carregar conferências:', error);
        alert('Erro ao carregar conferências');
    }
}

function renderizarTabela() {
    console.log('🎨 RENDERIZANDO TABELA - Total de conferências:', conferencias.length);
    
    const tbody = document.querySelector('#tabela-conferencias tbody');
    if (!tbody) {
        console.error('❌ ERRO: tbody não encontrado!');
        return;
    }
    
    tbody.innerHTML = '';
    
    conferencias.forEach((conf, index) => {
        console.log(`\n━━━━━━ CONFERÊNCIA ${index + 1} ━━━━━━`);
        console.log('ID:', conf.id);
        console.log('Status:', conf.conferencia_status);
        console.log('Divergente:', conf.divergencia);
        
        const tr = document.createElement('tr');
        
        const statusBadge = getStatusBadge(conf.conferencia_status);
        const divergenciaBadge = conf.divergencia ? 
            `<span class="badge bg-danger"><i class="bi bi-exclamation-triangle-fill"></i> ${(conf.percentual_diferenca || 0).toFixed(1)}%</span>` : 
            '<span class="badge bg-success"><i class="bi bi-check-circle-fill"></i> OK</span>';
        
        const fornecedor = conf.ordem_servico?.fornecedor_snapshot?.nome || '-';
        
        // LÓGICA DO BOTÃO DE AÇÃO
        let botaoAcao = '';
        
        if (conf.conferencia_status === 'PENDENTE') {
            console.log('  → Botão: PROCESSAR (status PENDENTE)');
            botaoAcao = `<a href="/conferencia-form/${conf.id}" class="btn btn-sm btn-primary">Processar</a>`;
        } 
        else if (conf.conferencia_status === 'DIVERGENTE') {
            console.log('  → ✅✅✅ Botão: ENVIAR P/ ADM (status DIVERGENTE)');
            botaoAcao = `<button class="btn btn-sm btn-warning" onclick="enviarParaAdmDireto(${conf.id})">
                            <i class="bi bi-exclamation-triangle"></i> Enviar p/ ADM
                        </button>`;
        } 
        else if (conf.conferencia_status === 'AGUARDANDO_ADM') {
            console.log('  → Botão: DECIDIR (status AGUARDANDO_ADM)');
            botaoAcao = `<a href="/conferencia-decisao-adm/${conf.id}" class="btn btn-sm btn-warning">Decidir</a>`;
        } 
        else {
            console.log('  → Botão: VER DETALHES (status:', conf.conferencia_status, ')');
            botaoAcao = `<button class="btn btn-sm btn-secondary" onclick="verDetalhes(${conf.id})">Ver Detalhes</button>`;
        }
        
        console.log('  HTML do botão gerado:', botaoAcao.substring(0, 100));
        
        tr.innerHTML = `
            <td>${conf.id}</td>
            <td>${conf.os_id || '-'}</td>
            <td>${conf.oc_id || '-'}</td>
            <td>${fornecedor}</td>
            <td>${conf.peso_fornecedor ? conf.peso_fornecedor.toFixed(2) + ' kg' : '-'}</td>
            <td>${conf.peso_real ? conf.peso_real.toFixed(2) + ' kg' : '-'}</td>
            <td>${divergenciaBadge}</td>
            <td>${statusBadge}</td>
            <td>${botaoAcao}</td>
        `;
        
        tbody.appendChild(tr);
        console.log('  ✅ Linha adicionada à tabela');
    });
    
    console.log('✅ TABELA RENDERIZADA COM SUCESSO!');
}

function getStatusBadge(status) {
    const badges = {
        'PENDENTE': '<span class="badge bg-primary">Pendente</span>',
        'DIVERGENTE': '<span class="badge bg-warning text-dark">Divergente</span>',
        'AGUARDANDO_ADM': '<span class="badge bg-info">Aguardando ADM</span>',
        'APROVADA': '<span class="badge bg-success">Aprovada</span>',
        'REJEITADA': '<span class="badge bg-danger">Rejeitada</span>'
    };
    return badges[status] || `<span class="badge bg-secondary">${status}</span>`;
}

function verDetalhes(id) {
    window.location.href = `/conferencia-form/${id}`;
}

async function enviarParaAdmDireto(conferenciaId) {
    console.log('🚨 FUNÇÃO enviarParaAdmDireto CHAMADA! ID:', conferenciaId);
    
    if (!confirm('Confirma o envio desta divergência para análise administrativa?')) {
        console.log('Usuário cancelou');
        return;
    }
    
    try {
        const token = localStorage.getItem('token');
        const response = await fetch(`${CONFERENCIA_API_URL}/${conferenciaId}/enviar-para-adm`, {
            method: 'PUT',
            headers: { 
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({})
        });
        
        if (response.ok) {
            const result = await response.json();
            console.log('✅ Sucesso ao enviar para ADM:', result);
            alert('✅ Divergência enviada para análise administrativa com sucesso!');
            
            // Recarregar a lista
            const filtro = document.getElementById('filtro-status').value;
            await carregarConferencias(filtro);
            await carregarEstatisticas();
        } else {
            const error = await response.json();
            console.error('❌ Erro na resposta:', error);
            alert('❌ Erro: ' + (error.erro || 'Erro ao enviar para ADM'));
        }
    } catch (error) {
        console.error('❌ Erro ao enviar para ADM:', error);
        alert('❌ Erro ao enviar para análise administrativa');
    }
}

// INICIALIZAÇÃO
console.log('🔧 Aguardando DOMContentLoaded...');
document.addEventListener('DOMContentLoaded', function() {
    console.log('✅ DOM CARREGADO - Iniciando aplicação de conferências');
    
    const filtroStatus = document.getElementById('filtro-status');
    if (filtroStatus) {
        filtroStatus.addEventListener('change', (e) => {
            console.log('Filtro mudou para:', e.target.value);
            carregarConferencias(e.target.value);
        });
    }
    
    console.log('📡 Iniciando primeiro carregamento...');
    carregarEstatisticas();
    carregarConferencias();
    
    // Auto-refresh a cada 30 segundos
    setInterval(() => {
        console.log('🔄 Auto-refresh (30s)');
        carregarEstatisticas();
        const filtro = document.getElementById('filtro-status').value;
        carregarConferencias(filtro);
    }, 30000);
});

console.log('✅ FIM DO ARQUIVO conferencias.js');
