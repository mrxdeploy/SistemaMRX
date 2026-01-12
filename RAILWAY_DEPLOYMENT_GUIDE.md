# Guia de Deploy no Railway - ATUALIZADO

## ✅ Correções Implementadas

1. **Problema do $PORT resolvido**: Criado `entrypoint.sh` que expande corretamente a variável PORT
2. **Criação automática de tabelas**: Script inicializa o banco antes de iniciar o servidor
3. **Suporte a postgres:// e postgresql://**: Conversão automática no código

## Arquivos de Configuração

Este projeto usa **Docker** para deployment no Railway:
- `Dockerfile` - Build da imagem Docker
- `entrypoint.sh` - **NOVO**: Script que resolve PORT e inicializa DB
- `railway.json` - Configuração do Railway com startCommand
- `init_db.py` - Script de criação de tabelas do banco

## Passo a Passo para Deploy

### 1. Conectar o Repositório ao Railway
- Acesse [railway.app](https://railway.app)
- Crie um novo projeto
- Conecte seu repositório GitHub

### 2. Adicionar PostgreSQL
- No dashboard do Railway, clique em "New" > "Database" > "PostgreSQL"
- Railway criará automaticamente a variável `DATABASE_URL`

### 3. Configurar Variáveis de Ambiente
Adicione estas variáveis no Railway (aba "Variables"):

```
SESSION_SECRET=sua-chave-secreta-aleatoria-aqui
JWT_SECRET_KEY=sua-chave-jwt-aleatoria-aqui
```

**IMPORTANTE**: Gere chaves fortes e únicas! Use este comando para gerar:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### 4. Remover Start Command Customizado (IMPORTANTE!)
**No Railway Dashboard**:
1. Vá em **Settings** → **Deploy**
2. Se houver um **Start Command** customizado, **DELETE/REMOVA** ele
3. Deixe vazio - o `railway.json` já define o comando correto
4. Salve as alterações

### 5. Deploy Automático
- Railway detectará o `Dockerfile` automaticamente
- Usará o `entrypoint.sh` que resolve todos os problemas
- Railway definirá a variável `PORT` automaticamente

### 6. Verificar o Deploy
Após o deploy, verifique os logs. Você deve ver:
```
🚀 Iniciando aplicação...
ℹ️  Usando PORT: 8080
✅ DATABASE_URL está configurado
📊 Inicializando banco de dados...
✅ Tabelas criadas/verificadas com sucesso!
✅ Usuário admin verificado!
🌐 Iniciando servidor Gunicorn na porta 8080...
```

## Estrutura de Inicialização (ATUALIZADA)

1. `Dockerfile` define `ENTRYPOINT` como `entrypoint.sh`
2. `entrypoint.sh` expande a variável `$PORT` corretamente (resolve o erro)
3. `entrypoint.sh` executa `init_db.py` para criar tabelas
4. `entrypoint.sh` inicia o Gunicorn com eventlet worker
5. A aplicação fica disponível na porta definida por Railway

## Solução de Problemas

### ✅ Erro: "$PORT is not a valid port number" - RESOLVIDO
**Solução implementada:**
- Criado `entrypoint.sh` que usa bash para expandir `$PORT` corretamente
- Dockerfile usa `ENTRYPOINT` que sempre funciona
- `railway.json` define `startCommand` explicitamente
- **Ação necessária**: Remova qualquer Start Command customizado no Railway Dashboard

### ✅ Tabelas não sendo criadas - RESOLVIDO
**Solução implementada:**
- DATABASE_URL converte `postgres://` para `postgresql://` automaticamente
- `entrypoint.sh` executa `init_db.py` ANTES de iniciar o servidor
- `db.create_all()` também é chamado no `app/__init__.py` como backup
- Logs mostram confirmação da criação das tabelas

### Database Connection Issues
- Verifique se a variável `DATABASE_URL` está configurada no Railway
- Verifique se o serviço PostgreSQL está ativo

## Comandos Úteis

### Criar tabelas manualmente (se necessário)
```bash
python init_db.py
```

### Recriar todas as tabelas (CUIDADO: apaga dados)
```bash
python init_db.py --drop
```

### Testar localmente com Docker
```bash
docker build -t app .
docker run -p 5000:5000 -e PORT=5000 -e DATABASE_URL=sua_url app
```

## Arquivos Importantes

- `Dockerfile` - Build da imagem Docker
- `railway.json` - Configuração do Railway
- `start.py` - Script de inicialização
- `init_db.py` - Script de criação de tabelas
- `app/__init__.py` - Configuração da aplicação Flask
- `requirements.txt` - Dependências Python
