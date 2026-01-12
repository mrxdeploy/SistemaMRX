
"""
Script para testar permissões RBAC do sistema
"""
import os
os.environ['DATABASE_URL'] = os.environ.get('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/mrx_db')

from app import create_app
from app.models import db, Usuario, Perfil
import requests

def testar_rbac():
    app = create_app()
    
    with app.app_context():
        print("🧪 TESTE DE PERMISSÕES RBAC\n")
        print("="*80)
        
        perfis = Perfil.query.filter_by(ativo=True).all()
        
        for perfil in perfis:
            print(f"\n📋 PERFIL: {perfil.nome}")
            print(f"   Descrição: {perfil.descricao}")
            print(f"\n   ✅ Permissões Ativas:")
            
            if perfil.permissoes:
                permissoes_ativas = [k for k, v in perfil.permissoes.items() if v]
                if permissoes_ativas:
                    for perm in sorted(permissoes_ativas):
                        print(f"      • {perm}")
                else:
                    print("      (Nenhuma permissão ativa)")
            else:
                print("      (Sem permissões configuradas)")
            
            # Buscar usuário de teste para este perfil
            usuario = Usuario.query.filter_by(perfil_id=perfil.id).first()
            if usuario:
                print(f"\n   👤 Usuário de teste: {usuario.email}")
            
            print("-" * 80)
        
        print("\n" + "="*80)
        print("📊 MATRIZ DE PERMISSÕES POR PERFIL")
        print("="*80 + "\n")
        
        # Coletar todas as permissões únicas
        todas_permissoes = set()
        for perfil in perfis:
            if perfil.permissoes:
                todas_permissoes.update(perfil.permissoes.keys())
        
        # Cabeçalho
        print(f"{'Permissão':<35} | ", end="")
        for perfil in perfis:
            print(f"{perfil.nome[:8]:<8} | ", end="")
        print()
        print("-" * 150)
        
        # Linhas de permissões
        for perm in sorted(todas_permissoes):
            print(f"{perm:<35} | ", end="")
            for perfil in perfis:
                tem_perm = perfil.permissoes.get(perm, False) if perfil.permissoes else False
                print(f"{'✅' if tem_perm else '❌':^8} | ", end="")
            print()
        
        print("\n" + "="*80)
        print("💡 COMO TESTAR:")
        print("-" * 80)
        print("1. Execute 'python criar_usuarios_teste.py' para criar usuários")
        print("2. Faça login com cada email de teste (senha: teste123)")
        print("3. Verifique quais funcionalidades estão disponíveis")
        print("4. Teste ações que deveriam ser bloqueadas (ex: usuário comum tentando gerenciar usuários)")
        print("="*80)

if __name__ == '__main__':
    testar_rbac()
