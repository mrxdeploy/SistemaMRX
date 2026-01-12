
# 🧪 Guia de Testes - Sistema RBAC

## 📝 Preparação

### 1. Criar Usuários de Teste

```bash
python criar_usuarios_teste.py
```

Isso criará 7 usuários, um para cada perfil:

| Email | Senha | Perfil |
|-------|-------|--------|
| admin@teste.com | teste123 | Administrador |
| comprador@teste.com | teste123 | Comprador (PJ) |
| conferente@teste.com | teste123 | Conferente / Estoque |
| separacao@teste.com | teste123 | Separação |
| motorista@teste.com | teste123 | Motorista |
| financeiro@teste.com | teste123 | Financeiro |
| auditoria@teste.com | teste123 | Auditoria / BI |

### 2. Visualizar Matriz de Permissões

```bash
python testar_rbac.py
```

---

## 🎯 Casos de Teste por Perfil

### 1️⃣ ADMINISTRADOR (admin@teste.com)

**✅ DEVE TER ACESSO A:**
- ✓ Gerenciar usuários (criar, editar, excluir)
- ✓ Gerenciar perfis
- ✓ Gerenciar fornecedores
- ✓ Gerenciar veículos e motoristas
- ✓ Criar e aprovar solicitações
- ✓ Criar e aprovar lotes
- ✓ Processar entradas de estoque
- ✓ Visualizar auditoria
- ✓ Exportar relatórios
- ✓ Definir limites e autorizar descarte

**🧪 TESTES:**
1. Login em `/administracao.html`
2. Criar um novo funcionário
3. Criar um novo fornecedor
4. Aprovar uma solicitação
5. Processar entrada de estoque

---

### 2️⃣ COMPRADOR (comprador@teste.com)

**✅ DEVE TER ACESSO A:**
- ✓ Criar fornecedores
- ✓ Editar fornecedores
- ✓ Criar solicitações de compra
- ✓ Visualizar solicitações
- ✓ Informar entrega/coleta
- ✓ Registrar preço pago

**❌ NÃO DEVE TER ACESSO A:**
- ✗ Gerenciar usuários
- ✗ Aprovar solicitações
- ✗ Processar entradas de estoque
- ✗ Gerenciar veículos/motoristas

**🧪 TESTES:**
1. Login e acessar `/fornecedores.html`
2. Criar um novo fornecedor ✅
3. Acessar `/solicitacoes.html`
4. Criar uma nova solicitação ✅
5. Tentar acessar `/administracao.html` ❌ (deve ser bloqueado)

---

### 3️⃣ CONFERENTE / ESTOQUE (conferente@teste.com)

**✅ DEVE TER ACESSO A:**
- ✓ Validar chegada de materiais
- ✓ Pesar itens
- ✓ Conferir qualidade
- ✓ Criar lotes
- ✓ Dar entrada no estoque
- ✓ Visualizar lotes e entradas

**❌ NÃO DEVE TER ACESSO A:**
- ✗ Criar fornecedores
- ✗ Aprovar solicitações
- ✗ Gerenciar usuários

**🧪 TESTES:**
1. Login e acessar `/lotes.html`
2. Visualizar lotes existentes ✅
3. Acessar `/entradas.html`
4. Processar entrada de estoque ✅
5. Tentar criar fornecedor ❌ (deve ser bloqueado)

---

### 4️⃣ SEPARAÇÃO (separacao@teste.com)

**✅ DEVE TER ACESSO A:**
- ✓ Separar lotes por material/condição
- ✓ Criar sublotes
- ✓ Marcar resíduos
- ✓ Visualizar lotes
- ✓ Solicitar descarte (aprovação ADM necessária)

**❌ NÃO DEVE TER ACESSO A:**
- ✗ Aprovar descartes
- ✗ Processar entradas
- ✗ Criar solicitações

**🧪 TESTES:**
1. Login e acessar `/lotes.html`
2. Visualizar lotes ✅
3. Separar lote por classificação ✅
4. Solicitar descarte ✅
5. Tentar aprovar descarte ❌ (deve ser bloqueado)

---

### 5️⃣ MOTORISTA (motorista@teste.com)

