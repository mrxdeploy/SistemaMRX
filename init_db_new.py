import os
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

def executar_migr_sql():
    """Executa o script de migração SQL"""
    
    database_url = os.environ.get('DATABASE_URL')
    
    if not database_url:
        print("❌ DATABASE_URL não configurada!")
        print("Configure a variável de ambiente DATABASE_URL antes de executar este script.")
        return False
    
    print("=" * 60)
    print("MIGRAÇÃO PARA NOVA ESTRUTURA DO SISTEMA MRX")
    print("=" * 60)
    print()
    print("⚠️  ATENÇÃO: Este script irá APAGAR TODOS OS DADOS!")
    print("⚠️  Use apenas em ambiente de desenvolvimento ou com backup!")
    print()
    
    confirmacao = input("Digite 'SIM' para confirmar a migração: ")
    
    if confirmacao != 'SIM':
        print("❌ Migração cancelada pelo usuário.")
        return False
    
    try:
        print("\n🔄 Conectando ao banco de dados...")
        conn = psycopg2.connect(database_url)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        print("📖 Lendo script de migração...")
        with open('migrations/migrate_to_new_schema.sql', 'r', encoding='utf-8') as f:
            sql_script = f.read()
        
        print("🗑️  Removendo estrutura antiga...")
        print("🆕 Criando nova estrutura...")
        print("📦 Inserindo dados iniciais...")
        
        cursor.execute(sql_script)
        
        print("\n✅ Migração executada com sucesso!")
        print()
        print("📊 Verificando dados criados...")
        
        cursor.execute("SELECT COUNT(*) FROM usuarios WHERE tipo = 'admin'")
        admins = cursor.fetchone()[0]
        print(f"   - Usuários admin: {admins}")
        
        cursor.execute("SELECT COUNT(*) FROM tipos_lote")
        tipos = cursor.fetchone()[0]
        print(f"   - Tipos de lote: {tipos}")
        
        print()
        print("🔐 Credenciais de acesso:")
        print("   Email: admin@sistema.com")
        print("   Senha: admin123")
        print()
        print("⚠️  IMPORTANTE: Altere a senha padrão em produção!")
        print()
        print("=" * 60)
        
        cursor.close()
        conn.close()
        
        return True
        
    except psycopg2.Error as e:
        print(f"\n❌ Erro ao executar migração: {e}")
        return False
    except FileNotFoundError:
        print("\n❌ Arquivo de migração não encontrado: migrations/migrate_to_new_schema.sql")
        return False
    except Exception as e:
        print(f"\n❌ Erro inesperado: {e}")
        return False

if __name__ == '__main__':
    sucesso = executar_migr_sql()
    
    if sucesso:
        print("\n✅ Banco de dados pronto para uso!")
        print("🚀 Inicie a aplicação com: python app.py")
    else:
        print("\n❌ Migração não foi concluída.")
        print("Verifique os erros acima e tente novamente.")
