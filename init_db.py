#!/usr/bin/env python3
"""Script para inicializar o banco de dados com todas as tabelas necessárias."""

from app import create_app
from app.models import db
import sys
import os

def init_database(drop_existing=False):
    """Cria todas as tabelas no banco de dados.

    Args:
        drop_existing: Se True, remove todas as tabelas antes de criar (padrão: False)
    """
    try:
        # Verifica se DATABASE_URL está definido
        database_url = os.environ.get('DATABASE_URL')
        if not database_url:
            print("❌ ERRO: DATABASE_URL não está definido!")
            print("   Configure o PostgreSQL no Railway")
            return False

        print(f"🔗 Conectando ao banco de dados...")
        print(f"   URL: {database_url[:30]}...")

        app = create_app()

        with app.app_context():
            if drop_existing:
                print("⚠️  Removendo tabelas antigas...")
                db.drop_all()
                print("✅ Tabelas antigas removidas!")

            # Criar tabelas
            print("📊 Criando tabelas no banco de dados...")
            db.create_all()
            print("✅ Tabelas criadas/verificadas com sucesso!")

            # Executar migrações automáticas
            from sqlalchemy import text
            
            print("🔄 Verificando e aplicando migrações...")
            
            # Migração: bags_producao - colunas faltantes para módulo de produção
            try:
                migration_producao = """
                DO $$
                BEGIN
                    -- Colunas para bags_producao
                    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'bags_producao') THEN
                        IF NOT EXISTS (
                            SELECT 1 FROM information_schema.columns 
                            WHERE table_name = 'bags_producao' 
                            AND column_name = 'categoria_manual'
                        ) THEN
                            ALTER TABLE bags_producao ADD COLUMN categoria_manual VARCHAR(100);
                            RAISE NOTICE 'Adicionada coluna bags_producao.categoria_manual';
                        END IF;

                        IF NOT EXISTS (
                            SELECT 1 FROM information_schema.columns 
                            WHERE table_name = 'bags_producao' 
                            AND column_name = 'categorias_mistas'
                        ) THEN
                            ALTER TABLE bags_producao ADD COLUMN categorias_mistas BOOLEAN DEFAULT FALSE NOT NULL;
                            RAISE NOTICE 'Adicionada coluna bags_producao.categorias_mistas';
                        END IF;

                        IF NOT EXISTS (
                            SELECT 1 FROM information_schema.columns 
                            WHERE table_name = 'bags_producao' 
                            AND column_name = 'observacoes'
                        ) THEN
                            ALTER TABLE bags_producao ADD COLUMN observacoes TEXT;
                            RAISE NOTICE 'Adicionada coluna bags_producao.observacoes';
                        END IF;
                    END IF;

                    -- Colunas para usuarios
                    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'usuarios') THEN
                        IF NOT EXISTS (
                            SELECT 1 FROM information_schema.columns 
                            WHERE table_name = 'usuarios' 
                            AND column_name = 'foto_path'
                        ) THEN
                            ALTER TABLE usuarios ADD COLUMN foto_path VARCHAR(255);
                            RAISE NOTICE 'Adicionada coluna usuarios.foto_path';
                        END IF;
                    END IF;

                    -- Colunas para itens_producao
                    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'itens_producao') THEN
                        IF NOT EXISTS (
                            SELECT 1 FROM information_schema.columns 
                            WHERE table_name = 'itens_producao' 
                            AND column_name = 'custo_proporcional'
                        ) THEN
                            ALTER TABLE itens_producao ADD COLUMN custo_proporcional NUMERIC(10,2) DEFAULT 0;
                            RAISE NOTICE 'Adicionada coluna itens_producao.custo_proporcional';
                        END IF;

                        IF NOT EXISTS (
                            SELECT 1 FROM information_schema.columns 
                            WHERE table_name = 'itens_producao' 
                            AND column_name = 'valor_estimado'
                        ) THEN
                            ALTER TABLE itens_producao ADD COLUMN valor_estimado NUMERIC(10,2) DEFAULT 0;
                            RAISE NOTICE 'Adicionada coluna itens_producao.valor_estimado';
                        END IF;

                        IF NOT EXISTS (
                            SELECT 1 FROM information_schema.columns 
                            WHERE table_name = 'itens_producao' 
                            AND column_name = 'entrada_estoque_id'
                        ) THEN
                            ALTER TABLE itens_producao ADD COLUMN entrada_estoque_id INTEGER;
                            RAISE NOTICE 'Adicionada coluna itens_producao.entrada_estoque_id';
                        END IF;
                    END IF;

                    -- Colunas para ordens_producao
                    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'ordens_producao') THEN
                        IF NOT EXISTS (
                            SELECT 1 FROM information_schema.columns 
                            WHERE table_name = 'ordens_producao' 
                            AND column_name = 'custo_total_aquisicao'
                        ) THEN
                            ALTER TABLE ordens_producao ADD COLUMN custo_total_aquisicao NUMERIC(12,2) DEFAULT 0;
                            RAISE NOTICE 'Adicionada coluna ordens_producao.custo_total_aquisicao';
                        END IF;

                        IF NOT EXISTS (
                            SELECT 1 FROM information_schema.columns 
                            WHERE table_name = 'ordens_producao' 
                            AND column_name = 'valor_total_estimado'
                        ) THEN
                            ALTER TABLE ordens_producao ADD COLUMN valor_total_estimado NUMERIC(12,2) DEFAULT 0;
                            RAISE NOTICE 'Adicionada coluna ordens_producao.valor_total_estimado';
                        END IF;
                    END IF;

                    -- Colunas para fornecedores (migração 020)
                    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'fornecedores') THEN
                        IF NOT EXISTS (
                            SELECT 1 FROM information_schema.columns 
                            WHERE table_name = 'fornecedores' 
                            AND column_name = 'tabela_preco_status'
                        ) THEN
                            ALTER TABLE fornecedores ADD COLUMN tabela_preco_status VARCHAR(20) DEFAULT 'pendente';
                            RAISE NOTICE 'Adicionada coluna fornecedores.tabela_preco_status';
                        END IF;

                        IF NOT EXISTS (
                            SELECT 1 FROM information_schema.columns 
                            WHERE table_name = 'fornecedores' 
                            AND column_name = 'tabela_preco_aprovada_em'
                        ) THEN
                            ALTER TABLE fornecedores ADD COLUMN tabela_preco_aprovada_em TIMESTAMP;
                            RAISE NOTICE 'Adicionada coluna fornecedores.tabela_preco_aprovada_em';
                        END IF;

                        IF NOT EXISTS (
                            SELECT 1 FROM information_schema.columns 
                            WHERE table_name = 'fornecedores' 
                            AND column_name = 'tabela_preco_aprovada_por_id'
                        ) THEN
                            ALTER TABLE fornecedores ADD COLUMN tabela_preco_aprovada_por_id INTEGER;
                            RAISE NOTICE 'Adicionada coluna fornecedores.tabela_preco_aprovada_por_id';
                        END IF;
                    END IF;

                    -- Colunas para entradas_estoque
                    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'entradas_estoque') THEN
                        IF NOT EXISTS (
                            SELECT 1 FROM information_schema.columns 
                            WHERE table_name = 'entradas_estoque' 
                            AND column_name = 'usado_producao'
                        ) THEN
                            ALTER TABLE entradas_estoque ADD COLUMN usado_producao BOOLEAN DEFAULT FALSE;
                            RAISE NOTICE 'Adicionada coluna entradas_estoque.usado_producao';
                        END IF;
                    END IF;
                END $$;

                -- Criar índices se não existirem
                CREATE INDEX IF NOT EXISTS idx_bag_classificacao ON bags_producao(classificacao_grade_id);
                CREATE INDEX IF NOT EXISTS idx_bag_status ON bags_producao(status);
                CREATE INDEX IF NOT EXISTS idx_fornecedores_tabela_preco_status ON fornecedores(tabela_preco_status);
                """
                db.session.execute(text(migration_producao))
                db.session.commit()
                print("✅ Migrações de produção aplicadas!")
            except Exception as e:
                print(f"⚠️  Aviso ao aplicar migrações: {e}")
                db.session.rollback()

            # Lista as tabelas criadas
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            print(f"📋 Tabelas no banco: {', '.join(tables)}")

            try:
                from app.auth import criar_admin_padrao
                criar_admin_padrao()
                print("✅ Usuário admin verificado!")
            except Exception as e:
                print(f"⚠️  Aviso ao criar admin: {e}")

        return True
    except Exception as e:
        print(f"❌ Erro ao inicializar banco de dados: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    # Verifica se deve fazer drop das tabelas
    drop = '--drop' in sys.argv or os.environ.get('DROP_TABLES', '').lower() == 'true'

    if drop:
        print("⚠️  MODO DESTRUTIVO: Todas as tabelas serão removidas e recriadas!")

    success = init_database(drop_existing=drop)
    sys.exit(0 if success else 1)