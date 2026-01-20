#!/bin/bash
set -e

echo "=========================================="
echo "🚀 Iniciando aplicação Railway MRX"
echo "=========================================="

# Define PORT com fallback para 8000
export PORT=${PORT:-8000}
echo "ℹ️  PORT configurado: $PORT"

# Verifica variáveis de ambiente críticas
echo ""
echo "📋 Verificando variáveis de ambiente..."
if [ -z "$DATABASE_URL" ]; then
    echo "❌ ERRO CRÍTICO: DATABASE_URL não está definido!"
    echo "   Configure o PostgreSQL no Railway e adicione a variável DATABASE_URL"
    exit 1
else
    echo "✅ DATABASE_URL está configurado"
    # Mostra apenas o início da URL por segurança
    echo "   URL: ${DATABASE_URL:0:20}..."
fi

if [ -z "$SESSION_SECRET" ]; then
    echo "⚠️  AVISO: SESSION_SECRET não definido (usando valor padrão)"
else
    echo "✅ SESSION_SECRET configurado"
fi

if [ -z "$JWT_SECRET_KEY" ]; then
    echo "⚠️  AVISO: JWT_SECRET_KEY não definido (usando valor padrão)"
else
    echo "✅ JWT_SECRET_KEY configurado"
fi

# Testa conexão Python
echo ""
echo "🐍 Testando importação da aplicação..."
python -c "from app import create_app; print('✅ App importado com sucesso')" || {
    echo "❌ ERRO: Falha ao importar aplicação"
    exit 1
}

# Executa migrações de produção (adiciona colunas faltantes)
echo ""
echo "🔄 Executando migrações de produção..."
python migrate_production.py || echo "⚠️  Aviso: Falha ao executar migrate_production.py, continuando inicialização..."

# Inicializa o banco de dados
echo ""
echo "📊 Inicializando banco de dados..."
python init_db.py || {
    echo "❌ ERRO: Falha ao inicializar banco de dados"
    echo "   Verifique se o PostgreSQL está ativo no Railway e se a URL está correta"
    # Não vamos dar exit 1 aqui para tentar iniciar o servidor mesmo assim se o banco já estiver pronto
    echo "   Tentando continuar mesmo com erro no init_db..."
}

# Inicia o servidor Gunicorn
echo ""
echo "=========================================="
echo "🌐 Iniciando servidor Gunicorn"
echo "   - Worker: eventlet"
echo "   - Workers: 1"
echo "   - Bind: 0.0.0.0:$PORT"
echo "   - Timeout: 300s"
echo "   - WSGI: wsgi:application"
echo "=========================================="
# Adicionando --preload para detectar erros de importação na inicialização
# Aumentando timeout para 300s para evitar 502 no deploy inicial
exec gunicorn --worker-class eventlet -w 1 --bind "0.0.0.0:$PORT" --timeout 300 --log-level debug --preload wsgi:application
