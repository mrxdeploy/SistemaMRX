# Módulo de Solicitação, Aprovação e Entrada de Lotes

## Implementado em: 10/11/2025

Este documento descreve o novo módulo completo de gestão de lotes com classificação inteligente por IA.

## 📋 Funcionalidades Implementadas

### 1. Solicitação de Compra de Lote
- **Rota**: `/api/solicitacao-lotes/criar`
- **Tela**: `solicitacao_compra.html`
- **Funcionalidades**:
  - Seleção de fornecedor
  - Seleção de tipo de lote vinculado ao fornecedor
  - Upload de foto do lote
  - Análise automática com IA Gemini (classifica como leve, médio ou pesado)
  - Classificação manual editável
  - Cálculo automático de valor baseado em estrelas e peso
  - Envio de solicitação com status "aguardando_aprovacao"

### 2. Aprovação de Solicitações
- **Rota**: `/api/solicitacao-lotes/aguardando-aprovacao`
- **Tela**: `aprovar_solicitacoes.html`
- **Funcionalidades**:
  - Listagem de todas as solicitações pendentes
  - Visualização de imagens dos lotes
  - Aprovação ou rejeição de solicitações
  - Visualização da sugestão da IA vs classificação final

### 3. Lotes Aprovados
- **Rota**: `/api/solicitacao-lotes/aprovadas`
- **Tela**: `lotes_aprovados.html`
- **Funcionalidades**:
  - Listagem de lotes aprovados
  - Registro de entrada física (quando o lote chega)
  - Move para tela de entradas ao receber

### 4. Configuração de Fornecedores
- **Rota**: `/api/solicitacao-lotes/configuracao/fornecedor/{id}/tipo/{id}`
- **Funcionalidades**:
  - Definir quantidade de estrelas por classificação
  - Configurar leve, médio e pesado para cada fornecedor/tipo

## 🗄️ Estrutura do Banco de Dados

### Tabela: `fornecedor_tipo_lote_classificacao`
```sql
- id (serial)
- fornecedor_id (FK)
- tipo_lote_id (FK)
- leve_estrelas (1-5)
- medio_estrelas (1-5)
- pesado_estrelas (1-5)
- ativo (boolean)
- data_cadastro, data_atualizacao
```

### Campos Adicionados:
- `itens_solicitacao.classificacao` (leve, medio, pesado)
- `itens_solicitacao.classificacao_sugerida_ia` (sugestão da IA)
- `lotes.classificacao_predominante`

### Configuração Global:
- `valor_base_por_estrela` = 1.00 (configurável)

## 📐 Lógica de Cálculo

```
valor_unitario = valor_base_por_estrela * numero_de_estrelas
valor_total = valor_unitario * peso_kg
```

**Exemplo**:
- Fornecedor: ABC Eletrônicos
- Tipo: Placas de Computador
- Classificação: PESADO (configurado com 5 estrelas)
- Peso: 10 kg
- Valor base: R$ 1,00

Cálculo: 1,00 × 5 × 10 = **R$ 50,00**

## 🤖 Integração com IA Gemini

### Modelo: `gemini-2.0-flash-exp`

A IA analisa a imagem da placa e classifica baseado em:
- **LEVE**: Poucos componentes, circuitos simples
- **MÉDIO**: Quantidade moderada de componentes
- **PESADO**: Muitos componentes, alta densidade

A sugestão pode ser editada manualmente pelo usuário.

## 📁 Arquivos Criados/Modificados

### Backend:
- `app/routes/solicitacao_lotes.py` (NOVO)
- `app/models.py` (modificado - novo modelo)
- `app/__init__.py` (modificado - registro de blueprint)
- `migrations/004_add_classificacao_lotes.sql` (NOVO)

### Frontend:
- `app/templates/solicitacao_compra.html` (NOVO)
- `app/templates/aprovar_solicitacoes.html` (NOVO)
- `app/templates/lotes_aprovados.html` (NOVO)

### Deploy:
- `railway_reset_database.sql` (NOVO)
- `executar_migracao_railway.py` (NOVO)

## 🚀 Deploy no Railway

### Opção 1: Migração Incremental (Preserva Dados)
```bash
python executar_migracao_railway.py --mode incremental
```

### Opção 2: Reset Completo (Apaga Tudo)
```bash
python executar_migracao_railway.py --mode full
```

**Ou execute o SQL diretamente no Railway:**
```bash
psql $DATABASE_URL < railway_reset_database.sql
```

## 🔑 Variáveis de Ambiente Necessárias

- `DATABASE_URL` - URL do PostgreSQL
- `GEMINI_API_KEY` - Chave da API do Google Gemini (obtida em https://aistudio.google.com/app/apikey)

## 📊 Fluxo Completo

```
1. SOLICITAÇÃO
   └─> Usuário acessa "Solicitar Compra"
   └─> Escolhe fornecedor e tipo
   └─> Tira foto do lote
   └─> IA sugere classificação
   └─> Usuário confirma ou edita
   └─> Informa peso
   └─> Sistema calcula valor
   └─> Status: "aguardando_aprovacao"

2. APROVAÇÃO
   └─> Admin acessa "Aprovar Solicitações"
   └─> Visualiza detalhes e foto
   └─> Aprova ou rejeita
   └─> Status: "aprovado" ou "rejeitado"

3. ENTRADA
   └─> Admin acessa "Lotes Aprovados"
   └─> Registra recebimento físico
   └─> Lote vai para "Entradas de Estoque"
   └─> Status: "recebido"
   └─> Atualiza balanço de compras
```

## ✅ Checklist de Implementação

- [x] Modelo de dados criado
- [x] Migration SQL executada
- [x] Rotas backend implementadas
- [x] Integração com Gemini IA
- [x] Telas frontend criadas
- [x] Sistema de upload de imagens
- [x] Cálculo automático de valores
- [x] Fluxo de aprovação/rejeição
- [x] Registro de entradas
- [x] Script de deploy para Railway
- [x] Documentação completa

## 🔧 Próximos Passos Sugeridos

1. Adicionar links no dashboard para as novas telas
2. Adicionar notificações quando solicitações são criadas/aprovadas
3. Criar relatórios de compras por classificação
4. Adicionar filtros avançados nas listagens
5. Implementar histórico de alterações nas classificações

## 📞 Suporte

Para dúvidas sobre o funcionamento do módulo, consulte este documento ou os comentários no código.
