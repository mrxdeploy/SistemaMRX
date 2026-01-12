#!/bin/bash

echo "╔══════════════════════════════════════════════════════════╗"
echo "║  MIGRAÇÃO DO SISTEMA DE SOLICITAÇÕES                     ║"
echo "║  MRX System - Versão 2.0                                 ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# Verificar se DATABASE_URL está configurada
if [ -z "$DATABASE_URL" ]; then
    echo "❌ ERRO: Variável DATABASE_URL não está configurada!"
    echo ""
    echo "Configure assim:"
    echo "export DATABASE_URL='sua-string-de-conexao-postgres'"
    exit 1
fi

echo "✓ DATABASE_URL encontrada"
echo ""
echo "Iniciando migração..."
echo ""

# Executar script Python
python migrations/migrar_sistema_solicitacoes.py

# Verificar resultado
if [ $? -eq 0 ]; then
    echo ""
    echo "╔══════════════════════════════════════════════════════════╗"
    echo "║  ✅ MIGRAÇÃO CONCLUÍDA COM SUCESSO!                      ║"
    echo "╚══════════════════════════════════════════════════════════╝"
    echo ""
    echo "Próximos passos:"
    echo "1. Acessar o sistema e criar as tabelas de preço (1★, 2★, 3★)"
    echo "2. Adicionar materiais base"
    echo "3. Configurar preços para cada material"
    echo "4. Vincular fornecedores às tabelas"
    echo "5. Testar criação de solicitações"
    echo ""
else
    echo ""
    echo "╔══════════════════════════════════════════════════════════╗"
    echo "║  ❌ ERRO NA MIGRAÇÃO                                     ║"
    echo "╚══════════════════════════════════════════════════════════╝"
    echo ""
    echo "Verifique os logs acima para mais detalhes."
    echo ""
    exit 1
fi
