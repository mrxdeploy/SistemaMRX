let chatWidgetOpen = false;
let chatSessaoId = null;
let chatConversas = [];

function isChatUserAdmin() {
    if (typeof currentUser !== 'undefined' && currentUser) {
        return currentUser.tipo === 'admin' || currentUser.perfil_nome === 'Administrador';
    }
    return false;
}

function initChatWidget() {
    const token = getToken();
    if (!token) return;
    
    if (!isChatUserAdmin()) {
        console.log('Chat widget: usuario nao e admin, ocultando widget');
        return;
    }
    
    const widgetHTML = `
        <div id="chatWidgetContainer" class="chat-widget-container">
            <div id="chatWidgetBubble" class="chat-widget-bubble" onclick="toggleChatWidget()">
                <i class="fas fa-robot"></i>
                <span class="chat-widget-badge" id="chatBadge" style="display: none;">!</span>
            </div>
            <div id="chatWidgetPopup" class="chat-widget-popup">
                <div class="chat-widget-header">
                    <div class="chat-widget-header-info">
                        <i class="fas fa-robot"></i>
                        <div>
                            <span class="chat-widget-title">Assistente MRX</span>
                            <span class="chat-widget-status">Online</span>
                        </div>
                    </div>
                    <div class="chat-widget-header-actions">
                        <button onclick="novaChatConversa()" title="Nova conversa"><i class="fas fa-plus"></i></button>
                        <button onclick="toggleChatWidget()" title="Fechar"><i class="fas fa-times"></i></button>
                    </div>
                </div>
                <div class="chat-widget-messages" id="chatWidgetMessages">
                    <div class="chat-widget-welcome">
                        <i class="fas fa-comments"></i>
                        <p>Ola! Sou o assistente inteligente do MRX Systems. Posso ajudar com informacoes sobre fornecedores, solicitacoes, cotacoes de metais e muito mais!</p>
                    </div>
                </div>
                <div class="chat-widget-suggestions" id="chatWidgetSuggestions">
                    <button onclick="usarSugestaoChat('Dados da empresa')"><i class="fas fa-building"></i> Dados da empresa</button>
                    <button onclick="usarSugestaoChat('Cotacao do ouro')"><i class="fas fa-coins"></i> Cotacao ouro</button>
                    <button onclick="usarSugestaoChat('Quantos fornecedores ativos?')"><i class="fas fa-users"></i> Fornecedores</button>
                </div>
                <div class="chat-widget-input-container">
                    <textarea id="chatWidgetInput" placeholder="Digite sua mensagem..." rows="1" onkeydown="handleChatWidgetKeyDown(event)"></textarea>
                    <button id="chatWidgetSendBtn" onclick="enviarMensagemWidget()">
                        <i class="fas fa-paper-plane"></i>
                    </button>
                </div>
            </div>
        </div>
    `;
    
    document.body.insertAdjacentHTML('beforeend', widgetHTML);
    chatSessaoId = 'widget_' + Date.now();
}

function toggleChatWidget() {
    const popup = document.getElementById('chatWidgetPopup');
    const bubble = document.getElementById('chatWidgetBubble');
    
    if (!popup || !bubble) return;
    
    chatWidgetOpen = !chatWidgetOpen;
    
    if (chatWidgetOpen) {
        popup.classList.add('active');
        bubble.classList.add('active');
        document.getElementById('chatWidgetInput')?.focus();
        
        const badge = document.getElementById('chatBadge');
        if (badge) badge.style.display = 'none';
    } else {
        popup.classList.remove('active');
        bubble.classList.remove('active');
    }
}

function novaChatConversa() {
    chatSessaoId = 'widget_' + Date.now();
    chatConversas = [];
    
    const messagesContainer = document.getElementById('chatWidgetMessages');
    if (messagesContainer) {
        messagesContainer.innerHTML = `
            <div class="chat-widget-welcome">
                <i class="fas fa-comments"></i>
                <p>Nova conversa iniciada! Como posso ajudar?</p>
            </div>
        `;
    }
    
    const suggestions = document.getElementById('chatWidgetSuggestions');
    if (suggestions) suggestions.style.display = 'flex';
}

function usarSugestaoChat(texto) {
    const input = document.getElementById('chatWidgetInput');
    if (input) {
        input.value = texto;
        enviarMensagemWidget();
    }
}

function handleChatWidgetKeyDown(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        enviarMensagemWidget();
    }
}

async function enviarMensagemWidget() {
    const input = document.getElementById('chatWidgetInput');
    const mensagem = input?.value?.trim();
    
    if (!mensagem) return;
    
    input.value = '';
    input.style.height = 'auto';
    
    const suggestions = document.getElementById('chatWidgetSuggestions');
    if (suggestions) suggestions.style.display = 'none';
    
    const welcome = document.querySelector('.chat-widget-welcome');
    if (welcome) welcome.remove();
    
    adicionarMensagemWidget(mensagem, 'user');
    mostrarTypingWidget();
    
    try {
        const token = getToken();
        if (!token) {
            removerTypingWidget();
            adicionarMensagemWidget('Por favor, faca login para usar o assistente.', 'assistant');
            return;
        }
        
        const response = await fetch('/api/assistente/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                mensagem: mensagem,
                sessao_id: chatSessaoId
            })
        });
        
        removerTypingWidget();
        
        if (response.status === 401) {
            adicionarMensagemWidget('Sua sessao expirou. Por favor, faca login novamente.', 'assistant');
            return;
        }
        
        if (response.ok) {
            const data = await response.json();
            chatSessaoId = data.sessao_id;
            adicionarMensagemWidget(data.resposta, 'assistant', data.fonte_dados);
        } else {
            const error = await response.json();
            adicionarMensagemWidget('Desculpe, ocorreu um erro. Tente novamente.', 'assistant');
        }
    } catch (error) {
        console.error('Erro no chat widget:', error);
        removerTypingWidget();
        adicionarMensagemWidget('Erro de conexao. Verifique sua internet.', 'assistant');
    }
}

function adicionarMensagemWidget(texto, tipo, fonte = null) {
    const container = document.getElementById('chatWidgetMessages');
    if (!container) return;
    
    const msgDiv = document.createElement('div');
    msgDiv.className = `chat-widget-message ${tipo}`;
    
    let textoFormatado = texto
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\n/g, '<br>')
        .replace(/- /g, '&bull; ');
    
    if (tipo === 'assistant' && fonte) {
        msgDiv.innerHTML = `
            <div class="chat-widget-message-content">${textoFormatado}</div>
            <div class="chat-widget-message-fonte"><i class="fas fa-database"></i> ${fonte}</div>
        `;
    } else {
        msgDiv.innerHTML = `<div class="chat-widget-message-content">${textoFormatado}</div>`;
    }
    
    container.appendChild(msgDiv);
    container.scrollTop = container.scrollHeight;
}

function mostrarTypingWidget() {
    const container = document.getElementById('chatWidgetMessages');
    if (!container) return;
    
    const typingDiv = document.createElement('div');
    typingDiv.className = 'chat-widget-typing';
    typingDiv.id = 'chatWidgetTyping';
    typingDiv.innerHTML = '<span></span><span></span><span></span>';
    container.appendChild(typingDiv);
    container.scrollTop = container.scrollHeight;
}

function removerTypingWidget() {
    const typing = document.getElementById('chatWidgetTyping');
    if (typing) typing.remove();
}

document.addEventListener('DOMContentLoaded', function() {
    setTimeout(initChatWidget, 500);
});