**✅ DEVE TER ACESSO A:**
- ✓ Visualizar rotas atribuídas
- ✓ Registrar coletas
- ✓ Enviar comprovantes/fotos
- ✓ Visualizar dados pessoais

**❌ NÃO DEVE TER ACESSO A:**
- ✗ Criar solicitações
- ✗ Visualizar fornecedores
- ✗ Processar entradas

**🧪 TESTES:**
1. Login e verificar dashboard
2. Visualizar rotas ✅
3. Registrar coleta ✅
4. Tentar acessar fornecedores ❌ (deve ser bloqueado)

---

### 6️⃣ FINANCEIRO (financeiro@teste.com)

**✅ DEVE TER ACESSO A:**
- ✓ Emitir notas fiscais
- ✓ Controlar pagamentos
- ✓ Conciliação bancária
- ✓ Visualizar fornecedores
- ✓ Visualizar solicitações
- ✓ Exportar relatórios

**❌ NÃO DEVE TER ACESSO A:**
- ✗ Criar fornecedores
- ✗ Aprovar solicitações
- ✗ Processar entradas

**🧪 TESTES:**
1. Login e acessar relatórios
2. Exportar dados ✅
3. Visualizar fornecedores ✅
4. Tentar criar fornecedor ❌ (deve ser bloqueado)

---

### 7️⃣ AUDITORIA / BI (auditoria@teste.com)

**✅ DEVE TER ACESSO A (SOMENTE LEITURA):**
- ✓ Visualizar painéis e dashboards
- ✓ Visualizar trilhas de auditoria
- ✓ Visualizar relatórios
- ✓ Exportar dados
- ✓ Visualizar todos os cadastros

**❌ NÃO DEVE PODER EDITAR NADA:**
- ✗ Criar/editar usuários
- ✗ Criar/editar fornecedores
- ✗ Aprovar solicitações
- ✗ Processar entradas
- ✗ Qualquer operação POST/PUT/DELETE

**🧪 TESTES:**
1. Login e acessar `/dashboard.html` ✅
2. Visualizar auditoria ✅
3. Exportar relatórios ✅
4. Tentar criar usuário ❌ (deve ser bloqueado)
5. Tentar editar fornecedor ❌ (deve ser bloqueado)
6. Verificar que todos os botões de ação estão ocultos

---

## 🔍 Testes de Segurança

### Teste 1: Escalação de Privilégios
```python
# Tentar acessar endpoint admin sem ser admin
# Login como comprador@teste.com
# Tentar POST /api/usuarios (deve retornar 403)
```

### Teste 2: Bypass de Permissões
```python
# Login como auditoria@teste.com
# Tentar PUT /api/fornecedores/1 (deve retornar 403)
# Tentar DELETE /api/usuarios/5 (deve retornar 403)
```

### Teste 3: Logs de Auditoria
```python
# Fazer login com diferentes perfis
# Verificar se ações estão sendo registradas em auditoria_logs
```

---

## ✅ Checklist de Validação

- [ ] Todos os 7 usuários de teste foram criados
- [ ] Cada perfil consegue fazer login
- [ ] Administrador tem acesso total
- [ ] Comprador consegue criar fornecedores e solicitações
- [ ] Conferente consegue processar entradas
- [ ] Separação consegue gerenciar lotes
- [ ] Motorista vê apenas suas rotas
- [ ] Financeiro visualiza mas não edita
- [ ] Auditoria tem SOMENTE leitura (todos os POST/PUT/DELETE bloqueados)
- [ ] Logs de auditoria estão sendo registrados
- [ ] Mensagens de erro são claras quando acesso é negado

---

## 📊 Logs de Auditoria

Para verificar os logs:

```sql
SELECT 
    u.nome as usuario,
    al.acao,
    al.entidade_tipo,
    al.data_acao,
    al.detalhes
FROM auditoria_logs al
LEFT JOIN usuarios u ON u.id = al.usuario_id
ORDER BY al.data_acao DESC
LIMIT 50;
```

---

## 🐛 Reportar Problemas

Se encontrar algum problema durante os testes:

1. Anote o perfil do usuário
2. Anote a ação que estava tentando realizar
3. Copie a mensagem de erro
4. Verifique os logs do servidor
5. Reporte com todos esses detalhes
