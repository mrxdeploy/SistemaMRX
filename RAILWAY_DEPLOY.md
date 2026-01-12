# Deploy no Railway - MRX Systems

## Pré-requisitos

1. Conta no Railway (https://railway.app/)
2. Banco de dados PostgreSQL configurado no Railway

## Passos para Deploy

### 1. Criar Novo Projeto no Railway

1. Acesse https://railway.app/
2. Clique em "New Project"
3. Selecione "Deploy from GitHub repo" ou "Empty Project"

### 2. Adicionar PostgreSQL

1. No seu projeto, clique em "+ New"
2. Selecione "Database" → "Add PostgreSQL"
3. O Railway criará automaticamente a variável `DATABASE_URL`

### 3. Configurar Variáveis de Ambiente

No Railway, adicione as seguintes variáveis de ambiente:

```
DATABASE_URL=postgresql://... (gerado automaticamente pelo Railway)
SESSION_SECRET=seu-secret-key-aqui
JWT_SECRET_KEY=seu-jwt-secret-aqui
PORT=8080
ADMIN_EMAIL=admin@sistema.com (opcional)
ADMIN_PASSWORD=sua-senha-segura (opcional)
```

### 4. Deploy da Aplicação

#### Opção A: Via GitHub

1. Conecte seu repositório GitHub ao Railway
2. O Railway detectará automaticamente o `railway.json` e `Procfile`
3. O deploy será iniciado automaticamente

#### Opção B: Via Railway CLI

```bash
# Instalar Railway CLI
npm i -g @railway/cli

# Login
railway login

# Link ao projeto
railway link

# Deploy
railway up
```

### 5. Inicializar Banco de Dados

Após o primeiro deploy, execute o script de inicialização:

```bash
railway run python init_db.py
```

Ou conecte via SSH e execute:

```bash
python init_db.py
```

### 6. Verificar Deploy

1. Acesse a URL fornecida pelo Railway
2. Faça login com as credenciais de admin
3. Verifique se todas as funcionalidades estão operacionais

## Estrutura de Arquivos para Deploy

- `Procfile`: Define o comando de inicialização
- `railway.json`: Configurações específicas do Railway
- `requirements.txt`: Dependências Python
- `runtime.txt`: Versão do Python
- `init_db.py`: Script para criar tabelas no banco
- `nixpacks.toml`: Configuração do builder (opcional)

## Troubleshooting

### Erro: "Failed to find attribute 'app'"
✅ **Resolvido**: O arquivo `app.py` agora exporta `application` corretamente

### Tabelas não criadas
Execute: `railway run python init_db.py`

### Erro de conexão com banco
Verifique se a variável `DATABASE_URL` está configurada corretamente

### Timeout no deploy
Aumentado timeout no Procfile para 120 segundos

## Comandos Úteis

```bash
# Ver logs em tempo real
railway logs

# Conectar ao shell
railway shell

# Executar comando no ambiente
railway run <comando>

# Ver variáveis de ambiente
railway variables
```

## Suporte

Para mais informações, consulte a documentação do Railway:
https://docs.railway.app/
