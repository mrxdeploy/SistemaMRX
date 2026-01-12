#!/usr/bin/env python3
"""
Script para executar migração do banco de dados no Railway
Recria todas as tabelas com as novas funcionalidades
"""
import os
import sys
import psycopg2
from psycopg2 import sql

def executar_migracao():
    """Executa a migração completa do banco de dados"""
    
    database_url = os.getenv('DATABASE_URL')
    
    if not database_url:
        print("❌ Erro: DATABASE_URL não configurada")
        sys.exit(1)
    
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    
    print("🔄 Iniciando migração do banco de dados...")
    print(f"📊 Conectando ao banco de dados...")
    
    try:
        conn = psycopg2.connect(database_url)
        conn.autocommit = False
        cursor = conn.cursor()
        
        print("✅ Conectado com sucesso!")
        print("⚠️  ATENÇÃO: Este script irá APAGAR todos os dados existentes!")
        
        resposta = input("Digite 'SIM' para confirmar a execução: ")
        
        if resposta.upper() != 'SIM':
            print("❌ Migração cancelada pelo usuário")
            sys.exit(0)
        
        print("\n📝 Lendo script SQL...")
        with open('railway_reset_database.sql', 'r', encoding='utf-8') as f:
            sql_script = f.read()
        
        print("🗑️  Removendo tabelas antigas...")
        cursor.execute(sql_script)
        
        conn.commit()
        print("✅ Migração concluída com sucesso!")
        
        print("\n📊 Estatísticas do banco:")
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE'
            ORDER BY table_name;
        """)
        
        tabelas = cursor.fetchall()
        print(f"   Total de tabelas: {len(tabelas)}")
        for tabela in tabelas:
            print(f"   - {tabela[0]}")
        
        cursor.close()
        conn.close()
        
        print("\n✅ Banco de dados pronto para uso!")
        print("⚠️  Não esqueça de configurar o usuário administrador inicial")
        
    except Exception as e:
        print(f"\n❌ Erro durante a migração: {str(e)}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        sys.exit(1)

def executar_migracao_incremental():
    """Executa apenas a migração 004 sem apagar dados existentes"""
    
    database_url = os.getenv('DATABASE_URL')
    
    if not database_url:
        print("❌ Erro: DATABASE_URL não configurada")
        sys.exit(1)
    
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    
    print("🔄 Iniciando migração incremental...")
    
    try:
        conn = psycopg2.connect(database_url)
        conn.autocommit = False
        cursor = conn.cursor()
        
        print("✅ Conectado com sucesso!")
        print("📝 Aplicando migração 004...")
        
        with open('migrations/004_add_classificacao_lotes.sql', 'r', encoding='utf-8') as f:
            sql_script = f.read()
        
        cursor.execute(sql_script)
        conn.commit()
        
        print("✅ Migração incremental concluída com sucesso!")
        print("   - Tabela fornecedor_tipo_lote_classificacao criada")
        print("   - Campos de classificação adicionados")
        print("   - Configuração valor_base_por_estrela adicionada")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"\n❌ Erro durante a migração: {str(e)}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        sys.exit(1)

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Executar migração do banco de dados')
    parser.add_argument('--mode', choices=['full', 'incremental'], default='incremental',
                       help='Modo de migração: full (apaga tudo) ou incremental (preserva dados)')
    
    args = parser.parse_args()
    
    if args.mode == 'full':
        executar_migracao()
    else:
        executar_migracao_incremental()
