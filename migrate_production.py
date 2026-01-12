#!/usr/bin/env python3
"""
Script de Migração para Produção - Adiciona colunas faltantes de forma segura
Execute com: python migrate_production.py

Este script verifica e adiciona colunas faltantes sem destruir dados existentes.
Ideal para ambientes de produção (Railway, Heroku, etc.)
"""
import os
import sys
import psycopg2
from psycopg2 import sql

def get_database_url():
    """Obtém a URL do banco de dados"""
    database_url = os.getenv('DATABASE_URL')
    
    if not database_url:
        print("❌ Erro: DATABASE_URL não configurada")
        print("   Configure a variável de ambiente DATABASE_URL")
        sys.exit(1)
    
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    
    return database_url

def column_exists(cursor, table_name, column_name):
    """Verifica se uma coluna existe em uma tabela"""
    cursor.execute("""
        SELECT EXISTS (
            SELECT 1 
            FROM information_schema.columns 
            WHERE table_schema = 'public' 
            AND table_name = %s 
            AND column_name = %s
        );
    """, (table_name, column_name))
    return cursor.fetchone()[0]

def table_exists(cursor, table_name):
    """Verifica se uma tabela existe"""
    cursor.execute("""
        SELECT EXISTS (
            SELECT 1 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = %s
        );
    """, (table_name,))
    return cursor.fetchone()[0]

def index_exists(cursor, index_name):
    """Verifica se um índice existe"""
    cursor.execute("""
        SELECT EXISTS (
            SELECT 1 
            FROM pg_indexes 
            WHERE schemaname = 'public' 
            AND indexname = %s
        );
    """, (index_name,))
    return cursor.fetchone()[0]

def add_column_if_not_exists(cursor, table_name, column_name, column_definition):
    """Adiciona uma coluna se ela não existir"""
    if not column_exists(cursor, table_name, column_name):
        try:
            cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition};")
            print(f"   ✅ Adicionada coluna: {table_name}.{column_name}")
            return True
        except Exception as e:
            print(f"   ⚠️ Erro ao adicionar {table_name}.{column_name}: {e}")
            return False
    else:
        print(f"   ✓ Coluna já existe: {table_name}.{column_name}")
        return True

def create_index_if_not_exists(cursor, index_name, table_name, column_name):
    """Cria um índice se ele não existir"""
    if not index_exists(cursor, index_name):
        try:
            cursor.execute(f"CREATE INDEX {index_name} ON {table_name}({column_name});")
            print(f"   ✅ Criado índice: {index_name}")
            return True
        except Exception as e:
            print(f"   ⚠️ Erro ao criar índice {index_name}: {e}")
            return False
    else:
        print(f"   ✓ Índice já existe: {index_name}")
        return True

