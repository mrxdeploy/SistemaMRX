# 🚀 Migração do Sistema de Solicitações - Guia Completo

## 📦 O Que Foi Criado

### 1. Script de Migração Python
**Arquivo**: `migrations/migrar_sistema_solicitacoes.py`

Este script adiciona automaticamente todas as tabelas e colunas necessárias para o novo sistema:

#### Tabelas Criadas:
- ✅ `materiais_base` - Catálogo de materiais eletrônicos
- ✅ `tabelas_preco` - Tabelas 1★, 2★, 3★
- ✅ `tabelas_preco_itens` - Preços de materiais por tabela
- ✅ `ordens_compra` - OCs geradas automaticamente
- ✅ `auditoria_oc` - Auditoria completa de OCs

#### Colunas Adicionadas em Tabelas Existentes:

**`solicitacoes`**:
- `tipo_retirada` (VARCHAR) - buscar/entregar
- `modalidade_frete` (VARCHAR) - FOB/CIF
- `rua` (VARCHAR)
- `numero` (VARCHAR)
- `cep` (VARCHAR)
- `localizacao_lat` (FLOAT)
- `localizacao_lng` (FLOAT)
- `endereco_completo` (VARCHAR)

**`itens_solicitacao`**:
- `material_id` (INTEGER FK) - Link com materiais base
- `preco_customizado` (BOOLEAN) - Flag de preço diferente
- `preco_oferecido` (FLOAT) - Preço negociado
- `preco_por_kg_snapshot` (FLOAT)
- `estrelas_snapshot` (INTEGER)

**`fornecedores`**:
- `tabela_preco_id` (INTEGER FK) - Vínculo com tabela de preços

## 🎯 Como Usar

### Opção 1: Script Bash (Recomendado)

```bash
chmod +x migrations/executar_migracao.sh
./migrations/executar_migracao.sh
```

### Opção 2: Python Direto

```bash
python migrations/migrar_sistema_solicitacoes.py
```

## ✅ Sistema Atual (Desenvolvimento)

No ambiente de desenvolvimento (Replit), as mudanças **JÁ ESTÃO APLICADAS** e funcionando:

### ✨ Funcionalidades Ativas:

1. **Aprovação Automática de Solicitações** ✅
   - Quando preço ≤ tabela → Aprovação automática
   - Quando preço > tabela → Aguarda aprovação do admin
   - OC e lotes criados automaticamente

2. **Sistema de Materiais e Preços** ✅
   - Materiais base cadastrados
   - Tabelas de preço 1★, 2★, 3★
   - Preços por material configuráveis

3. **Preço Customizado por Item** ✅
   - Campo "Preço Diferente" no wizard
   - Comparação automática com tabela
   - Snapshot de preços para auditoria

## 🔄 Para Ambiente de Produção

### Pré-Requisitos:
1. Acesso ao banco PostgreSQL de produção
2. Variável `DATABASE_URL` configurada
3. Python 3.x instalado

### Passos:

**1. Configure a DATABASE_URL**:
```bash
export DATABASE_URL="postgresql://user:password@host:port/database"
```

**2. Execute a Migração**:
```bash
python migrations/migrar_sistema_solicitacoes.py
```

**3. Verifique os Logs**:
O script mostra cada etapa em tempo real e confirma o sucesso.

**4. Inicialize os Dados**:
```bash
python seed_modulo_comprador.py
```

Isso cria:
- 3 tabelas de preço (1★, 2★, 3★)
- Materiais base iniciais
- Preços configurados

## 📊 Estrutura de Dados

### Fluxo de Aprovação:

```
┌─────────────────────────────────────┐
│ Usuário cria solicitação            │
│ - Seleciona fornecedor (tem tabela) │
│ - Adiciona materiais                │
│ - Define preços (tabela ou custom)  │
└───────────────┬─────────────────────┘
                │
                ▼
        ┌───────────────┐
        │ Validação     │
        │ de Preços     │
        └───────┬───────┘
                │
       ┌────────┴────────┐
       │                 │
       ▼                 ▼
┌──────────────┐  ┌──────────────┐
│ Preço ≤      │  │ Preço >      │
│ Tabela       │  │ Tabela       │
└──────┬───────┘  └──────┬───────┘
       │                 │
       ▼                 ▼
┌──────────────┐  ┌──────────────┐
│ APROVADA     │  │ PENDENTE     │
│ Automática   │  │ (Aguarda     │
│              │  │  Admin)      │
│ ✓ Cria OC    │  │              │
│ ✓ Cria Lotes │  │              │
└──────────────┘  └──────────────┘
                         │
                         ▼
                  ┌──────────────┐
                  │ Admin Aprova │
                  │              │
                  │ ✓ Cria OC    │
                  │ ✓ Cria Lotes │
                  └──────────────┘
```

## 🧪 Testar Após Migração

1. **Criar Fornecedor**:
   - Vincular a uma tabela de preço (1★, 2★ ou 3★)

2. **Criar Solicitação**:
   - Selecionar fornecedor
   - Adicionar material
   - Usar preço da tabela → Deve aprovar automaticamente
   - Usar preço maior → Deve ficar pendente

3. **Verificar OCs**:
   - Acessar "Ordens de Compra"
   - Confirmar que OCs foram criadas automaticamente

4. **Verificar Lotes**:
   - Acessar "WMS / Lotes"
   - Confirmar que lotes foram criados

## 🐛 Troubleshooting

### Erro: "DATABASE_URL não encontrada"
**Solução**: Configure a variável de ambiente
```bash
export DATABASE_URL="sua-string-de-conexao"
```

### Erro: "Permission denied"
**Solução**: Verifique permissões do usuário no banco

### Erro: "Tabela já existe"
**Solução**: Normal! O script é idempotente (pode rodar múltiplas vezes)

### OCs não aparecem após migração
**Solução**: 
1. Rode a migração
2. Rode o seed: `python seed_modulo_comprador.py`
3. Crie uma nova solicitação (as antigas não terão OCs)

## 📝 Logs Importantes

O script mostra:
```
==============================================================
 INICIANDO MIGRAÇÃO DO SISTEMA DE SOLICITAÇÕES
==============================================================

📦 Etapa 1: Criando tabela materiais_base...
   ✓ Tabela materiais_base criada/verificada

💰 Etapa 2: Criando tabela tabelas_preco...
   ✓ Tabela tabelas_preco criada/verificada

... (continua)

==============================================================
 ✅ MIGRAÇÃO CONCLUÍDA COM SUCESSO!
==============================================================
```

## 🎉 Resultado Final

Após a migração, seu sistema terá:

✅ Sistema completo de materiais e preços  
✅ Aprovação automática baseada em estrelas  
✅ Geração automática de OCs e lotes  
✅ Auditoria completa de todas as operações  
✅ Compatibilidade total com versão anterior  

---

**Data**: 24/11/2025  
**Versão**: 2.0.0  
**Status**: ✅ Pronto para Produção
