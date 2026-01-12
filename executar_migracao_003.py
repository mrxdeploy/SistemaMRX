#!/usr/bin/env python3
"""
Script para executar a migração 003 - Adicionar classificação e preços por estrela
"""
import os
import sys
from app import create_app
from app.models import db

def executar_migracao():
    """Executa a migração 003 de forma segura"""
    app = create_app()
    
    with app.app_context():
        print("=" * 60)
        print("MIGRAÇÃO 003: Classificação e Preços por Estrela")
        print("=" * 60)
        
        # Ler o arquivo SQL de migração
        sql_path = os.path.join('migrations', '003_add_classificacao_e_precos_estrela.sql')
        
        if not os.path.exists(sql_path):
            print(f"❌ Erro: Arquivo de migração não encontrado: {sql_path}")
            return False
        
        with open(sql_path, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        print(f"\n📄 Lendo migração: {sql_path}")
        print(f"   Tamanho: {len(sql_content)} bytes\n")
        
        # Perguntar confirmação se não for forçado
        force = '--force' in sys.argv or os.getenv('FORCE_MIGRATE', 'false').lower() == 'true'
        
        if not force:
            print("⚠️  ATENÇÃO: Esta migração irá modificar o schema do banco de dados!")
            print("\nMudanças que serão aplicadas:")
            print("  1. Adicionar campo 'classificacao' na tabela tipos_lote")
            print("  2. Criar tabela 'tipo_lote_preco_estrelas'")
            print("  3. Adicionar índices e constraints")
            print("\n❗ Recomenda-se fazer backup do banco antes de continuar!")
            
            resposta = input("\nDeseja executar a migração? (s/N): ").strip().lower()
            
            if resposta != 's':
                print("\n❌ Migração cancelada pelo usuário.")
                return False
        
        try:
            print("\n🔄 Executando migração SQL...")
            
            # Executar o SQL
            db.session.execute(db.text(sql_content))
            db.session.commit()
            
            print("\n✅ Migração 003 executada com sucesso!")
            print("\nResumo das mudanças:")
            print("  ✓ Campo 'classificacao' adicionado em tipos_lote")
            print("  ✓ Tabela 'tipo_lote_preco_estrelas' criada")
            print("  ✓ Índices e constraints configurados")
            
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"\n❌ Erro ao executar migração: {str(e)}")
            print("\n💡 Dica: Verifique se o banco de dados está acessível")
            print("        e se você tem permissões adequadas.")
            return False

if __name__ == '__main__':
    print("\n🚀 Iniciando processo de migração...\n")
    
    sucesso = executar_migracao()
    
    if sucesso:
        print("\n" + "=" * 60)
        print("✨ Migração concluída! O sistema está pronto para uso.")
        print("=" * 60)
        print("\nPróximos passos:")
        print("  1. Configurar tipos de lote com classificações")
        print("  2. Definir preços padrão por estrela")
        print("  3. Reiniciar a aplicação\n")
        sys.exit(0)
    else:
        print("\n❌ Falha na migração. Verifique os erros acima.\n")
        sys.exit(1)
