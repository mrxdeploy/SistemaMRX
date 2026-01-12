"""
Script para inicializar as tabelas de preço (1★, 2★, 3★) no banco de dados
Este script é executado automaticamente na inicialização do app
"""
import os
os.environ['DATABASE_URL'] = os.environ.get('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/mrx_db')

from app import create_app
from app.models import db, TabelaPreco

def init_tabelas_preco():
    """Inicializa as 3 tabelas de preço se não existirem"""
    app = create_app()
    
    with app.app_context():
        # Verificar quais tabelas já existem
        tabelas_existentes = TabelaPreco.query.all()
        niveis_existentes = {t.nivel_estrelas for t in tabelas_existentes}
        
        # Criar as tabelas faltantes
        niveis_necessarios = {1, 2, 3}
        niveis_faltantes = niveis_necessarios - niveis_existentes
        
        if niveis_faltantes:
            print(f"Criando {len(niveis_faltantes)} tabela(s) de preço faltante(s)...")
            
            for nivel in sorted(niveis_faltantes):
                nome_estrelas = "Estrela" if nivel == 1 else "Estrelas"
                tabela = TabelaPreco(
                    nome=f'{nivel} {nome_estrelas}',
                    nivel_estrelas=nivel,
                    ativo=True
                )
                db.session.add(tabela)
                print(f"  ✓ Criada tabela: {tabela.nome}")
            
            db.session.commit()
            print("✅ Tabelas de preço inicializadas com sucesso!")
        else:
            print("✓ Todas as tabelas de preço já existem")
        
        # Verificar e exibir status final
        todas_tabelas = TabelaPreco.query.order_by(TabelaPreco.nivel_estrelas).all()
        print(f"\nTabelas de preço ativas:")
        for t in todas_tabelas:
            print(f"  - {t.nome} (ID: {t.id}, {t.nivel_estrelas} estrelas)")

if __name__ == '__main__':
    init_tabelas_preco()
