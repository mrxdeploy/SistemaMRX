# 🏭 MRX Systems - Sistema Completo de Gestão de Metais e Eletrônicos

Sistema ERP completo e profissional para gestão inteligente de compra, logística, estoque e separação de materiais metálicos e placas eletrônicas, com inteligência artificial, rastreamento GPS e automação completa de processos.

---

## 📋 Índice

- [Visão Geral](#-visão-geral)
- [Módulos do Sistema](#-módulos-do-sistema)
- [Fluxos de Trabalho Detalhados](#-fluxos-de-trabalho-detalhados)
- [Funcionalidades por Perfil](#-funcionalidades-por-perfil)
- [API REST Completa](#-api-rest-completa)
- [Modelos de Dados](#-modelos-de-dados)
- [Tecnologias](#-tecnologias)
- [Instalação e Deploy](#-instalação-e-deploy)
- [Segurança e Auditoria](#-segurança-e-auditoria)

---

## 🎯 Visão Geral

O **MRX Systems** é uma plataforma completa de ERP desenvolvida especificamente para empresas que trabalham com compra, venda e processamento de materiais metálicos e placas eletrônicas. O sistema integra desde a solicitação de compra até a separação final do material, incluindo:

- 🤖 **Inteligência Artificial** para classificação automática de placas eletrônicas
- 📍 **Rastreamento GPS** em tempo real de motoristas e coletas
- 📊 **Dashboard analítico** com métricas e KPIs em tempo real
- 🔔 **Notificações em tempo real** via WebSocket
- 📱 **PWA Mobile** para motoristas e funcionários de campo
- 🏷️ **Sistema de precificação dinâmica** baseado em estrelas e classificação
- 📦 **WMS completo** (Warehouse Management System)
- 🔐 **RBAC** (Role-Based Access Control) granular

### Diferenciais Competitivos

1. **Classificação Inteligente com IA (Gemini AI)**
   - Análise automática de fotos de placas eletrônicas
   - Classificação em: Leve, Média ou Pesada
   - Justificativa textual da classificação
   - Redução de 80% no tempo de avaliação manual

2. **Rastreamento GPS Completo**
   - Localização em tempo real de motoristas
   - Geocoding reverso (GPS → Endereço)
   - Histórico completo de rotas
   - Logs de eventos com coordenadas GPS

3. **Sistema de Precificação Avançado**
   - Preços por fornecedor, tipo de lote e qualidade (1-5 estrelas)
   - Classificação automática: Leve, Médio, Pesado
   - Mapeamento flexível de estrelas por classificação
   - Importação/exportação via Excel

4. **WMS (Warehouse Management System)**
   - Gestão de lotes com código de rastreamento único
   - Movimentação com auditoria completa
   - Inventário cíclico com contagem múltipla
   - Bloqueio/reserva de lotes
   - Separação com registro de resíduos

---

## 🧩 Módulos do Sistema

### 1️⃣ Módulo de Gestão de Usuários e Perfis

**Funcionalidades:**
- Sistema RBAC (Role-Based Access Control) completo
- 7 perfis pré-configurados:
  - Administrador (acesso total)
  - Comprador/PJ (solicitações e fornecedores)
  - Conferente/Estoque (recebimento e conferência)
  - Separação (processos de separação)
  - Motorista (app móvel e coletas)
  - Financeiro (relatórios e pagamentos)
  - Auditoria/BI (apenas leitura e análises)
- Permissões granulares por recurso e ação
- Auditoria completa de ações de usuários
- Histórico de login com sucesso/falha

**API Endpoints:**
```
GET    /api/usuarios              - Listar usuários
GET    /api/usuarios/{id}         - Obter usuário específico
POST   /api/usuarios              - Criar usuário [ADMIN]
PUT    /api/usuarios/{id}         - Atualizar usuário [ADMIN]
DELETE /api/usuarios/{id}         - Excluir usuário [ADMIN]

GET    /api/perfis                - Listar perfis
GET    /api/perfis/{id}           - Obter perfil
POST   /api/perfis                - Criar perfil [ADMIN]
PUT    /api/perfis/{id}           - Atualizar perfil [ADMIN]
DELETE /api/perfis/{id}           - Excluir perfil [ADMIN]
```

---

### 2️⃣ Módulo de Fornecedores e Vendedores

**Funcionalidades:**
- Cadastro completo de fornecedores (PF e PJ)
- Consulta automática de CNPJ via API externa
- Endereços múltiplos (endereço principal + outro endereço)
- Dados bancários (conta, agência, PIX)
- Condições e formas de pagamento
- Sistema de atribuição: admin vincula fornecedores a funcionários
- Funcionários veem apenas fornecedores próprios ou atribuídos
- Cadastro de vendedores associados a fornecedores
- Tipos de lote que o fornecedor comercializa
- Filtros avançados: vendedor, cidade, forma de pagamento

**API Endpoints:**
```
GET    /api/fornecedores                          - Listar fornecedores (filtros: busca, vendedor, cidade)
GET    /api/fornecedores/{id}                     - Obter fornecedor
POST   /api/fornecedores                          - Criar fornecedor
PUT    /api/fornecedores/{id}                     - Atualizar fornecedor
DELETE /api/fornecedores/{id}                     - Excluir fornecedor
POST   /api/fornecedores/{id}/atribuir            - Atribuir fornecedor a funcionário [ADMIN]
GET    /api/fornecedores/{id}/precos              - Listar preços do fornecedor
GET    /api/fornecedores/consultar-cnpj/{cnpj}    - Consultar dados do CNPJ

GET    /api/vendedores                            - Listar vendedores
POST   /api/vendedores                            - Criar vendedor
PUT    /api/vendedores/{id}                       - Atualizar vendedor
DELETE /api/vendedores/{id}                       - Excluir vendedor
```

---

### 3️⃣ Módulo de Tipos de Lote e Preços

**Funcionalidades:**
- Cadastro de tipos de lote (ex: Placa Mãe, HD, Alumínio, Cobre)
- Código automático (TL001, TL002...)
- Até 150 tipos de lote suportados
- Sistema de classificação: Leve, Médio, Pesado
- Tabela de preços por fornecedor + tipo + estrelas (1-5)
- Classificação de estrelas personalizável por fornecedor
- Importação/exportação via Excel
- Modelo de Excel para importação em massa

**Tabelas de Configuração:**

1. **TipoLote** - Define os tipos de material
2. **FornecedorTipoLote** - Quais tipos o fornecedor vende
3. **FornecedorTipoLotePreco** - Preço por kg por tipo e estrelas
4. **FornecedorTipoLoteClassificacao** - Mapeamento: classificação → estrelas

**Exemplo de Precificação:**
```
Fornecedor: João Metais
Tipo: Placa Mãe

Configuração de Classificação:
- Leve   → 1 estrela
- Médio  → 3 estrelas  
- Pesado → 5 estrelas

Tabela de Preços:
- 1 estrela: R$ 5,00/kg
- 2 estrelas: R$ 8,00/kg
- 3 estrelas: R$ 12,00/kg
- 4 estrelas: R$ 18,00/kg
- 5 estrelas: R$ 25,00/kg

Fluxo: IA classifica como "Pesado" → 5 estrelas → R$ 25,00/kg
```

**API Endpoints:**
```
GET    /api/tipos-lote                          - Listar tipos de lote
GET    /api/tipos-lote/{id}                     - Obter tipo
POST   /api/tipos-lote                          - Criar tipo [ADMIN]
PUT    /api/tipos-lote/{id}                     - Atualizar tipo [ADMIN]
DELETE /api/tipos-lote/{id}                     - Excluir tipo [ADMIN]
GET    /api/tipos-lote/modelo-importacao        - Download Excel modelo
POST   /api/tipos-lote/importar-excel           - Importar via Excel [ADMIN]

GET    /api/fornecedor-tipo-lote-precos                  - Listar preços
GET    /api/fornecedor-tipo-lote-precos/{id}             - Obter preço
POST   /api/fornecedor-tipo-lote-precos                  - Criar preço [ADMIN]
PUT    /api/fornecedor-tipo-lote-precos/{id}             - Atualizar preço [ADMIN]
DELETE /api/fornecedor-tipo-lote-precos/{id}             - Excluir preço [ADMIN]
GET    /api/fornecedor-tipo-lote-precos/modelo-excel     - Modelo Excel
POST   /api/fornecedor-tipo-lote-precos/importar-excel   - Importar Excel
GET    /api/fornecedor-tipo-lote-precos/exportar-excel   - Exportar Excel

GET    /api/fornecedor-tipo-lote-classificacoes          - Listar classificações
POST   /api/fornecedor-tipo-lote-classificacoes          - Criar classificação [ADMIN]
PUT    /api/fornecedor-tipo-lote-classificacoes/{id}     - Atualizar [ADMIN]
GET    /api/fornecedor-tipo-lote-classificacoes/modelo-excel   - Modelo
POST   /api/fornecedor-tipo-lote-classificacoes/importar-excel - Importar
GET    /api/fornecedor-tipo-lote-classificacoes/exportar-excel - Exportar
```

---

### 4️⃣ Módulo de Solicitações de Compra com IA

**Funcionalidades:**
- Criação de solicitações por funcionários (compradores)
- Múltiplos itens por solicitação
- Upload de fotos de placas/materiais
- **Análise de imagem com Gemini AI:**
  - Upload de foto
  - IA classifica: Leve, Médio ou Pesado
  - Justificativa da classificação
  - Classificação converte em estrelas
  - Cálculo automático do preço
- Captura de GPS e geocoding reverso
- Tipo de retirada: Buscar ou Entregar
- Endereço do fornecedor ou outro local
- Status: Pendente → Aprovada/Reprovada
- Notificações em tempo real via WebSocket

**Fluxo Completo:**
```
1. Funcionário acessa fornecedor atribuído
2. Tira foto do lote de placas
3. Upload da foto → Gemini AI analisa
4. IA retorna: "Pesado - Alta densidade de componentes"
5. Sistema busca: Pesado → 5 estrelas (config do fornecedor)
6. Sistema busca: 5 estrelas → R$ 25/kg (tabela de preços)
7. Funcionário informa peso: 50kg
8. Sistema calcula: 50kg × R$ 25 = R$ 1.250,00
9. Captura GPS atual
10. Converte GPS em endereço (geocoding reverso)
11. Envia solicitação para aprovação
12. Admin recebe notificação em tempo real (WebSocket)
13. Admin revisa e aprova/reprova
14. Funcionário recebe notificação do resultado
```

**API Endpoints:**
```
POST   /api/solicitacao-lotes/geocode                    - Geocoding reverso (GPS → Endereço)
POST   /api/solicitacao-lotes/analisar-imagem            - Análise com Gemini AI
POST   /api/solicitacao-lotes/upload-imagem              - Upload de foto
GET    /api/solicitacao-lotes/fornecedores-com-tipos     - Fornecedores + Tipos + Preços
POST   /api/solicitacao-lotes/criar                      - Criar solicitação
GET    /api/solicitacao-lotes/aguardando-aprovacao       - Listar pendentes [ADMIN]
PUT    /api/solicitacao-lotes/{id}/aprovar               - Aprovar [ADMIN]
PUT    /api/solicitacao-lotes/{id}/rejeitar              - Reprovar [ADMIN]

GET    /api/solicitacoes                                 - Listar solicitações
GET    /api/solicitacoes/{id}                            - Obter solicitação
POST   /api/solicitacoes                                 - Criar (legado)
POST   /api/solicitacoes/{id}/aprovar                    - Aprovar
POST   /api/solicitacoes/{id}/rejeitar                   - Reprovar
DELETE /api/solicitacoes/{id}                            - Excluir
```

---

### 5️⃣ Módulo de Logística e Ordem de Serviço

**Funcionalidades:**
- **Geração automática de OS** a partir de OC aprovada
- **Cadastro de motoristas** com CPF, CNH e telefone
- **Cadastro de veículos** com placa, modelo e capacidade
- **Atribuição de motorista + veículo** a cada OS
- **Janela de coleta** (data/hora início e fim)
- **App PWA para motoristas** com GPS automático
- **Rastreamento em tempo real** de rotas
- **Registro de eventos:**
  - Saiu da base
  - Chegou no fornecedor
  - Material coletado
  - Saiu do fornecedor
  - Chegou na MRX
  - Entrega finalizada
- **Logs de GPS** salvos a cada evento
- **Reagendamento** com notificação ao motorista
- **Cancelamento** com motivo registrado
- **Quadro Kanban** visual de OS
- **Estatísticas** de performance

**Estados da Ordem de Serviço:**
```
PENDENTE → AGENDADA → EM_ROTA → ENTREGUE → FINALIZADA
                                     ↓
                                CANCELADA
```

**Fluxo do Motorista:**
```
1. Motorista loga no App (/app-motorista)
2. Vê lista de OS atribuídas a ele (status: AGENDADA)
3. Clica em "Iniciar Rota"
   - GPS é capturado automaticamente
   - Status muda para EM_ROTA
4. Chega no fornecedor → Clica "Cheguei"
   - GPS registrado
   - Evento CHEGUEI salvo
5. Coleta material → Clica "Material Coletado"
   - Pode tirar foto como comprovante
   - Evento COLETEI salvo
6. Sai do fornecedor → Clica "Saí"
   - GPS registrado
7. Chega na MRX → Clica "Cheguei na MRX"
   - Status muda para ENTREGUE
8. Conferência realiza pesagem
9. Motorista clica "Finalizar OS"
   - Status muda para FINALIZADA
```

**API Endpoints:**
```
POST   /api/oc/{oc_id}/gerar-os                  - Gerar OS de OC aprovada [ADMIN]
GET    /api/os                                    - Listar OS (filtros: status, motorista, data)
GET    /api/os/{id}                               - Obter OS completa
PUT    /api/os/{id}/atribuir-motorista            - Atribuir motorista/veículo [ADMIN]
POST   /api/os/{id}/reagendar                     - Reagendar coleta [ADMIN]
PUT    /api/os/{id}/iniciar-rota                  - Motorista inicia rota
POST   /api/os/{id}/evento                        - Registrar evento (CHEGUEI, COLETEI, etc)
PUT    /api/os/{id}/cancelar                      - Cancelar OS [ADMIN]
GET    /api/os/estatisticas                       - Estatísticas de OS

GET    /api/motoristas                            - Listar motoristas
GET    /api/motoristas/{id}                       - Obter motorista
GET    /api/motoristas/cpf/{cpf}                  - Buscar por CPF
POST   /api/motoristas                            - Criar motorista [ADMIN]
PUT    /api/motoristas/{id}                       - Atualizar motorista [ADMIN]
DELETE /api/motoristas/{id}                       - Excluir motorista [ADMIN]

GET    /api/veiculos                              - Listar veículos
GET    /api/veiculos/{id}                         - Obter veículo
GET    /api/veiculos/placa/{placa}                - Buscar por placa
POST   /api/veiculos                              - Criar veículo [ADMIN]
PUT    /api/veiculos/{id}                         - Atualizar veículo [ADMIN]
DELETE /api/veiculos/{id}                         - Excluir veículo [ADMIN]
```

---

### 6️⃣ Módulo de Conferência de Recebimento

**Funcionalidades:**
- Iniciado após OS entregue
- Conferente registra:
  - Peso real recebido
  - Qualidade (1-5 estrelas)
  - Fotos do material
  - Observações
- **Detecção automática de divergências:**
  - Compara peso esperado × peso real
  - Calcula % de diferença
  - Se divergência > 5% → envia para decisão admin
- **Workflow de decisão administrativa:**
  - ACEITAR - Aceita como está
  - ACEITAR_COM_DESCONTO - Aceita com desconto (%)
  - REJEITAR - Rejeita o recebimento
- **Criação automática de lote** após aprovação
- Estatísticas de conferências

**Fluxo de Conferência:**
```
1. OS com status ENTREGUE
2. Conferente acessa /conferencia
3. Inicia conferência da OS
4. Sistema busca peso esperado da OC (ex: 50kg)
5. Conferente pesa material real: 48kg
6. Sistema detecta divergência: -2kg (-4%)
7. Como divergência < 5%, aprova automaticamente
8. Cria lote no estoque com 48kg
9. Notifica comprador original

OU (com divergência alta):

5. Conferente pesa: 40kg
6. Sistema detecta: -10kg (-20%)
7. Como divergência > 5%, envia para admin
8. Admin revisa fotos e decide:
   - ACEITAR_COM_DESCONTO: 15% de desconto
   - Recalcula valor da OC
   - Cria lote com peso real
   - Notifica financeiro sobre desconto
```

**API Endpoints:**
```
POST   /api/conferencia/{os_id}/iniciar              - Iniciar conferência
GET    /api/conferencia                              - Listar conferências
GET    /api/conferencia/{id}                         - Obter conferência
PUT    /api/conferencia/{id}/registrar-pesagem       - Registrar peso/qualidade/fotos
PUT    /api/conferencia/{id}/enviar-para-adm         - Enviar divergência para admin
PUT    /api/conferencia/{id}/decisao-adm             - Admin decide (ACEITAR/DESCONTO/REJEITAR)
GET    /api/conferencia/estatisticas                 - Estatísticas
```

---

### 7️⃣ Módulo WMS (Warehouse Management System)

**Funcionalidades Avançadas:**

#### 📦 Gestão de Lotes
- Número único de lote (gerado automaticamente)
- Rastreamento de origem (solicitação, OC, OS, conferência)
- Estados: Disponível, Bloqueado, Reservado, Separado
- Localização atual no estoque
- Hierarquia: lote pai → sublotes
- Peso e quantidade
- Tipo de lote associado
- Fornecedor de origem
- Divergências registradas
- Auditoria completa

#### 🔒 Bloqueio e Reserva
- **Bloqueio:** impede qualquer movimentação
  - Motivo obrigatório
  - Usuário e data de bloqueio
  - Pode ser desbloqueado pelo admin
- **Reserva:** separa para uso específico
  - Reservado para usuário/processo
  - Data de expiração da reserva
  - Libera automaticamente após expiração

#### 📍 Movimentação
- Tipos: Transferência, Entrada, Saída, Ajuste
- Registra: origem, destino, quantidade, peso
- Dados before/after para auditoria
- GPS e device_id do operador
- Observações
- Possibilidade de reversão
- Histórico completo de movimentações

#### 📊 Inventário Cíclico
- **Tipos de inventário:**
  - Geral (todo o estoque)
  - Por localização
  - Por tipo de lote
- **Processo:**
  1. Inicia inventário → bloqueia lotes
  2. Contador registra contagens múltiplas
  3. Pode tirar fotos das contagens
  4. Finaliza inventário → calcula divergências
  5. Consolida → ajusta estoque automaticamente
- **Divergências:**
  - Quantidade faltante/sobrando
  - % de acuracidade
  - Valor da divergência
- **Auditoria:**
  - Quem contou
  - Quando contou
  - Quantas vezes foi contado
  - Fotos anexadas

#### 🔍 Auditoria de Lote
- Histórico completo de ações
- Registro de:
  - Criação
  - Bloqueio/desbloqueio
  - Reserva/liberação
  - Movimentações
  - Separação
  - Inventários
- Dados de cada ação:
  - Usuário
  - Data/hora
  - IP
  - GPS
  - Device ID
  - Valores before/after

**API Endpoints:**
```
# Lotes
GET    /api/wms/lotes                           - Listar lotes (filtros múltiplos)
GET    /api/wms/lotes/{id}                      - Obter lote completo
POST   /api/wms/lotes/{id}/bloquear             - Bloquear lote
POST   /api/wms/lotes/{id}/desbloquear          - Desbloquear lote
POST   /api/wms/lotes/{id}/reservar             - Reservar lote
POST   /api/wms/lotes/{id}/liberar-reserva      - Liberar reserva

# Movimentações
POST   /api/wms/lotes/{id}/movimentar           - Registrar movimentação
GET    /api/wms/movimentacoes                   - Listar movimentações
POST   /api/wms/movimentacoes/{id}/reverter     - Reverter movimentação

# Inventário
POST   /api/wms/inventarios                     - Iniciar inventário
POST   /api/wms/inventarios/{id}/contagem       - Registrar contagem
POST   /api/wms/inventarios/{id}/finalizar      - Finalizar inventário
POST   /api/wms/inventarios/{id}/consolidar     - Consolidar e ajustar estoque
GET    /api/wms/inventarios                     - Listar inventários
GET    /api/wms/inventarios/{id}                - Obter inventário

# Auditoria
GET    /api/wms/auditoria/lotes/{id}            - Histórico do lote

# Estatísticas
GET    /api/wms/estatisticas                    - Métricas WMS
```

---

### 8️⃣ Módulo de Separação de Lotes

**Funcionalidades:**
- Separação física de lotes em componentes
- Registro de peso separado por componente
- Cálculo automático de resíduos
- Tipos de resíduo: Orgânico, Metal, Plástico, Outro
- Fotos do processo de separação
- Aprovação de resíduos pelo supervisor
- Rastreamento de operador
- Tempo de separação
- Rendimento (% aproveitado)

**Fluxo de Separação:**
```
1. Operador seleciona lote disponível
2. Inicia processo de separação
3. Separa componentes:
   - Alumínio: 10kg
   - Cobre: 5kg
   - Plástico: 2kg
4. Resíduo gerado: 3kg (plástico não reciclável)
5. Sistema cria sublotes para cada componente
6. Registra resíduo para aprovação
7. Supervisor aprova/reprova resíduo
8. Lote original marcado como "Separado"
9. Sublotes ficam disponíveis no estoque
```

**API Endpoints:**
```
GET    /api/separacao/fila                      - Lotes aguardando separação
POST   /api/separacao/{lote_id}/iniciar         - Iniciar separação
POST   /api/separacao/{id}/registrar-componente - Registrar componente separado
POST   /api/separacao/{id}/registrar-residuo    - Registrar resíduo
POST   /api/separacao/{id}/finalizar            - Finalizar separação
GET    /api/separacao/estatisticas              - Estatísticas de separação

GET    /api/residuos/pendentes                  - Resíduos aguardando aprovação
PUT    /api/residuos/{id}/aprovar               - Aprovar resíduo [SUPERVISOR]
PUT    /api/residuos/{id}/reprovar              - Reprovar resíduo [SUPERVISOR]
```

---

### 9️⃣ Módulo de Notificações em Tempo Real

**Funcionalidades:**
- WebSocket (Socket.IO) para notificações instantâneas
- Salas separadas por tipo de usuário:
  - Sala "admins" para administradores
  - Salas "user_{id}" para cada funcionário
- Tipos de notificação:
  - Nova solicitação criada
  - Solicitação aprovada/reprovada
  - OS atribuída a motorista
  - Material coletado
  - Divergência de conferência
  - Lote bloqueado/reservado
  - Resíduo para aprovação
- Marcação de lida/não lida
- Contador de não lidas
- Histórico completo
- Push notification (preparado para PWA)

**API Endpoints:**
```
GET    /api/notificacoes                        - Listar notificações do usuário
GET    /api/notificacoes/nao-lidas              - Contar não lidas
PUT    /api/notificacoes/{id}/marcar-lida       - Marcar como lida
PUT    /api/notificacoes/marcar-todas-lidas     - Marcar todas como lidas
```

**Eventos WebSocket:**
```javascript
// Conexão
socket.connect({ token: jwt_token })

// Eventos recebidos
socket.on('nova_notificacao', (data) => { ... })
socket.on('solicitacao_aprovada', (data) => { ... })
socket.on('solicitacao_reprovada', (data) => { ... })
socket.on('os_atribuida', (data) => { ... })
```

---

### 🔟 Módulo de Dashboard e Análises

**Métricas Disponíveis:**
- Total de solicitações (pendentes, aprovadas, reprovadas)
- Total de fornecedores ativos
- Peso total movimentado
- Valor total de compras
- OS por status
- Conferências com divergência
- Lotes por localização
- Acuracidade de inventário
- Performance de motoristas
- Tempo médio de separação
- Rendimento de separação
- Top 10 fornecedores
- Evolução mensal de compras
- Gráficos Chart.js:
  - Compras por mês
  - Fornecedores por ranking
  - OS por status
  - Divergências por período

**API Endpoints:**
```
GET    /api/dashboard/metricas                  - Métricas principais
GET    /api/dashboard/grafico-mensal            - Dados para gráfico mensal
GET    /api/dashboard/top-fornecedores          - Top 10 fornecedores
GET    /api/dashboard/mapa-solicitacoes         - Dados geográficos
```

---

## 🔄 Fluxos de Trabalho Detalhados

### Fluxo Completo: Da Solicitação à Separação

```
┌─────────────────────────────────────────────────────────────┐
│ 1. SOLICITAÇÃO (Funcionário/Comprador)                     │
├─────────────────────────────────────────────────────────────┤
│ ▸ Acessa fornecedor atribuído                              │
│ ▸ Tira foto do lote de placas                              │
│ ▸ IA analisa e classifica (Leve/Médio/Pesado)             │
│ ▸ Sistema mapeia classificação → estrelas                  │
│ ▸ Sistema busca preço na tabela                            │
│ ▸ Informa peso (kg)                                        │
│ ▸ Sistema calcula valor total                              │
│ ▸ Captura GPS e endereço                                   │
│ ▸ Envia solicitação                                        │
└─────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. APROVAÇÃO (Admin)                                        │
├─────────────────────────────────────────────────────────────┤
│ ▸ Recebe notificação em tempo real (WebSocket)            │
│ ▸ Revisa solicitação, fotos e valores                     │
│ ▸ APROVA → Cria Ordem de Compra (OC)                      │
│      OU                                                     │
│ ▸ REPROVA → Notifica funcionário com motivo                │
└─────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. ORDEM DE SERVIÇO (Logística)                            │
├─────────────────────────────────────────────────────────────┤
│ ▸ Sistema gera OS da OC aprovada                           │
│ ▸ Admin atribui motorista + veículo                        │
│ ▸ Define janela de coleta (data/hora)                      │
│ ▸ Status muda para AGENDADA                                │
│ ▸ Motorista recebe notificação                             │
└─────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. COLETA (Motorista via App PWA)                          │
├─────────────────────────────────────────────────────────────┤
│ ▸ Motorista inicia rota (GPS registrado)                   │
│ ▸ Chega no fornecedor (evento + GPS)                       │
│ ▸ Coleta material (foto como comprovante)                  │
│ ▸ Sai do fornecedor (GPS)                                  │
│ ▸ Chega na MRX (GPS)                                       │
│ ▸ Status: ENTREGUE                                         │
└─────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│ 5. CONFERÊNCIA (Conferente)                                │
├─────────────────────────────────────────────────────────────┤
│ ▸ Inicia conferência da OS                                 │
│ ▸ Pesa material                                            │
│ ▸ Compara peso real × esperado                             │
│ ▸ Tira fotos                                               │
│ ▸ Registra qualidade (estrelas)                            │
│                                                             │
│ SE divergência > 5%:                                        │
│   ▸ Envia para decisão administrativa                      │
│   ▸ Admin aprova/desconto/rejeita                          │
│ SENÃO:                                                      │
│   ▸ Aprova automaticamente                                 │
└─────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│ 6. ENTRADA NO ESTOQUE (WMS)                                │
├─────────────────────────────────────────────────────────────┤
│ ▸ Sistema cria lote automaticamente                        │
│ ▸ Gera número único do lote                                │
│ ▸ Atribui localização inicial                              │
│ ▸ Registra origem (solicitação + OC + OS)                  │
│ ▸ Status: DISPONÍVEL                                       │
│ ▸ Rastreabilidade completa ativa                           │
└─────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│ 7. SEPARAÇÃO (Operador de Separação)                       │
├─────────────────────────────────────────────────────────────┤
│ ▸ Seleciona lote para separação                            │
│ ▸ Inicia processo                                          │
│ ▸ Separa fisicamente os componentes:                       │
│   - Alumínio: 10kg → cria sublote                         │
│   - Cobre: 8kg → cria sublote                             │
│   - Plástico: 5kg → cria sublote                          │
│   - Resíduo: 2kg → registra para aprovação                │
│ ▸ Tira fotos do processo                                   │
│ ▸ Finaliza separação                                       │
│ ▸ Lote original: status SEPARADO                           │
│ ▸ Sublotes: status DISPONÍVEL                             │
└─────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│ 8. VENDA/SAÍDA (Comercial)                                 │
├─────────────────────────────────────────────────────────────┤
│ ▸ Reserva lote para cliente                                │
│ ▸ Registra venda                                           │
│ ▸ Movimenta lote para "EXPEDIÇÃO"                          │
│ ▸ Registra saída                                           │
│ ▸ Auditoria completa do ciclo                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 👥 Funcionalidades por Perfil

### 🔴 Administrador
- ✅ Acesso total ao sistema
- ✅ Gerenciar usuários e perfis
- ✅ Gerenciar fornecedores e vendedores
- ✅ Configurar tipos de lote e preços
- ✅ Aprovar/reprovar solicitações
- ✅ Gerenciar ordens de compra
- ✅ Atribuir motoristas a OS
- ✅ Decisões administrativas em conferências
- ✅ Visualizar todas as métricas e relatórios
- ✅ Acesso à auditoria completa
- ✅ Configuração de parâmetros do sistema

### 🟢 Comprador/PJ
- ✅ Visualizar fornecedores atribuídos
- ✅ Criar solicitações de compra
- ✅ Upload de fotos com análise IA
- ✅ Captura de GPS e endereço
- ✅ Visualizar histórico próprio
- ✅ Receber notificações de aprovação/reprovação
- ✅ Dashboard com métricas próprias
- ❌ Não pode aprovar solicitações
- ❌ Não vê dados de outros compradores

### 🟡 Conferente/Estoque
- ✅ Visualizar OS entregues
- ✅ Iniciar conferências
- ✅ Registrar peso, qualidade e fotos
- ✅ Detectar divergências
- ✅ Criar lotes no estoque
- ✅ Movimentar lotes
- ✅ Consultar lotes
- ✅ Realizar inventários
- ❌ Não pode aprovar/reprovar solicitações
- ❌ Não vê informações financeiras

### 🟣 Separação
- ✅ Visualizar fila de separação
- ✅ Iniciar processo de separação
- ✅ Registrar componentes separados
- ✅ Registrar resíduos
- ✅ Tirar fotos do processo
- ✅ Finalizar separações
- ✅ Visualizar histórico de separações
- ❌ Não pode aprovar resíduos
- ❌ Não movimenta lotes diretamente

### 🔵 Motorista
- ✅ Acessar App PWA mobile
- ✅ Visualizar OS atribuídas
- ✅ Iniciar rotas (GPS automático)
- ✅ Registrar eventos da coleta
- ✅ Upload de fotos como comprovante
- ✅ Finalizar OS
- ✅ Histórico de coletas
- ❌ Não vê OS de outros motoristas
- ❌ Não pode reagendar OS

### 🟠 Financeiro
- ✅ Visualizar todas as OCs
- ✅ Visualizar valores e descontos
- ✅ Relatórios financeiros
- ✅ Dashboard de compras
- ✅ Exportar dados para Excel
- ❌ Não pode criar solicitações
- ❌ Não pode aprovar OCs

### ⚪ Auditoria/BI
- ✅ Acesso somente leitura a tudo
- ✅ Visualizar logs de auditoria
- ✅ Dashboards e relatórios completos
- ✅ Exportar dados
- ✅ Rastreabilidade completa
- ❌ Nenhuma ação de modificação
- ❌ Apenas consulta e análise

---

## 📡 API REST Completa

### Resumo de Endpoints por Módulo

**Autenticação** (7 endpoints)
```
POST   /api/auth/login
POST   /api/auth/refresh
GET    /api/auth/me
GET    /api/auth/menus
```

**Usuários e Perfis** (12 endpoints)
```
GET/POST/PUT/DELETE  /api/usuarios
GET/POST/PUT/DELETE  /api/perfis
```

**Fornecedores e Vendedores** (15 endpoints)
```
GET/POST/PUT/DELETE  /api/fornecedores
POST /api/fornecedores/{id}/atribuir
GET  /api/fornecedores/{id}/precos
GET  /api/fornecedores/consultar-cnpj/{cnpj}
GET/POST/PUT/DELETE  /api/vendedores
```

**Tipos de Lote e Preços** (22 endpoints)
```
GET/POST/PUT/DELETE  /api/tipos-lote
GET/POST  /api/tipos-lote/modelo-importacao
GET/POST  /api/tipos-lote/importar-excel
GET/POST/PUT/DELETE  /api/fornecedor-tipo-lote-precos
GET/POST/GET  /api/fornecedor-tipo-lote-precos/modelo-excel
GET/POST/GET  /api/fornecedor-tipo-lote-classificacoes/...
```

**Solicitações** (11 endpoints)
```
GET/POST/DELETE  /api/solicitacoes
POST /api/solicitacoes/{id}/aprovar
POST /api/solicitacoes/{id}/rejeitar
POST /api/solicitacao-lotes/geocode
POST /api/solicitacao-lotes/analisar-imagem
POST /api/solicitacao-lotes/criar
PUT  /api/solicitacao-lotes/{id}/aprovar
PUT  /api/solicitacao-lotes/{id}/rejeitar
```

**Ordens de Compra** (6 endpoints)
```
GET/POST  /api/ordens-compra
GET  /api/ordens-compra/{id}
PUT  /api/ordens-compra/{id}/aprovar
PUT  /api/ordens-compra/{id}/reprovar
```

**Logística - OS** (10 endpoints)
```
POST /api/oc/{oc_id}/gerar-os
GET  /api/os
GET  /api/os/{id}
PUT  /api/os/{id}/atribuir-motorista
POST /api/os/{id}/reagendar
PUT  /api/os/{id}/iniciar-rota
POST /api/os/{id}/evento
PUT  /api/os/{id}/cancelar
GET  /api/os/estatisticas
```

**Motoristas e Veículos** (12 endpoints)
```
GET/POST/PUT/DELETE  /api/motoristas
GET  /api/motoristas/cpf/{cpf}
GET/POST/PUT/DELETE  /api/veiculos
GET  /api/veiculos/placa/{placa}
```

**Conferência** (7 endpoints)
```
POST /api/conferencia/{os_id}/iniciar
GET  /api/conferencia
GET  /api/conferencia/{id}
PUT  /api/conferencia/{id}/registrar-pesagem
PUT  /api/conferencia/{id}/enviar-para-adm
PUT  /api/conferencia/{id}/decisao-adm
GET  /api/conferencia/estatisticas
```

**WMS** (18 endpoints)
```
GET  /api/wms/lotes
GET  /api/wms/lotes/{id}
POST /api/wms/lotes/{id}/bloquear
POST /api/wms/lotes/{id}/desbloquear
POST /api/wms/lotes/{id}/reservar
POST /api/wms/lotes/{id}/liberar-reserva
POST /api/wms/lotes/{id}/movimentar
GET  /api/wms/movimentacoes
POST /api/wms/movimentacoes/{id}/reverter
POST /api/wms/inventarios
POST /api/wms/inventarios/{id}/contagem
POST /api/wms/inventarios/{id}/finalizar
POST /api/wms/inventarios/{id}/consolidar
GET  /api/wms/inventarios
GET  /api/wms/inventarios/{id}
GET  /api/wms/auditoria/lotes/{id}
GET  /api/wms/estatisticas
```

**Separação** (8 endpoints)
```
GET  /api/separacao/fila
POST /api/separacao/{lote_id}/iniciar
POST /api/separacao/{id}/registrar-componente
POST /api/separacao/{id}/registrar-residuo
POST /api/separacao/{id}/finalizar
GET  /api/separacao/estatisticas
GET  /api/residuos/pendentes
PUT  /api/residuos/{id}/aprovar
PUT  /api/residuos/{id}/reprovar
```

**Notificações** (4 endpoints)
```
GET  /api/notificacoes
GET  /api/notificacoes/nao-lidas
PUT  /api/notificacoes/{id}/marcar-lida
PUT  /api/notificacoes/marcar-todas-lidas
```

**Dashboard** (5 endpoints)
```
GET  /api/dashboard/metricas
GET  /api/dashboard/grafico-mensal
GET  /api/dashboard/top-fornecedores
GET  /api/dashboard/mapa-solicitacoes
GET  /api/dashboard/estatisticas
```

**TOTAL: 147+ endpoints**

---

## 🗄️ Modelos de Dados

### Principais Entidades

**Usuario**
- id, nome, email, senha_hash, tipo (admin/funcionario)
- perfil_id → Perfil
- ativo, data_cadastro, criado_por

**Perfil**
- id, nome, descricao
- permissoes (JSON com granularidade por recurso)
- ativo, data_cadastro

**Fornecedor**
- id, nome, nome_social, cnpj, cpf
- endereco (rua, numero, cidade, cep, estado, bairro, complemento)
- tem_outro_endereco, outro_* (segundo endereço)
- telefone, email
- vendedor_id → Vendedor
- criado_por_id → Usuario
- dados_bancarios (conta, agencia, chave_pix, banco)
- condicao_pagamento, forma_pagamento
- ativo, data_cadastro

**TipoLote**
- id, nome, descricao, codigo (TL001...)
- classificacao (leve/medio/pesado)
- ativo, data_cadastro

**FornecedorTipoLotePreco**
- id, fornecedor_id, tipo_lote_id
- estrelas (1-5)
- preco_por_kg
- ativo, data_cadastro

**FornecedorTipoLoteClassificacao**
- id, fornecedor_id, tipo_lote_id
- leve_estrelas, medio_estrelas, pesado_estrelas
- ativo, data_cadastro

**Solicitacao**
- id, funcionario_id → Usuario, fornecedor_id → Fornecedor
- tipo_retirada (buscar/entregar)
- status (pendente/aprovada/reprovada)
- observacoes, data_envio, data_confirmacao
- admin_id → Usuario (quem aprovou)
- endereco (rua, numero, cep, localizacao_lat, localizacao_lng)
- itens → ItemSolicitacao[]

**ItemSolicitacao**
- id, solicitacao_id, tipo_lote_id
- peso_kg, estrelas_classificacao
- preco_por_kg, valor_calculado
- fotos[] (paths), analise_ia (JSON)

**OrdemCompra (OC)**
- id, solicitacao_id → Solicitacao
- numero_oc, fornecedor_id
- total_peso, total_valor
- status (pendente/aprovada/reprovada)
- aprovado_por_id → Usuario
- data_aprovacao, observacoes

**OrdemServico (OS)**
- id, oc_id → OrdemCompra
- numero_os
- motorista_id → Motorista, veiculo_id → Veiculo
- fornecedor_snapshot (JSON)
- tipo (COLETA/ENTREGA)
- janela_coleta_inicio, janela_coleta_fim
- rota (JSON), status
- gps_logs → GPSLog[]
- eventos → RotaOperacional[]
- criado_em, created_by

**Motorista**
- id, nome, cpf, cnh, telefone
- usuario_id → Usuario
- ativo, data_cadastro

**Veiculo**
- id, placa, modelo, marca
- capacidade_kg, ativo

**GPSLog**
- id, os_id → OrdemServico
- latitude, longitude, precisao
- timestamp, evento

**ConferenciaRecebimento**
- id, os_id → OrdemServico, oc_id → OrdemCompra
- conferente_id → Usuario
- peso_esperado, peso_real
- divergencia_kg, divergencia_percentual
- qualidade_estrelas, fotos[]
- status (pendente/aprovada/aguardando_adm/reprovada)
- decisao_admin, decisao_admin_id → Usuario
- percentual_desconto, motivo_decisao

**Lote**
- id, numero_lote (único)
- tipo_lote_id → TipoLote
- fornecedor_id → Fornecedor
- solicitacao_id, ordem_compra_id, ordem_servico_id, conferencia_id
- peso_kg, quantidade
- localizacao_atual, bloqueado, motivo_bloqueio
- reservado, reservado_para_id → Usuario
- data_expiracao_reserva
- lote_pai_id → Lote (hierarquia)
- divergencias (JSON)
- auditoria (JSON[])
- data_criacao

**MovimentacaoEstoque**
- id, lote_id → Lote
- tipo (transferencia/entrada/saida/ajuste)
- localizacao_origem, localizacao_destino
- quantidade, peso
- usuario_id → Usuario
- dados_before, dados_after (JSON)
- auditoria (JSON)
- data_movimentacao

**Inventario**
- id, tipo (geral/localizacao/tipo_lote)
- localizacao, tipo_lote_id
- status (em_andamento/finalizado/consolidado)
- iniciado_por_id → Usuario
- data_inicio, data_fim
- contagens → InventarioContagem[]

**InventarioContagem**
- id, inventario_id → Inventario, lote_id → Lote
- contador_id → Usuario
- quantidade_contada, peso_contado
- fotos[], observacoes
- data_contagem

**LoteSeparacao**
- id, lote_id → Lote
- operador_id → Usuario
- data_inicio, data_fim
- componentes_separados (JSON[])
- fotos[], observacoes
- status (em_andamento/finalizada)

**Residuo**
- id, separacao_id → LoteSeparacao
- tipo (organico/metal/plastico/outro)
- peso_kg, descricao
- aprovado, aprovado_por_id → Usuario
- data_aprovacao

**Notificacao**
- id, usuario_id → Usuario
- titulo, mensagem, tipo
- lida, data_envio

**AuditoriaLog**
- id, usuario_id → Usuario
- entidade, entidade_id
- acao (CREATE/UPDATE/DELETE/APPROVE/REJECT)
- dados_before, dados_after (JSON)
- ip, gps, device_id
- timestamp

---

## 🛠️ Tecnologias

### Backend
- **Python 3.11+** - Linguagem principal
- **Flask 3.0** - Framework web
- **SQLAlchemy** - ORM para PostgreSQL
- **Flask-JWT-Extended** - Autenticação JWT
- **Flask-SocketIO** - WebSocket em tempo real
- **Flask-CORS** - CORS para API REST
- **Flask-Migrate** - Migrations de banco de dados
- **bcrypt** - Hash de senhas
- **psycopg2-binary** - Driver PostgreSQL

### Inteligência Artificial
- **Google Gemini AI (gemini-2.0-flash-exp)** - Análise de imagens
- **google-genai** - SDK oficial do Gemini
- Classificação: Leve, Médio, Pesado
- Análise de densidade de componentes eletrônicos

### Frontend
- **HTML5, CSS3, JavaScript** - Tecnologias web padrão
- **Chart.js** - Gráficos e visualizações
- **Leaflet.js** - Mapas interativos
- **Socket.IO Client** - WebSocket client-side
- **Service Worker** - PWA e cache offline
- **Geolocation API** - GPS do navegador

### Banco de Dados
- **PostgreSQL** - Banco de dados principal
- Suporte a JSON (JSONB) para dados flexíveis
- Índices otimizados para performance
- Constraints e foreign keys

### Infraestrutura
- **Gunicorn** - WSGI HTTP Server
- **Eventlet** - Async workers para WebSocket
- **Pillow** - Processamento de imagens
- **OpenCV** - Análise de imagens (headless)
- **Pandas, openpyxl** - Importação/exportação Excel
- **Requests** - Cliente HTTP
- **python-dotenv** - Variáveis de ambiente

### Deploy
- **Railway** - Platform as a Service
- **Neon PostgreSQL** - Banco de dados serverless
- **Dockerfile** - Containerização
- **Gunicorn + Eventlet** - Production server

---

## 🚀 Instalação e Deploy

### Requisitos
- Python 3.11+
- PostgreSQL 14+
- Node.js 18+ (opcional, para dev frontend)

### Instalação Local

```bash
# 1. Clonar repositório
git clone <seu-repositorio>
cd mrx-systems

# 2. Criar ambiente virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# 3. Instalar dependências
pip install -r requirements.txt

# 4. Configurar variáveis de ambiente
cp .env.example .env
nano .env

# Variáveis obrigatórias:
# DATABASE_URL=postgresql://user:pass@localhost/mrx_db
# JWT_SECRET_KEY=<chave-secreta-forte>
# SESSION_SECRET=<outra-chave-secreta>
# GEMINI_API_KEY=<sua-chave-gemini>
# ADMIN_EMAIL=admin@mrx.com
# ADMIN_PASSWORD=<senha-forte>

# 5. Criar banco de dados
createdb mrx_db

# 6. Executar migrations
flask db upgrade

# 7. Inicializar dados padrão
python init_db.py

# 8. Executar desenvolvimento
python app.py
```

Acesse: http://localhost:5000

**Credenciais padrão:**
- Email: admin@sistema.com
- Senha: admin123

### Deploy no Railway

#### Passo 1: Preparar Repositório
```bash
# Certifique-se de ter os arquivos:
# - requirements.txt
# - Procfile (ou railway.json)
# - Dockerfile (opcional)
# - .gitignore

# Procfile deve conter:
web: gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:$PORT app:app
```

#### Passo 2: Criar Projeto no Railway
1. Acesse https://railway.app
2. Clique em "New Project"
3. Escolha "Deploy from GitHub repo"
4. Selecione seu repositório

#### Passo 3: Adicionar PostgreSQL
1. No projeto Railway, clique em "+ New"
2. Selecione "Database" → "PostgreSQL"
3. Railway cria automaticamente a variável `DATABASE_URL`

#### Passo 4: Configurar Variáveis de Ambiente
No painel do Railway, adicione:

```bash
DATABASE_URL=<gerado-automaticamente>
JWT_SECRET_KEY=<gerar-chave-forte>
SESSION_SECRET=<gerar-chave-forte>
GEMINI_API_KEY=<sua-chave-da-google>
ADMIN_EMAIL=seu-email@empresa.com
ADMIN_PASSWORD=<senha-forte-producao>
PORT=5000
```

**Gerar chaves secretas:**
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

#### Passo 5: Deploy
Railway fará deploy automaticamente quando você fazer push:

```bash
git add .
git commit -m "Deploy inicial"
git push origin main
```

#### Passo 6: Executar Migrations
No Railway, abra o terminal e execute:

```bash
flask db upgrade
python init_db.py
```

#### Passo 7: Configurar Domínio (Opcional)
1. No Railway, vá em "Settings"
2. Em "Domains", clique em "Generate Domain"
3. Ou adicione domínio customizado

### Configuração de Produção

**Importante para Produção:**

1. **Segurança:**
   - Altere TODAS as senhas padrão
   - Use HTTPS (Railway fornece automaticamente)
   - Configure CORS adequadamente
   - Mantenha JWT_SECRET_KEY seguro

2. **Performance:**
   - Configure workers do Gunicorn conforme CPU:
     ```bash
     gunicorn --worker-class eventlet -w 4 --bind 0.0.0.0:$PORT app:app
     ```
   - Habilite cache de assets
   - Configure CDN para imagens (se necessário)

3. **Backup:**
   - Configure backup automático do PostgreSQL
   - Railway oferece snapshots automáticos
   - Ou configure backup manual:
     ```bash
     pg_dump $DATABASE_URL > backup.sql
     ```

4. **Monitoramento:**
   - Habilite logs no Railway
   - Configure alertas de erro
   - Monitore uso de recursos

5. **Variáveis de Ambiente de Produção:**
   ```bash
   FLASK_ENV=production
   DEBUG=False
   LOG_LEVEL=WARNING
   ```

---

## 🔐 Segurança e Auditoria

### Autenticação
- **JWT (JSON Web Tokens)**
  - Access token: 24h de validade
  - Refresh token: 30 dias
  - Claims customizados: user_id, tipo, perfil_id, permissoes
- **Bcrypt** para hash de senhas (10 rounds)
- **Password policy** recomendado: mínimo 8 caracteres

### Autorização (RBAC)
- Controle granular por perfil
- Middleware `@admin_required` para rotas administrativas
- Middleware `@jwt_required()` para rotas autenticadas
- Verificação de permissões por recurso e ação

### Auditoria Completa
Todas as ações críticas são registradas:
- Quem executou (usuario_id)
- O que foi feito (ação: CREATE, UPDATE, DELETE, APPROVE, etc)
- Quando (timestamp UTC)
- Onde (IP, GPS, device_id)
- Dados before/after (JSON completo)

**Ações auditadas:**
- Criação/edição/exclusão de usuários
- Criação/aprovação/reprovação de solicitações
- Criação/aprovação de OCs
- Atribuição de motoristas
- Início/eventos/finalização de OS
- Conferências e decisões administrativas
- Bloqueio/desbloqueio de lotes
- Reserva/liberação de lotes
- Movimentações de estoque
- Inventários
- Separações
- Aprovação de resíduos

### Proteção de Dados Sensíveis
- Senhas nunca expostas na API
- Dados bancários apenas para admin/financeiro
- Logs de GPS criptografados (recomendado)
- CORS configurado apenas para domínios autorizados
- Validação de inputs em todas as rotas
- Sanitização de dados do usuário
- Upload de arquivos com validação de tipo e tamanho

### Rastreabilidade
- Código único de lote rastreável em toda a cadeia
- Histórico completo desde solicitação até separação
- GPS logs em todas as etapas de coleta
- Fotos anexadas em múltiplos pontos
- Auditoria JSON com versionamento de dados

---

## 📱 Progressive Web App (PWA)

O sistema é uma PWA completa:

### Funcionalidades PWA
- ✅ **Instalável** em Android e iOS
- ✅ **Ícone na tela inicial**
- ✅ **Service Worker** para cache
- ✅ **Offline-first** (navegação básica)
- ✅ **Push notifications** (preparado)
- ✅ **Tela de splash**
- ✅ **Modo standalone** (sem barra de navegador)

### Configuração
- **Manifest.json** configurado
  - Nome: MRX Systems
  - Ícones: 192x192 e 512x512
  - Theme color: #10b981
  - Display: standalone
  - Orientation: portrait

- **Service Worker** (sw.js)
  - Cache de assets estáticos
  - Cache de rotas principais
  - Estratégia: Cache First para assets, Network First para API

### Instalação
1. Acesse o sistema via navegador mobile
2. Popup automático oferece instalação
3. Ou menu → "Adicionar à tela inicial"
4. App fica disponível como aplicativo nativo

---

## 📊 Métricas e KPIs

### Dashboard Principal
- Total de solicitações (hoje, semana, mês)
- Taxa de aprovação
- Tempo médio de aprovação
- Peso total movimentado
- Valor total de compras
- Top 10 fornecedores
- OS por status
- Acuracidade de inventário
- Taxa de divergência em conferências

### Métricas por Módulo

**Compras:**
- Valor total por período
- Peso total por período
- Número de solicitações por status
- Taxa de aprovação %
- Tempo médio de resposta

**Logística:**
- OS por status
- Tempo médio de coleta
- Distância total percorrida
- Performance por motorista
- Taxa de pontualidade

**Conferência:**
- Total de conferências
- Divergências detectadas
- Taxa de divergência %
- Valor de descontos aplicados
- Tempo médio de conferência

**WMS:**
- Lotes ativos
- Lotes bloqueados/reservados
- Ocupação por localização
- Movimentações por dia
- Acuracidade de inventário

**Separação:**
- Lotes separados
- Rendimento médio %
- Tempo médio de separação
- Resíduos por tipo
- Taxa de aprovação de resíduos

---

## 🎓 Treinamento e Suporte

### Materiais de Treinamento Incluídos
- `/GUIA_TESTE_RBAC.md` - Guia de testes de permissões
- `/LOGISTICA_GUIDE.md` - Guia completo de logística
- `/GUIA_APP_MOTORISTA.md` - Manual do aplicativo do motorista
- `/INSTRUCOES_MODULO_LOTES.md` - Instruções de módulo de lotes
- `/RAILWAY_DEPLOYMENT_GUIDE.md` - Guia de deploy no Railway

### Fluxos de Trabalho Documentados
Cada módulo possui:
- Descrição de funcionalidades
- Fluxo passo a passo
- Screenshots (quando aplicável)
- Exemplos de uso
- Troubleshooting

### Suporte Técnico
Para suporte técnico, consulte:
- Documentação inline no código
- Logs de auditoria para rastreamento de problemas
- Variáveis de ambiente para debug

---

## 📄 Licença

Este projeto foi desenvolvido para gestão interna de compras e processamento de materiais metálicos e eletrônicos.

**Desenvolvido em:** Novembro de 2025  
**Versão:** 2.0.0  
**Última atualização:** 18/11/2025

---

## 🏆 Resumo de Funcionalidades

✅ Sistema ERP completo para metais e eletrônicos  
✅ 7 perfis de usuário com RBAC granular  
✅ Inteligência Artificial (Gemini) para classificação  
✅ Rastreamento GPS em tempo real  
✅ WebSocket para notificações instantâneas  
✅ WMS completo com inventário cíclico  
✅ Módulo de separação com rastreamento de resíduos  
✅ App PWA para motoristas  
✅ Sistema de precificação dinâmica  
✅ Auditoria completa de todas as operações  
✅ Dashboard analítico com métricas em tempo real  
✅ Importação/exportação via Excel  
✅ Geocoding e mapas interativos  
✅ Conferência com detecção de divergências  
✅ 147+ endpoints REST  
✅ Totalmente responsivo e mobile-first  

---

**Desenvolvido com ❤️ para otimizar a gestão de materiais metálicos e eletrônicos**
#   S i s t e m a M R X  
 