def executar_migracao():
    """Executa a migração de produção de forma segura"""
    
    database_url = get_database_url()
    
    print("=" * 60)
    print("🔄 MIGRAÇÃO DE PRODUÇÃO - Modo Seguro")
    print("=" * 60)
    print("📊 Conectando ao banco de dados...")
    
    try:
        conn = psycopg2.connect(database_url)
        conn.autocommit = False
        cursor = conn.cursor()
        
        print("✅ Conectado com sucesso!\n")
        
        print("📋 ETAPA 1: Migrando tabela bags_producao...")
        print("-" * 40)
        
        if table_exists(cursor, 'bags_producao'):
            add_column_if_not_exists(cursor, 'bags_producao', 'categoria_manual', 'VARCHAR(100)')
            add_column_if_not_exists(cursor, 'bags_producao', 'categorias_mistas', 'BOOLEAN DEFAULT FALSE NOT NULL')
            add_column_if_not_exists(cursor, 'bags_producao', 'observacoes', 'TEXT')
        else:
            print("   ⚠️ Tabela bags_producao não encontrada")
        
        print("\n📋 ETAPA 2: Migrando tabela usuarios...")
        print("-" * 40)
        
        if table_exists(cursor, 'usuarios'):
            add_column_if_not_exists(cursor, 'usuarios', 'foto_path', 'VARCHAR(255)')
            add_column_if_not_exists(cursor, 'usuarios', 'ultimo_acesso', 'TIMESTAMP')
            add_column_if_not_exists(cursor, 'usuarios', 'tentativas_login', 'INTEGER DEFAULT 0')
            add_column_if_not_exists(cursor, 'usuarios', 'bloqueado_ate', 'TIMESTAMP')
        else:
            print("   ⚠️ Tabela usuarios não encontrada")
        
        print("\n📋 ETAPA 3: Migrando tabela itens_producao...")
        print("-" * 40)
        
        if table_exists(cursor, 'itens_producao'):
            add_column_if_not_exists(cursor, 'itens_producao', 'custo_proporcional', 'NUMERIC(10,2) DEFAULT 0')
            add_column_if_not_exists(cursor, 'itens_producao', 'valor_estimado', 'NUMERIC(10,2) DEFAULT 0')
            add_column_if_not_exists(cursor, 'itens_producao', 'entrada_estoque_id', 'INTEGER')
        else:
            print("   ⚠️ Tabela itens_producao não encontrada")
        
        print("\n📋 ETAPA 4: Migrando tabela ordens_producao...")
        print("-" * 40)
        
        if table_exists(cursor, 'ordens_producao'):
            add_column_if_not_exists(cursor, 'ordens_producao', 'custo_total_aquisicao', 'NUMERIC(12,2) DEFAULT 0')
            add_column_if_not_exists(cursor, 'ordens_producao', 'valor_total_estimado', 'NUMERIC(12,2) DEFAULT 0')
            add_column_if_not_exists(cursor, 'ordens_producao', 'margem_estimada', 'NUMERIC(5,2) DEFAULT 0')
            add_column_if_not_exists(cursor, 'ordens_producao', 'peso_entrada', 'NUMERIC(10,3) DEFAULT 0')
            add_column_if_not_exists(cursor, 'ordens_producao', 'peso_saida', 'NUMERIC(10,3) DEFAULT 0')
            add_column_if_not_exists(cursor, 'ordens_producao', 'percentual_perda', 'NUMERIC(5,2) DEFAULT 0')
        else:
            print("   ⚠️ Tabela ordens_producao não encontrada")
        
        print("\n📋 ETAPA 5: Migrando tabela lotes...")
        print("-" * 40)
        
        if table_exists(cursor, 'lotes'):
            add_column_if_not_exists(cursor, 'lotes', 'observacoes_qualidade', 'TEXT')
            add_column_if_not_exists(cursor, 'lotes', 'fotos_qualidade', 'JSON')
            add_column_if_not_exists(cursor, 'lotes', 'avaliacao_qualidade', 'INTEGER')
        else:
            print("   ⚠️ Tabela lotes não encontrada")
        
        print("\n📋 ETAPA 6: Migrando tabela entradas_estoque...")
        print("-" * 40)
        
        if table_exists(cursor, 'entradas_estoque'):
            add_column_if_not_exists(cursor, 'entradas_estoque', 'usado_producao', 'BOOLEAN DEFAULT FALSE')
            add_column_if_not_exists(cursor, 'entradas_estoque', 'ordem_producao_id', 'INTEGER')
        else:
            print("   ⚠️ Tabela entradas_estoque não encontrada")
        
        print("\n📋 ETAPA 7: Verificando índices...")
        print("-" * 40)
        
        if table_exists(cursor, 'bags_producao'):
            create_index_if_not_exists(cursor, 'idx_bag_classificacao', 'bags_producao', 'classificacao_grade_id')
            create_index_if_not_exists(cursor, 'idx_bag_status', 'bags_producao', 'status')
        
        if table_exists(cursor, 'itens_producao'):
            create_index_if_not_exists(cursor, 'idx_itens_producao_bag', 'itens_producao', 'bag_id')
        
        conn.commit()
        
        print("\n" + "=" * 60)
        print("✅ MIGRAÇÃO CONCLUÍDA COM SUCESSO!")
        print("=" * 60)
        
        print("\n📊 Verificando estado do banco...")
        cursor.execute("""
            SELECT table_name, 
                   (SELECT COUNT(*) FROM information_schema.columns 
                    WHERE table_name = t.table_name AND table_schema = 'public') as num_columns
            FROM information_schema.tables t
            WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE'
            AND table_name IN ('bags_producao', 'usuarios', 'itens_producao', 'ordens_producao', 'lotes', 'entradas_estoque')
            ORDER BY table_name;
        """)
        
        tabelas = cursor.fetchall()
        print(f"\n   Tabelas atualizadas:")
        for tabela in tabelas:
            print(f"   - {tabela[0]}: {tabela[1]} colunas")
        
        cursor.close()
        conn.close()
        
        print("\n✅ Banco de dados de produção atualizado!")
        print("   O sistema pode ser reiniciado com segurança.")
        
    except Exception as e:
        print(f"\n❌ Erro durante a migração: {str(e)}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        sys.exit(1)

def verificar_status():
    """Verifica o status atual das colunas sem fazer alterações"""
    
    database_url = get_database_url()
    
    print("=" * 60)
    print("📊 VERIFICAÇÃO DE STATUS DO BANCO")
    print("=" * 60)
    
    try:
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        colunas_verificar = [
            ('bags_producao', 'categoria_manual'),
            ('bags_producao', 'categorias_mistas'),
            ('bags_producao', 'observacoes'),
            ('usuarios', 'foto_path'),
            ('itens_producao', 'custo_proporcional'),
            ('itens_producao', 'valor_estimado'),
            ('ordens_producao', 'custo_total_aquisicao'),
            ('ordens_producao', 'valor_total_estimado'),
        ]
        
        print("\n📋 Status das colunas críticas:")
        print("-" * 40)
        
        todas_ok = True
        for tabela, coluna in colunas_verificar:
            if table_exists(cursor, tabela):
                exists = column_exists(cursor, tabela, coluna)
                status = "✅" if exists else "❌"
                print(f"   {status} {tabela}.{coluna}")
                if not exists:
                    todas_ok = False
            else:
                print(f"   ⚠️ Tabela {tabela} não existe")
                todas_ok = False
        
        cursor.close()
        conn.close()
        
        print("\n" + "-" * 40)
        if todas_ok:
            print("✅ Todas as colunas estão presentes!")
        else:
            print("⚠️ Algumas colunas estão faltando.")
            print("   Execute: python migrate_production.py")
        
    except Exception as e:
        print(f"❌ Erro ao verificar: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Migração segura para produção')
    parser.add_argument('--check', action='store_true',
                       help='Apenas verifica o status sem fazer alterações')
    
    args = parser.parse_args()
    
    if args.check:
        verificar_status()
    else:
        executar_migracao()
