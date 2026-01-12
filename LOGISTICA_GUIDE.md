# Sistema de Logística MRX - Guia Completo

## Visão Geral

O sistema de logística foi completamente implementado com 4 módulos principais:
1. **Gestão de Ordens de Serviço (OS)**
2. **Roteirização e GPS Tracking**
3. **App Motorista (PWA)**
4. **Conferência de Recebimento**

---

## 📊 Estrutura do Banco de Dados

### Tabelas Criadas
- `ordens_servico` - Gestão completa de OS vinculadas a OCs
- `rotas_operacionais` - Rotas planejadas e executadas
- `gps_logs` - Rastreamento GPS em tempo real
- `conferencias_recebimento` - Inspeção e qualidade dos recebimentos

### Relacionamentos
- OS vinculada a Ordem de Compra (OC)
- OS atribuída a Motorista e Veículo
- Conferência vinculada a OS e OC
- Auditoria completa com GPS, IP e device tracking

---

## 🚀 Endpoints da API

### Ordens de Serviço

**POST /api/oc/{oc_id}/gerar-os**
- Gera OS automaticamente a partir de uma OC aprovada
- Valida status da OC
- Cria snapshot do fornecedor

**GET /api/os**
- Lista todas as OS com filtros opcionais
- Parâmetros: status, motorista_id, data_inicio, data_fim

**GET /api/os/{id}**
- Detalhes completos de uma OS

**PUT /api/os/{id}/atribuir-motorista**
- Atribui motorista e veículo a uma OS
- Muda status para AGENDADA

**POST /api/os/{id}/reagendar**
- Reagenda janela de coleta
- Validações de disponibilidade

**PUT /api/os/{id}/iniciar-rota**
- Motorista inicia rota
- Registra GPS inicial
- Muda status para EM_ROTA

**POST /api/os/{id}/evento**
- Registra eventos do motorista durante a rota
- Eventos: CHEGUEI, COLETEI, SAI, CHEGUEI_MRX, FINALIZEI
- Atualiza status automaticamente

**GET /api/os/estatisticas**
- Estatísticas gerais: total_os, pendentes, em_rota, finalizadas

### Conferência de Recebimento

**POST /api/conferencia/{os_id}/iniciar**
- Inicia conferência a partir de uma OS
- Extrai peso esperado da OC

**GET /api/conferencia**
- Lista todas as conferências

**GET /api/conferencia/{id}**
- Detalhes de uma conferência

**PUT /api/conferencia/{id}/registrar-pesagem**
- Registra peso real, qualidade e fotos
- Detecta divergências automaticamente
- Calcula percentual de diferença

**PUT /api/conferencia/{id}/enviar-para-adm**
- Envia divergência para decisão administrativa
- Muda status para AGUARDANDO_ADM

**PUT /api/conferencia/{id}/decisao-adm**
- Admin decide: ACEITAR, ACEITAR_COM_DESCONTO, REJEITAR
- Registra motivo e percentual de desconto (se aplicável)

**GET /api/conferencia/estatisticas**
- Estatísticas: total_conferencias, pendentes, divergentes, aguardando_adm, aprovadas

---

## 🖥️ Interfaces Web

### 1. Painel de Logística (/logistica)
- Lista todas as OS com filtros
- Estatísticas em cards
- Atribuir motorista a OS
- Ver detalhes completos
- Link para Kanban

### 2. Quadro Kanban (/kanban)
- Visualização por colunas de status
- PENDENTE → AGENDADA → EM_ROTA → ENTREGUE → FINALIZADA → CANCELADA
- Contadores por coluna
- Drag-and-drop (preparado para implementação)

### 3. App Motorista (/app-motorista)
**PWA Mobile-First com:**
- GPS tracking automático
- Indicador de GPS ativo/inativo
- 3 abas: Pendentes, Em Rota, Finalizadas
- Botões de ação contextuais por status
- Registro de eventos com localização
- Interface otimizada para mobile

**Fluxo do Motorista:**
1. Ver OS atribuídas (tab Pendentes)
2. Iniciar Rota (registra GPS inicial)
3. Cheguei no Fornecedor
4. Material Coletado
5. Saí do Fornecedor
6. Cheguei na MRX
7. Finalizar OS

