
from app import create_app
from app.models import db, Usuario, Perfil
from app.auth import hash_senha

app = create_app()

with app.app_context():
    print("🔄 Recriando usuários de teste com senhas válidas...")
    
    # Buscar perfis
    perfil_comprador = Perfil.query.filter_by(nome='Comprador (PJ)').first()
    perfil_conferente = Perfil.query.filter_by(nome='Conferente / Estoque').first()
    perfil_separacao = Perfil.query.filter_by(nome='Separação').first()
    perfil_financeiro = Perfil.query.filter_by(nome='Financeiro').first()
    perfil_auditoria = Perfil.query.filter_by(nome='Auditoria / BI').first()
    
    # Lista de usuários para criar/atualizar
    usuarios_teste = [
        {
            'email': 'joao.comprador@mrx.com',
            'nome': 'João Comprador',
            'senha': 'senha123',
            'tipo': 'funcionario',
            'perfil': perfil_comprador
        },
        {
            'email': 'fernanda.compradora@mrx.com',
            'nome': 'Fernanda Compradora',
            'senha': 'senha123',
            'tipo': 'funcionario',
            'perfil': perfil_comprador
        },
        {
            'email': 'carlos.conferente@mrx.com',
            'nome': 'Carlos Conferente',
            'senha': 'senha123',
            'tipo': 'funcionario',
            'perfil': perfil_conferente
        },
        {
            'email': 'ana.separacao@mrx.com',
            'nome': 'Ana Separação',
            'senha': 'senha123',
            'tipo': 'funcionario',
            'perfil': perfil_separacao
        },
        {
            'email': 'roberto.financeiro@mrx.com',
            'nome': 'Roberto Financeiro',
            'senha': 'senha123',
            'tipo': 'funcionario',
            'perfil': perfil_financeiro
        },
        {
            'email': 'auditoria@teste.com',
            'nome': 'Usuário Auditoria',
            'senha': 'senha123',
            'tipo': 'funcionario',
            'perfil': perfil_auditoria
        }
    ]
    
    for usuario_data in usuarios_teste:
        # Verificar se usuário já existe
        usuario_existente = Usuario.query.filter_by(email=usuario_data['email']).first()
        
        if usuario_existente:
            print(f"♻️  Atualizando senha de {usuario_data['email']}...")
            usuario_existente.senha_hash = hash_senha(usuario_data['senha'])
            usuario_existente.ativo = True
        else:
            print(f"✅ Criando usuário {usuario_data['email']}...")
            novo_usuario = Usuario(
                email=usuario_data['email'],
                nome=usuario_data['nome'],
                senha_hash=hash_senha(usuario_data['senha']),
                tipo=usuario_data['tipo'],
                perfil_id=usuario_data['perfil'].id if usuario_data['perfil'] else None,
                ativo=True,
                criado_por=1  # Admin
            )
            db.session.add(novo_usuario)
    
    db.session.commit()
    print("\n✅ Usuários de teste atualizados com sucesso!")
    print("\n📋 Credenciais de acesso:")
    print("=" * 60)
    for usuario_data in usuarios_teste:
        print(f"Email: {usuario_data['email']}")
        print(f"Senha: {usuario_data['senha']}")
        print(f"Perfil: {usuario_data['perfil'].nome if usuario_data['perfil'] else 'Sem perfil'}")
        print("-" * 60)
