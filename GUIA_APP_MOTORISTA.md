# Guia do App Motorista

## Correções Realizadas

### 1. Criação de Registro de Motorista
- ✅ O usuário de teste `motorista@teste.com` agora possui um registro correspondente na tabela `motoristas`
- ✅ Senha: `teste123`

### 2. Atribuição de Ordem de Serviço
- ✅ A OS `OS-20251115-491FB5` foi atribuída ao motorista de teste
- ✅ Status atual: `AGENDADA`

### 3. Correção de Autenticação
- ✅ Corrigido problema de token no app do motorista
  - O app estava buscando `access_token`, mas o sistema salva como `token`
  - Adicionada validação de token
  - Redireciona para login se o token estiver inválido ou ausente

### 4. Script de Criação de Usuários Atualizado
- ✅ O script `criar_usuarios_teste.py` agora cria automaticamente registros de motorista
- ✅ Valida se usuários existentes com perfil "Motorista" têm registro de motorista

## Como Usar o App Motorista

### Passo 1: Fazer Login
1. Acesse a página inicial: `/`
2. Faça login com as credenciais:
   - **Email:** `motorista@teste.com`
   - **Senha:** `teste123`

### Passo 2: Acessar o App
1. Após o login, acesse: `/app-motorista`
2. O app solicitará permissão para acessar sua localização (GPS)
3. Conceda a permissão para usar todas as funcionalidades

### Passo 3: Visualizar OSs
- O app exibe 3 abas:
  - **Pendentes:** OSs com status AGENDADA ou PENDENTE
  - **Em Rota:** OSs em andamento (EM_ROTA, NO_FORNECEDOR, COLETADO, A_CAMINHO_MATRIZ, ENTREGUE)
  - **Finalizadas:** OSs concluídas

### Passo 4: Fluxo de Trabalho

#### 4.1 Iniciar Rota
1. Na aba "Pendentes", clique em **Iniciar Rota**
2. O GPS deve estar ativo
3. A OS mudará para status EM_ROTA

#### 4.2 Registrar Chegada no Fornecedor
1. Quando chegar no fornecedor, clique em **Cheguei no Fornecedor**
2. Status muda para NO_FORNECEDOR

#### 4.3 Coletar Material
1. Após coletar o material, clique em **Material Coletado**
2. Status muda para COLETADO

#### 4.4 Sair do Fornecedor
1. Ao sair, clique em **Saí do Fornecedor**
2. Status muda para A_CAMINHO_MATRIZ

#### 4.5 Chegar na Matriz
1. Ao chegar na matriz MRX, clique em **Cheguei na MRX**
2. Status muda para ENTREGUE

#### 4.6 Finalizar OS
1. Após entregar o material, clique em **Finalizar OS**
2. Status muda para FINALIZADA
3. A OS aparecerá na aba "Finalizadas"

## Observações Importantes

### GPS
- ⚠️ O GPS **DEVE** estar ativo para:
  - Iniciar rotas
  - Registrar eventos
- Indicador de GPS (canto inferior direito):
  - 🔵 **Aguardando GPS:** Ícone girando (aguardando primeira localização)
  - 🟢 **GPS Ativo:** Ícone de check verde (pronto para uso)
  - 🔴 **GPS Inativo:** Ícone de alerta vermelho (erro ou permissão negada)
- ⏱️ **Importante:** Aguarde alguns segundos após abrir o app para o GPS obter a primeira localização antes de tentar iniciar rotas

### Atualização Automática
- O app atualiza automaticamente a cada 30 segundos
- Você pode forçar uma atualização recarregando a página

### Eventos com Observações
- Ao registrar cada evento, você pode adicionar observações opcionais
- Útil para reportar problemas ou informações adicionais

## Solução de Problemas

### "Token não encontrado"
- **Causa:** Não está logado ou o token expirou
- **Solução:** Faça login novamente em `/`

### "GPS não está ativo" ou "Aguardando primeira localização GPS"
- **Causas possíveis:**
  1. GPS ainda está obtendo a primeira localização (aguarde 5-10 segundos)
  2. Permissão de localização não concedida
  3. GPS do dispositivo está desligado
  4. Navegador não suporta geolocalização
- **Solução:**
  1. Verifique se o indicador GPS mostra "GPS Ativo" (ícone verde com check)
  2. Se mostrar "Aguardando GPS", aguarde alguns segundos
  3. Se mostrar "GPS Inativo":
     - Verifique as configurações do navegador
     - Conceda permissão de localização
     - Ative o GPS do dispositivo
     - Recarregue a página
  4. Abra o console do navegador (F12) para ver logs detalhados do GPS

### OSs não aparecem
- **Causas possíveis:**
  1. Não há OSs atribuídas a você
  2. Token inválido
  3. Não está logado
- **Solução:**
  1. Verifique se está logado como motorista
  2. Entre em contato com o administrador para atribuir OSs

## Credenciais de Teste

| Email | Senha | Perfil |
|-------|-------|--------|
| motorista@teste.com | teste123 | Motorista |

## API Endpoints Utilizados

- `GET /api/os` - Lista OSs do motorista
- `PUT /api/os/{id}/iniciar-rota` - Inicia uma rota
- `POST /api/os/{id}/evento` - Registra eventos (CHEGUEI, COLETEI, SAI, CHEGUEI_MRX, FINALIZEI)

## Logs e Auditoria

Todos os eventos são registrados com:
- ✅ Localização GPS (latitude, longitude, precisão)
- ✅ Device ID (identificador único do dispositivo)
- ✅ Timestamp
- ✅ Observações (quando fornecidas)
- ✅ IP e User Agent do navegador

## Debug e Logs do Console

Para ver informações detalhadas sobre o GPS e operações:
1. Abra o console do navegador (F12 ou Ctrl+Shift+I)
2. Vá para a aba "Console"
3. Você verá logs como:
   - 🌍 "Inicializando GPS..."
   - ✅ "GPS ativo: {latitude, longitude, precisao}"
   - 🚗 "Tentando iniciar rota..."
   - 📍 "Iniciando rota com GPS: ..."
   - ❌ Erros detalhados se houver problemas

Isso ajuda a identificar problemas com GPS, autenticação ou conexão.