### 4. Conferência de Recebimento (/conferencia)
- Lista de recebimentos pendentes
- Registro de pesagem (peso, qualidade, fotos)
- Detecção automática de divergências
- Workflow de aprovação administrativa
- Estatísticas de conferência

---

## 🔐 Segurança

### Implementado
- JWT authentication em todos os endpoints
- Auditoria completa (GPS, IP, device_id, timestamp)
- Logs imutáveis em JSONB
- SQLAlchemy com defaults seguros (lambdas)

### A Implementar
- RBAC enforcement nos endpoints críticos
- Validações de permissão por perfil
- Rate limiting
- Sanitização de inputs

---

## 📱 Recursos do App Motorista (PWA)

### Características
- Funciona offline (preparado)
- Geolocation API integrada
- Interface mobile-first responsiva
- Device ID único por instalação
- Notificações push (infraestrutura pronta)

### Tecnologias
- HTML5 Geolocation API
- LocalStorage para cache
- Service Worker registrado
- AJAX para comunicação com API

---

## 🧪 Como Testar

### 1. Criar uma OS
```bash
POST /api/oc/1/gerar-os
Headers: Authorization: Bearer {token}
```

### 2. Atribuir Motorista
```bash
PUT /api/os/1/atribuir-motorista
Body: {"motorista_id": 1, "veiculo_id": 1}
```

### 3. Usar App Motorista
1. Acesse /app-motorista
2. Faça login
3. Veja suas OS na tab "Pendentes"
4. Clique em "Iniciar Rota"
5. Registre eventos conforme executa a coleta

### 4. Conferência
1. Acesse /conferencia
2. Registre pesagem de OS entregue
3. Se houver divergência, envie para ADM
4. Admin aprova/rejeita/desconta

---

## 📊 Fluxo Completo

```
OC Aprovada 
  → Gerar OS (POST /api/oc/{id}/gerar-os)
  → Atribuir Motorista (PUT /api/os/{id}/atribuir-motorista)
  → Motorista Inicia Rota (PUT /api/os/{id}/iniciar-rota)
  → Eventos de Coleta (POST /api/os/{id}/evento)
  → OS Entregue
  → Iniciar Conferência (POST /api/conferencia/{os_id}/iniciar)
  → Registrar Pesagem (PUT /api/conferencia/{id}/registrar-pesagem)
  → [Se divergente] Decisão ADM (PUT /api/conferencia/{id}/decisao-adm)
  → Aprovada → Atualizar Estoque
```

---

## 🎯 Próximos Passos (Melhorias Futuras)

### Roteirização Automática
- Implementar algoritmo de clustering geográfico
- Nearest-neighbor para otimização de rotas
- Cálculo de distâncias e tempos estimados

### Mapa Interativo
- Tela de mapa com rotas visualizadas
- Markers de fornecedores
- Tracking em tempo real de motoristas

### Notificações
- Push notifications para motoristas
- Alertas de divergência para admins
- WebSocket para atualizações em tempo real

### RBAC Completo
- Middleware de autorização em todos os endpoints
- Perfis: Admin, Logística, Motorista, Inspetor
- Logs de acesso detalhados

### Relatórios
- Dashboard de performance de motoristas
- Relatório de divergências
- KPIs logísticos

---

## 🐛 Problemas Conhecidos Corrigidos

1. ✅ **JSON defaults compartilhados** - Corrigido com lambdas
2. ✅ **Migração SQL sem ::jsonb** - Corrigido
3. ✅ **Falta de triggers para atualizado_em** - Criados
4. ✅ **Dependências não instaladas** - Instaladas
5. ✅ **Rotas não registradas** - Adicionadas ao app.py

---

## 📝 Notas Técnicas

- **Banco**: PostgreSQL com JSONB para flexibilidade
- **ORM**: SQLAlchemy com relacionamentos bem definidos
- **API**: RESTful com padrões consistentes
- **Frontend**: Vanilla JS + AJAX (sem frameworks pesados)
- **Mobile**: Progressive Web App (PWA)

---

## 🔗 Links Úteis

- Painel Logística: http://localhost:5000/logistica
- Kanban: http://localhost:5000/kanban
- App Motorista: http://localhost:5000/app-motorista
- Conferência: http://localhost:5000/conferencia

---

**Desenvolvido para MRX Systems - Sistema de Gestão Logística Completo**
