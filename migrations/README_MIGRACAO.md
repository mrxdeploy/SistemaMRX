# 📝 Migração do Sistema de Solicitações

## O que esta migração faz?

Esta migração adiciona **todas as tabelas e colunas** necessárias para o novo sistema de solicitações reformulado, incluindo:

### ✨ Novos Recursos

1. **Sistema de Materiais e Tabelas de Preço**
   - Tabela `materiais_base` - Catálogo de materiais eletrônicos
   - Tabela `tabelas_preco` - Tabelas 1★, 2★, 3★
   - Tabela `tabelas_preco_itens` - Preços por material em cada tabela

2. **Solicitações Reformuladas**
   - Campos de endereço (rua, número, CEP, latitude, longitude)
   - Tipo de retirada (buscar/entregar)
   - Modalidade de frete (FOB/CIF)

3. **Itens com Preço Customizado**
   - Campo `material_id` - Link com materiais base
   - Campo `preco_customizado` - Flag de preço diferente
   - Campo `preco_oferecido` - Preço negociado pelo fornecedor
   - Aprovação automática quando preço ≤ tabela

4. **Ordens de Compra (OC)**
   - Tabela `ordens_compra` - OCs geradas automaticamente
   - Tabela `auditoria_oc` - Auditoria completa de OCs
   - Criação automática quando solicitação é aprovada

## 🚀 Como Executar

### No Ambiente de Produção (Replit Deployment)

1. **Configure a variável DATABASE_URL** com a string de conexão do banco de produção

2. **Execute o script**:
```bash
python migrations/migrar_sistema_solicitacoes.py
```

3. **Verifique os logs** - O script mostra cada etapa e confirma sucesso/erro

### 📋 Checklist Pós-Migração

Após rodar a migração, você precisa:

- [ ] Criar as 3 tabelas de preço (1★, 2★, 3★)
- [ ] Adicionar materiais base ao sistema
- [ ] Configurar preços para cada material em cada tabela
- [ ] Vincular fornecedores às tabelas de preço
- [ ] Testar criação de solicitações com preço customizado
- [ ] Verificar aprovação automática funcionando

## ⚠️ Importante

- Esta migração é **idempotente** - pode ser executada múltiplas vezes sem problemas
- Usa `IF NOT EXISTS` para não quebrar se tabelas já existem
- **NÃO remove dados existentes** - apenas adiciona novas estruturas
- Funciona com PostgreSQL (Neon)

## 🔍 Tabelas Afetadas

| Tabela | Mudanças |
|--------|----------|
| `materiais_base` | **Nova tabela** - Catálogo de materiais |
| `tabelas_preco` | **Nova tabela** - Tabelas 1★, 2★, 3★ |
| `tabelas_preco_itens` | **Nova tabela** - Preços por material |
| `solicitacoes` | **Adiciona**: tipo_retirada, modalidade_frete, rua, numero, cep, lat, lng, endereco |
| `itens_solicitacao` | **Adiciona**: material_id, preco_customizado, preco_oferecido |
| `fornecedores` | **Adiciona**: tabela_preco_id |
| `ordens_compra` | **Nova tabela** - OCs automáticas |
| `auditoria_oc` | **Nova tabela** - Auditoria de OCs |

## 📞 Suporte

Em caso de erros:
1. Verifique os logs do script
2. Confirme que DATABASE_URL está correta
3. Verifique permissões do usuário do banco
4. Envie a mensagem de erro completa

---

**Data de criação**: 24/11/2025  
**Versão**: 1.0.0  
**Status**: Pronto para produção
