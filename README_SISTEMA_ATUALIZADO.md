# Sistema MRX - Atualização de Funcionalidades

## Resumo das Modificações

Este documento descreve as principais modificações implementadas no sistema MRX conforme solicitado.

## 1. Alterações de Nomenclatura

- **"Relatórios"** foi alterado para **"Solicitações"** em todo o sistema
- Arquivo `relatorios.html` renomeado para `solicitacoes.html`
- Novas rotas criadas em `/api/solicitacoes`
- Rotas antigas em `/api/relatorios` mantidas para compatibilidade

## 2. Estrutura de Empresas - Novos Campos

### Campos Obrigatórios Adicionados:
- Nome social
- CNPJ (já existia)
- CPF
- **Endereços:**
  - Endereço de coleta
  - Endereço de emissão
  - Rua, número, cidade, CEP, estado
- Telefone
- E-mail
- **Associação com vendedor** (relacionamento com tabela `vendedores`)
- **Dados bancários:**
  - Conta bancária
  - Agência
  - Chave Pix
  - Banco
- **Condições de pagamento:** à vista ou parcelado
- **Forma de pagamento:** cheque, pix, ted ou boleto

### Funcionalidades de Empresas:
- Filtros de busca por nome, CNPJ, CPF, email, vendedor, cidade, forma/condição de pagamento
- Perfil da empresa exibe histórico completo de solicitações e placas
- Endpoint `/api/empresas/<id>/historico` retorna todas as solicitações e placas

## 3. Sistema de Solicitações

### Estrutura:
- Cada empresa pode ter várias solicitações
- Cada solicitação pode conter várias placas
- Ao abrir uma solicitação, é possível lançar placas dentro dela

### Endpoints Principais:
- `GET /api/solicitacoes` - Listar solicitações
- `POST /api/solicitacoes` - Criar nova solicitação
- `POST /api/solicitacoes/<id>/placas` - Adicionar placa à solicitação
- `PUT /api/solicitacoes/<id>/confirmar` - Confirmar solicitação (envia para Entradas)

## 4. Placas - Perfil Individual

### Campos de Placa:
- **Tag única** (gerada automaticamente - 8 caracteres alfanuméricos)
- Empresa de origem
- Solicitação vinculada
- Data da compra
- Peso (kg)
- Valor (R$)
- Status atual: `em_analise`, `entrada`, `aprovada`, `reprovada`
- Tipo: leve, média ou pesada
- Imagem
- Localização

### Consulta Avançada:
Tela específica em `/consulta-placas.html` com filtros por:
- Empresa
- Peso (mínimo e máximo)
- Valor (mínimo e máximo)
- Data de compra
- Tag
- Status
- Vendedor
- Forma de pagamento
- Condição de pagamento
- Tipo de placa

Endpoint: `GET /api/placas/consulta` com parâmetros de filtro

## 5. Sistema de Entradas e Aprovações

### Fluxo:
1. Funcionário cria uma **Solicitação** e adiciona placas
2. Funcionário **confirma** a solicitação
3. Sistema cria automaticamente uma **Entrada** com status "pendente"
4. Todas as placas da solicitação são agrupadas em lote
5. Admin acessa tela **Entradas** (`/entradas.html`)
6. Admin pode:
   - **Aprovar** a entrada → placas vão para status "aprovada" e são inseridas no banco principal
   - **Reprovar** a entrada → placas vão para status "reprovada"

### Endpoints de Entradas:
- `GET /api/entradas` - Listar entradas (com filtro por status)
- `GET /api/entradas/<id>` - Detalhes da entrada
- `PUT /api/entradas/<id>/aprovar` - Aprovar entrada
- `PUT /api/entradas/<id>/reprovar` - Reprovar entrada
- `GET /api/entradas/estatisticas` - Estatísticas gerais

## 6. Vendedores

Nova tabela para gerenciar vendedores associados às empresas.

### Campos:
- Nome
- Email
- Telefone
- CPF
- Status (ativo/inativo)

### Endpoints:
- `GET /api/vendedores` - Listar vendedores
- `POST /api/vendedores` - Criar vendedor
- `PUT /api/vendedores/<id>` - Atualizar vendedor
- `DELETE /api/vendedores/<id>` - Deletar vendedor

## 7. Migração do Banco de Dados

⚠️ **IMPORTANTE:** Para bancos de dados existentes, é necessário executar a migração SQL antes de usar o sistema atualizado.

### Executar Migração:

```bash
# Se estiver usando PostgreSQL via psql
psql -U <usuario> -d <nome_banco> -f migrations/001_add_new_fields.sql

# Ou via ferramenta de banco de dados
# Execute o script migrations/001_add_new_fields.sql no seu banco
```

### O que a migração faz:
- Cria tabela `vendedores`
- Cria tabela `solicitacoes`
- Cria tabela `entradas`
- Adiciona novos campos à tabela `empresas`
- Adiciona novos campos à tabela `placas` (tag, status, etc.)
- Cria índices para melhor performance

## 8. Novos Templates HTML

### Criados:
- `entradas.html` - Tela de aprovação de lotes de placas
- `consulta-placas.html` - Tela de consulta avançada de placas

### Modificados:
- `relatorios.html` → renomeado para `solicitacoes.html`
- Todos os templates HTML - "Relatórios" alterado para "Solicitações"
- Links de navegação atualizados

## 9. Compatibilidade com Sistema Antigo

- Modelo `Relatorio` mantido para compatibilidade
- Rotas `/api/relatorios` mantidas
- Não há perda de dados existentes

## 10. Fluxo Completo de Uso

### Para Funcionários:
1. Criar nova Solicitação (escolher empresa)
2. Adicionar placas à solicitação (uma por uma)
3. Confirmar solicitação quando terminar
4. Sistema envia para Entradas automaticamente

### Para Administradores:
1. Acessar tela "Entradas"
2. Visualizar solicitações pendentes
3. Ver todas as placas do lote
4. Aprovar ou Reprovar
5. Sistema atualiza status automaticamente e notifica funcionário

## Observações Técnicas

- Tags de placas são geradas automaticamente como UUIDs de 8 caracteres
- Todos os relacionamentos usam chaves estrangeiras com integridade referencial
- Sistema de notificações via WebSocket mantido
- Autenticação JWT mantida
- CORS configurado para acesso cross-origin

## Próximos Passos Sugeridos

1. Executar a migração SQL no banco de dados
2. Testar fluxo completo de solicitação → entrada → aprovação
3. Treinar usuários sobre novo fluxo
4. Configurar vendedores no sistema
5. Atualizar dados de empresas com novos campos
