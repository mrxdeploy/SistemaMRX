# Guia de Deploy no Railway

## ✅ Configurações já realizadas

1. **Procfile** - Configurado para usar Gunicorn com EventLet
2. **requirements.txt** - Limpado e com todas as dependências
3. **runtime.txt** - Atualizado para Python 3.12
4. **nixpacks.toml** - Criado para configuração de build do Railway
5. **Criação automática de tabelas** - Já configurado em `app/__init__.py` (linha 42)

## 🚀 Passos para fazer o Deploy

### 1. Preparar o Repositório

Se ainda não fez, faça commit e push do código para o GitHub:

```bash
git add .
git commit -m "Configuração para deploy no Railway"
git push origin main
```

### 2. Criar Projeto no Railway

1. Acesse [railway.app](https://railway.app)
2. Faça login com GitHub
3. Clique em **"New Project"**
4. Selecione **"Deploy from GitHub repo"**
5. Escolha seu repositório

### 3. Adicionar Banco de Dados PostgreSQL

1. No projeto do Railway, clique em **"+ New"**
2. Selecione **"Database"** → **"Add PostgreSQL"**
3. Aguarde a criação do banco

### 4. Configurar Variáveis de Ambiente

1. Clique no seu serviço **web** (não no PostgreSQL)
2. Vá para a aba **"Variables"**
3. Clique em **"+ New Variable"** → **"Add Reference"**
4. Adicione a variável **DATABASE_URL** do PostgreSQL
5. Adicione também estas variáveis personalizadas:
   - `SESSION_SECRET` = (gere uma chave aleatória forte)
   - `JWT_SECRET_KEY` = (gere outra chave aleatória forte)
   - `ADMIN_EMAIL` = seu-email@exemplo.com (opcional)
   - `ADMIN_PASSWORD` = sua-senha-segura (opcional)

**Para gerar chaves secretas:**
```python
import secrets
print(secrets.token_hex(32))
```

### 5. Deploy Automático

O Railway irá automaticamente:
- ✅ Detectar Python
- ✅ Instalar dependências do `requirements.txt`
- ✅ Executar o comando do `Procfile` ou `nixpacks.toml`
- ✅ Criar as tabelas do banco de dados (via `db.create_all()`)
- ✅ Criar o usuário admin padrão

### 6. Gerar Domínio Público

1. Clique no serviço **web**
2. Vá para **Settings** → **Networking**
3. Clique em **"Generate Domain"**
4. Você receberá uma URL: `seu-app.up.railway.app`

## 🔧 Variáveis de Ambiente Importantes

| Variável | Descrição | Obrigatória |
|----------|-----------|-------------|
| `DATABASE_URL` | URL do PostgreSQL (auto-configurada) | ✅ Sim |
| `SESSION_SECRET` | Chave secreta para sessões | ✅ Sim |
| `JWT_SECRET_KEY` | Chave para tokens JWT | ✅ Sim |
| `ADMIN_EMAIL` | Email do admin (padrão: admin@sistema.com) | ⚠️ Recomendado |
| `ADMIN_PASSWORD` | Senha do admin (padrão: admin123) | ⚠️ Recomendado |
| `PORT` | Porta do servidor (auto-configurada pelo Railway) | ✅ Auto |

## 🗄️ Criação Automática de Tabelas

As tabelas serão criadas automaticamente quando o app iniciar, graças ao código em `app/__init__.py`:

```python
with app.app_context():
    db.create_all()  # Cria todas as tabelas definidas nos models
    criar_admin_padrao()  # Cria usuário admin
```

## ⚠️ Resolução de Problemas

### Erro: "misc ERROR no precompiled python"
**Solução:** Arquivos `runtime.txt` e `nixpacks.toml` já foram atualizados para resolver isso.

### Tabelas não são criadas
**Solução:** Verifique se a variável `DATABASE_URL` está corretamente configurada nas variáveis de ambiente do serviço web.

### Erro de conexão com banco
**Solução:** Certifique-se de que adicionou a referência da variável `DATABASE_URL` do PostgreSQL para o serviço web (não apenas criar a variável manualmente).

### App não inicia
**Solução:** Verifique os logs no Railway:
1. Clique no serviço web
2. Vá para a aba **"Deployments"**
3. Clique no deployment com erro
4. Veja os logs detalhados

## 📊 Monitoramento

Após o deploy:
- Acesse a URL gerada
- Login padrão: `admin@sistema.com` / `admin123` (se não configurou variáveis)
- Verifique que o WebSocket está funcionando
- Teste o cadastro de empresas e preços

## 💰 Custos

- Railway oferece **$5 em créditos gratuitos/mês**
- Uso além disso é cobrado por uso (pay-as-you-go)
- Estimativa: App pequeno/médio custa ~$5-10/mês

## 🔄 Próximos Passos

1. Configure um domínio customizado (opcional)
2. Altere as credenciais padrão do admin
3. Configure backups automáticos do PostgreSQL
4. Monitore uso de recursos no dashboard do Railway
