# Guia de Deploy no Railway - ATUALIZADO

Este guia explica como fazer deploy da aplicação no Railway com PostgreSQL.

## 🚀 Passo a Passo

### 1. Criar Projeto no Railway

1. Acesse [railway.app](https://railway.app)
2. Clique em "New Project"
3. Selecione "Deploy from GitHub repo"
4. Escolha o repositório do seu projeto

### 2. Adicionar PostgreSQL

1. No seu projeto Railway, clique em "+ New"
2. Selecione "Database"
3. Escolha "PostgreSQL"
4. O Railway vai criar automaticamente a variável `DATABASE_URL`

### 3. Configurar Variáveis de Ambiente

No painel do Railway, adicione as seguintes variáveis:

```bash
# Obrigatórias
DATABASE_URL=<gerado_automaticamente_pelo_railway>
SECRET_KEY=<sua_chave_secreta_aqui>
JWT_SECRET_KEY=<sua_chave_jwt_aqui>

# Opcionais
DROP_TABLES=false  # Mude para 'true' apenas se quiser recriar todas as tabelas
```

**Importante:** 
- ⚠️ NÃO defina a variável `PORT` manualmente - o Railway define automaticamente
- Use chaves secretas fortes e únicas
- O script `start.py` gerencia a porta automaticamente

### 4. Deploy Automático

O Railway vai:
1. ✅ Detectar o `Dockerfile` automaticamente
2. ✅ Fazer build da aplicação
3. ✅ Executar `start.py` (Python) que:
   - Inicializa o banco de dados automaticamente (cria tabelas se não existirem)
   - Cria o usuário admin padrão
   - Detecta e configura a porta $PORT corretamente
   - Inicia o servidor Gunicorn na porta correta

### 5. Verificar Deploy

Após o deploy:
1. Verifique os logs no Railway
2. Procure por mensagens como:
   - "✅ Tabelas criadas/verificadas com sucesso!"
   - "✅ Usuário admin verificado!"
   - "🌐 Iniciando servidor..."

### 6. Acessar a Aplicação

1. No Railway, clique em "Settings"
2. Em "Networking", clique em "Generate Domain"
3. Sua aplicação estará disponível na URL gerada

## 🔧 Solução de Problemas

### Erro: "$PORT is not a valid port number"

✅ **RESOLVIDO** - Agora usamos `start.py` (Python) em vez de shell script para máxima compatibilidade:
- `start.py` detecta e gerencia a variável PORT automaticamente
- Funciona em qualquer ambiente Docker/Railway
- Cria tabelas do banco automaticamente antes de iniciar

### Tabelas não foram criadas

Execute manualmente no Railway CLI:
```bash
railway run python init_db.py
```

### Recriar tabelas do zero

Defina a variável de ambiente:
```bash
DROP_TABLES=true
```

Ou execute localmente:
```bash
python init_db.py --drop
```

⚠️ **ATENÇÃO:** Isso apagará TODOS os dados!

## 📁 Arquivos de Deploy

- `Dockerfile`: Configuração do container
- `start.sh`: Script de inicialização (cria DB + inicia servidor)
- `init_db.py`: Script para criar/verificar tabelas
- `Procfile`: Para Heroku/Railway (usa start.sh)
- `railway.json`: Configuração específica do Railway

## 🔐 Segurança

1. Nunca commite arquivos `.env` no Git
2. Use variáveis de ambiente fortes e únicas
3. O PostgreSQL do Railway já está protegido
4. Revise as permissões de CORS em produção

## 📊 Monitoramento

No Railway, você pode:
- Ver logs em tempo real
- Monitorar uso de recursos
- Configurar domínio customizado
- Escalar verticalmente conforme necessário

## 🆘 Suporte

Se encontrar problemas:
1. Verifique os logs no Railway
2. Confirme que todas as variáveis de ambiente estão configuradas
3. Teste localmente primeiro com `docker build` e `docker run`
