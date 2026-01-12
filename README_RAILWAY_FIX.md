# ✅ CORREÇÃO PARA RAILWAY - DEPLOY RESOLVIDO

## Problema Original
```
Error: '$PORT' is not a valid port number.
```
Tabelas PostgreSQL não eram criadas automaticamente.

## ✅ Solução Implementada

### 1. Criado `entrypoint.sh`
Script bash que:
- Expande corretamente a variável `$PORT`
- Inicializa o banco de dados ANTES de iniciar o servidor
- Usa `exec` para substituir o processo corretamente
- Tem fallback para porta 8000 se PORT não estiver definido

### 2. Atualizado `Dockerfile`
- Usa `ENTRYPOINT` ao invés de `CMD`
- Copia e dá permissão ao `entrypoint.sh`
- Garante que o script sempre seja executado

### 3. Atualizado `railway.json`
- Define `startCommand` explicitamente: `/app/entrypoint.sh`
- Evita conflitos com comandos customizados

### 4. Corrigido `app/__init__.py`
- Converte automaticamente `postgres://` para `postgresql://`
- Compatível com Railway e outros hosts

## 🚀 Como Deploy no Railway

### Passo 1: Limpar Configuração Antiga
No Railway Dashboard:
1. Vá em **Settings** → **Deploy**
2. **REMOVA** qualquer Start Command customizado
3. Deixe o campo vazio
4. Salve

### Passo 2: Commit e Push
```bash
git add .
git commit -m "Fix Railway deployment PORT error and DB initialization"
git push
```

### Passo 3: Deploy Automático
- Railway detectará as mudanças
- Fará build com o Dockerfile
- Executará `entrypoint.sh` automaticamente

### Passo 4: Verificar Logs
Você deve ver no Railway:
```
🚀 Iniciando aplicação...
ℹ️  Usando PORT: 8080
✅ DATABASE_URL está configurado
📊 Inicializando banco de dados...
✅ Tabelas criadas/verificadas com sucesso!
✅ Usuário admin verificado!
🌐 Iniciando servidor Gunicorn na porta 8080...
[INFO] Listening at: http://0.0.0.0:8080
```

## 📋 Checklist

- ✅ `entrypoint.sh` criado e com permissão de execução
- ✅ `Dockerfile` atualizado para usar ENTRYPOINT
- ✅ `railway.json` com startCommand correto
- ✅ `app/__init__.py` converte postgres:// para postgresql://
- ✅ `.dockerignore` criado para otimizar build
- ⚠️  **TODO**: Remover Start Command customizado no Railway Dashboard

## 🔧 Variáveis de Ambiente Necessárias no Railway

```
DATABASE_URL=<automaticamente definido pelo Railway ao adicionar PostgreSQL>
SESSION_SECRET=<gere com: python -c "import secrets; print(secrets.token_hex(32))">
JWT_SECRET_KEY=<gere com: python -c "import secrets; print(secrets.token_hex(32))">
```

## 🎯 O que mudou?

### Antes (❌ Não Funcionava)
```dockerfile
# Dockerfile
CMD ["python", "start.py"]
```
- Railway executava: `gunicorn ... --bind 0.0.0.0:$PORT ...`
- Variável `$PORT` não era expandida
- Erro: "'$PORT' is not a valid port number"

### Depois (✅ Funciona)
```dockerfile
# Dockerfile
ENTRYPOINT ["/app/entrypoint.sh"]
```
```bash
# entrypoint.sh
#!/bin/bash
export PORT=${PORT:-8000}
python init_db.py  # Cria tabelas primeiro
exec gunicorn ... --bind "0.0.0.0:$PORT" ...  # PORT expandido corretamente
```

## 🧪 Testar Localmente com Docker

```bash
# Build
docker build -t mrx-app .

# Run (simulando Railway)
docker run -p 8080:8080 \
  -e PORT=8080 \
  -e DATABASE_URL="postgresql://user:pass@host:5432/db" \
  -e SESSION_SECRET="test-secret" \
  -e JWT_SECRET_KEY="test-jwt" \
  mrx-app
```

## 📞 Suporte

Se ainda houver problemas:
1. Verifique se o Start Command foi REMOVIDO no Railway
2. Confira os logs do Railway para mensagens de erro
3. Verifique se DATABASE_URL está definido
4. Teste localmente com Docker primeiro

---

**Data da Correção**: 07/11/2025  
**Status**: ✅ Pronto para Deploy
