"""
Migração para adicionar todas as colunas e tabelas do novo sistema de solicitações
Data: 24/11/2025
Descrição: Adiciona suporte completo ao sistema reformulado de solicitações com:
- Sistema de materiais e tabelas de preço
- Preços customizados por material
- Aprovação automática baseada em estrelas do fornecedor
- Sistema de Ordens de Compra (OC)
- Lotes vinculados a solicitações
"""

import os
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

def executar_migração():
    """Executa a migração do banco de dados"""
    
    # Obter conexão do ambiente
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ ERROR: DATABASE_URL não encontrada nas variáveis de ambiente")
        return False
    
    # Ajustar URL do Neon se necessário
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    
    try:
        conn = psycopg2.connect(database_url)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        print("\n" + "="*60)
        print(" INICIANDO MIGRAÇÃO DO SISTEMA DE SOLICITAÇÕES")
        print("="*60 + "\n")
        
        # ============================================================
        # 1. CRIAR TABELA DE MATERIAIS BASE (se não existir)
        # ============================================================
        print("📦 Etapa 1: Criando tabela materiais_base...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS materiais_base (
                id SERIAL PRIMARY KEY,
                codigo VARCHAR(50) UNIQUE NOT NULL,
                nome VARCHAR(200) NOT NULL,
                classificacao VARCHAR(10),
                descricao TEXT,
                ativo BOOLEAN DEFAULT TRUE NOT NULL,
                criado_por INTEGER REFERENCES usuarios(id),
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
            );
        """)
        print("   ✓ Tabela materiais_base criada/verificada")
        
        # ============================================================
        # 2. CRIAR TABELA DE TABELAS DE PREÇO (se não existir)
        # ============================================================
        print("\n💰 Etapa 2: Criando tabela tabelas_preco...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tabelas_preco (
                id SERIAL PRIMARY KEY,
                nome VARCHAR(100) UNIQUE NOT NULL,
                nivel_estrelas INTEGER NOT NULL CHECK (nivel_estrelas >= 1 AND nivel_estrelas <= 3),
                descricao TEXT,
                ativo BOOLEAN DEFAULT TRUE NOT NULL,
                criado_por INTEGER REFERENCES usuarios(id),
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
            );
        """)
        print("   ✓ Tabela tabelas_preco criada/verificada")
        
        # ============================================================
        # 3. CRIAR TABELA DE ITENS DE PREÇO (se não existir)
        # ============================================================
        print("\n📊 Etapa 3: Criando tabela tabelas_preco_itens...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tabelas_preco_itens (
                id SERIAL PRIMARY KEY,
                tabela_preco_id INTEGER NOT NULL REFERENCES tabelas_preco(id) ON DELETE CASCADE,
                material_id INTEGER NOT NULL REFERENCES materiais_base(id) ON DELETE CASCADE,
                preco_por_kg FLOAT NOT NULL CHECK (preco_por_kg >= 0),
                ativo BOOLEAN DEFAULT TRUE NOT NULL,
                atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                UNIQUE(tabela_preco_id, material_id)
            );
        """)
        print("   ✓ Tabela tabelas_preco_itens criada/verificada")
        
        # ============================================================
        # 4. ADICIONAR COLUNAS NA TABELA SOLICITACOES
        # ============================================================
        print("\n📋 Etapa 4: Atualizando tabela solicitacoes...")
        
        colunas_solicitacoes = [
            ("tipo_retirada", "VARCHAR(20) DEFAULT 'buscar'"),
            ("modalidade_frete", "VARCHAR(10) DEFAULT 'FOB'"),
            ("rua", "VARCHAR(200)"),
            ("numero", "VARCHAR(20)"),
            ("cep", "VARCHAR(10)"),
            ("localizacao_lat", "FLOAT"),
            ("localizacao_lng", "FLOAT"),
            ("endereco_completo", "VARCHAR(500)"),
        ]
        
        for coluna, tipo in colunas_solicitacoes:
            try:
                cursor.execute(f"""
                    ALTER TABLE solicitacoes 
                    ADD COLUMN IF NOT EXISTS {coluna} {tipo};
                """)
                print(f"   ✓ Coluna {coluna} adicionada/verificada")
            except Exception as e:
                print(f"   ⚠️  Coluna {coluna}: {str(e)}")
        
        # ============================================================
        # 5. CRIAR/ATUALIZAR TABELA ITENS_SOLICITACAO
        # ============================================================
        print("\n📦 Etapa 5: Atualizando tabela itens_solicitacao...")
        
        # Criar tabela se não existir
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS itens_solicitacao (
                id SERIAL PRIMARY KEY,
                solicitacao_id INTEGER NOT NULL REFERENCES solicitacoes(id) ON DELETE CASCADE,
                tipo_lote_id INTEGER REFERENCES tipos_lote(id),
                material_id INTEGER REFERENCES materiais_base(id),
                peso_kg FLOAT NOT NULL CHECK (peso_kg > 0),
                estrelas_sugeridas_ia INTEGER,
                estrelas_final INTEGER DEFAULT 3 NOT NULL,
                classificacao VARCHAR(10),
                classificacao_sugerida_ia VARCHAR(10),
                justificativa_ia TEXT,
                valor_calculado FLOAT DEFAULT 0.0 NOT NULL,
                preco_por_kg_snapshot FLOAT,
                estrelas_snapshot INTEGER,
                preco_customizado BOOLEAN DEFAULT FALSE NOT NULL,
                preco_oferecido FLOAT,
                imagem_url VARCHAR(500),
                observacoes TEXT,
                data_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                lote_id INTEGER REFERENCES lotes(id)
            );
        """)
        print("   ✓ Tabela itens_solicitacao criada/verificada")
        
        # Adicionar colunas que podem não existir
        colunas_itens = [
            ("material_id", "INTEGER REFERENCES materiais_base(id)"),
            ("preco_customizado", "BOOLEAN DEFAULT FALSE NOT NULL"),
            ("preco_oferecido", "FLOAT"),
            ("preco_por_kg_snapshot", "FLOAT"),
            ("estrelas_snapshot", "INTEGER"),
        ]
        
        for coluna, tipo in colunas_itens:
            try:
                cursor.execute(f"""
                    ALTER TABLE itens_solicitacao 
                    ADD COLUMN IF NOT EXISTS {coluna} {tipo};
                """)
                print(f"   ✓ Coluna {coluna} adicionada/verificada")
            except Exception as e:
                print(f"   ⚠️  Coluna {coluna}: {str(e)}")
        
        # ============================================================
        # 6. ADICIONAR COLUNA tabela_preco_id EM FORNECEDORES
        # ============================================================
        print("\n🏢 Etapa 6: Atualizando tabela fornecedores...")
        try:
            cursor.execute("""
                ALTER TABLE fornecedores 
                ADD COLUMN IF NOT EXISTS tabela_preco_id INTEGER REFERENCES tabelas_preco(id);
            """)
            print("   ✓ Coluna tabela_preco_id adicionada/verificada")
        except Exception as e:
            print(f"   ⚠️  Coluna tabela_preco_id: {str(e)}")
        
        # ============================================================
        # 7. CRIAR TABELA ORDENS_COMPRA (se não existir)
        # ============================================================
        print("\n📑 Etapa 7: Criando tabela ordens_compra...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ordens_compra (
                id SERIAL PRIMARY KEY,
                solicitacao_id INTEGER UNIQUE NOT NULL REFERENCES solicitacoes(id) ON DELETE CASCADE,
                fornecedor_id INTEGER NOT NULL REFERENCES fornecedores(id),
                valor_total FLOAT DEFAULT 0.0 NOT NULL,
                status VARCHAR(50) DEFAULT 'em_analise' NOT NULL,
                aprovado_por INTEGER REFERENCES usuarios(id),
                aprovado_em TIMESTAMP,
                observacao TEXT,
                ip_aprovacao VARCHAR(50),
                gps_aprovacao VARCHAR(100),
                device_info VARCHAR(100),
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                criado_por INTEGER NOT NULL REFERENCES usuarios(id)
            );
        """)
        print("   ✓ Tabela ordens_compra criada/verificada")
        
        # ============================================================
        # 8. CRIAR TABELA AUDITORIA_OC (se não existir)
        # ============================================================
        print("\n📝 Etapa 8: Criando tabela auditoria_oc...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS auditoria_oc (
                id SERIAL PRIMARY KEY,
                oc_id INTEGER NOT NULL REFERENCES ordens_compra(id) ON DELETE CASCADE,
                usuario_id INTEGER REFERENCES usuarios(id),
                acao VARCHAR(50) NOT NULL,
                status_anterior VARCHAR(50),
                status_novo VARCHAR(50),
                observacao TEXT,
                ip VARCHAR(50),
                gps VARCHAR(100),
                dispositivo VARCHAR(500),
                data TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
            );
        """)
        
        # Criar índice se não existir
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_oc_data ON auditoria_oc(oc_id, data);
        """)
        print("   ✓ Tabela auditoria_oc criada/verificada")
        print("   ✓ Índice idx_oc_data criado/verificado")
        
        # ============================================================
        # 9. CRIAR ÍNDICES PARA MELHOR PERFORMANCE
        # ============================================================
        print("\n🔍 Etapa 9: Criando índices...")
        indices = [
            ("idx_solicitacoes_status", "solicitacoes", "status"),
            ("idx_solicitacoes_fornecedor", "solicitacoes", "fornecedor_id"),
            ("idx_itens_solicitacao", "itens_solicitacao", "solicitacao_id"),
            ("idx_itens_material", "itens_solicitacao", "material_id"),
            ("idx_ocs_status", "ordens_compra", "status"),
            ("idx_ocs_solicitacao", "ordens_compra", "solicitacao_id"),
        ]
        
        for nome_indice, tabela, coluna in indices:
            try:
                cursor.execute(f"""
                    CREATE INDEX IF NOT EXISTS {nome_indice} ON {tabela}({coluna});
                """)
                print(f"   ✓ Índice {nome_indice} criado/verificado")
            except Exception as e:
                print(f"   ⚠️  Índice {nome_indice}: {str(e)}")
        
        # ============================================================
        # FINALIZAÇÃO
        # ============================================================
        print("\n" + "="*60)
        print(" ✅ MIGRAÇÃO CONCLUÍDA COM SUCESSO!")
        print("="*60)
        print("\nPróximos passos:")
        print("1. Verificar se os dados foram migrados corretamente")
        print("2. Criar tabelas de preço e materiais no sistema")
        print("3. Vincular fornecedores às tabelas de preço")
        print("4. Testar criação de solicitações com o novo sistema\n")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"\n❌ ERRO durante a migração: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Executando migração do sistema de solicitações...")
    sucesso = executar_migração()
    exit(0 if sucesso else 1)
