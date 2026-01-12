"""
Script para criar dados de teste para o módulo de logística
"""
import os
os.environ['DATABASE_URL'] = os.environ.get('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/mrx_db')

from app import create_app
from app.models import db, Usuario, Motorista, Veiculo, Fornecedor, OrdemCompra, OrdemServico
from datetime import datetime, timedelta
import uuid

def criar_dados_logistica():
    app = create_app()
    
    with app.app_context():
        print("🚛 Criando dados de teste para Logística...\n")
        
        # 1. Criar motoristas (vinculados aos usuários que já existem)
        print("1️⃣ Criando Motoristas...")
        motorista_user = Usuario.query.filter_by(email='motorista@teste.com').first()
        
        if motorista_user and not Motorista.query.filter_by(usuario_id=motorista_user.id).first():
            motorista1 = Motorista(
                usuario_id=motorista_user.id,
                nome='João Silva',
                cpf='12345678901',
                email='motorista@teste.com',
                cnh='123456789',
                categoria_cnh='D',
                telefone='11987654321',
                ativo=True
            )
            db.session.add(motorista1)
            print(f"   ✅ Motorista criado: João Silva")
        
        # Criar mais um motorista de teste
        user_motorista2 = Usuario.query.filter_by(email='separacao@teste.com').first()
        if user_motorista2 and not Motorista.query.filter_by(usuario_id=user_motorista2.id).first():
            motorista2 = Motorista(
                usuario_id=user_motorista2.id,
                nome='Maria Santos',
                cpf='98765432100',
                email='separacao@teste.com',
                cnh='987654321',
                categoria_cnh='C',
                telefone='11912345678',
                ativo=True
            )
            db.session.add(motorista2)
            print(f"   ✅ Motorista criado: Maria Santos")
        
        db.session.commit()
        
        # 2. Criar veículos
        print("\n2️⃣ Criando Veículos...")
        if not Veiculo.query.filter_by(placa='ABC1234').first():
            veiculo1 = Veiculo(
                placa='ABC1234',
                renavam='12345678901',
                tipo='VAN',
                capacidade=1500.0,
                marca='Fiat',
                modelo='Ducato',
                ano=2020,
                ativo=True
            )
            db.session.add(veiculo1)
            print("   ✅ Veículo criado: ABC1234 - Fiat Ducato")
        
        if not Veiculo.query.filter_by(placa='XYZ5678').first():
            veiculo2 = Veiculo(
                placa='XYZ5678',
                renavam='98765432100',
                tipo='CAMINHAO',
                capacidade=5000.0,
                marca='Mercedes',
                modelo='Sprinter',
                ano=2021,
                ativo=True
            )
            db.session.add(veiculo2)
            print("   ✅ Veículo criado: XYZ5678 - Mercedes Sprinter")
        
        db.session.commit()
        
        # 3. Criar fornecedor de teste se não existir
        print("\n3️⃣ Verificando Fornecedores...")
        fornecedor = Fornecedor.query.first()
        if not fornecedor:
            fornecedor = Fornecedor(
                cnpj='12345678000190',
                nome='Fornecedor Teste Ltda',
                nome_social='Fornecedor Teste',
                telefone='11987654321',
                email='fornecedor@teste.com',
                rua='Rua Teste',
                numero='123',
                bairro='Centro',
                cidade='São Paulo',
                estado='SP',
                cep='01234567',
                ativo=True
            )
            db.session.add(fornecedor)
            db.session.commit()
            print("   ✅ Fornecedor criado: Fornecedor Teste Ltda")
        else:
            print(f"   ℹ️  Fornecedor existente: {fornecedor.nome}")
        
        # 4. Verificar OCs existentes
        print("\n4️⃣ Verificando Ordens de Compra aprovadas...")
        ocs_aprovadas = OrdemCompra.query.filter_by(status='aprovada').all()
        print(f"   ℹ️  Encontradas {len(ocs_aprovadas)} OCs aprovadas no sistema")
        
        if ocs_aprovadas:
            print("\n5️⃣ Gerando Ordens de Serviço automaticamente...")
            admin = Usuario.query.filter_by(email='admin@teste.com').first()
            
            os_criadas = 0
            for oc in ocs_aprovadas:
                # Verificar se já existe OS para esta OC
                if OrdemServico.query.filter_by(oc_id=oc.id).first():
                    continue
                
                # Criar snapshot do fornecedor
                fornecedor_oc = oc.fornecedor
                fornecedor_snap = {
                    'id': fornecedor_oc.id,
                    'nome': fornecedor_oc.nome,
                    'cnpj': fornecedor_oc.cnpj,
                    'cpf': fornecedor_oc.cpf,
                    'telefone': fornecedor_oc.telefone,
                    'rua': fornecedor_oc.rua,
                    'numero': fornecedor_oc.numero,
                    'bairro': fornecedor_oc.bairro,
                    'cidade': fornecedor_oc.cidade,
                    'estado': fornecedor_oc.estado,
                    'cep': fornecedor_oc.cep
                }
                
                os = OrdemServico(
                    oc_id=oc.id,
                    numero_os=f'OS-{datetime.now().strftime("%Y%m%d")}-{str(uuid.uuid4())[:6].upper()}',
                    fornecedor_snapshot=fornecedor_snap,
                    tipo='COLETA',
                    status='PENDENTE',
                    janela_coleta_inicio=datetime.now() + timedelta(days=1),
                    janela_coleta_fim=datetime.now() + timedelta(days=1, hours=4),
                    created_by=admin.id if admin else None
                )
                
                db.session.add(os)
                os_criadas += 1
                print(f"   ✅ OS criada: {os.numero_os} para OC #{oc.id}")
            
            db.session.commit()
            print(f"   Total: {os_criadas} novas OS criadas")
        else:
            print("   ⚠️  Nenhuma OC aprovada encontrada. Crie solicitações e aprove-as primeiro!")
        
        print("\n" + "="*60)
        print("🎉 DADOS DE LOGÍSTICA CRIADOS COM SUCESSO!")
        print("="*60)
        
        # Estatísticas finais
        total_motoristas = Motorista.query.count()
        total_veiculos = Veiculo.query.count()
        total_os = OrdemServico.query.count()
        
        print(f"\n📊 Estatísticas:")
        print(f"   👨‍✈️  Motoristas: {total_motoristas}")
        print(f"   🚛 Veículos: {total_veiculos}")
        print(f"   📦 Ordens de Serviço: {total_os}")
        print(f"\n💡 Agora você pode acessar /logistica para gerenciar as OS!")
        print(f"\n📋 Fluxo de gerenciamento:")
        print(f"   1. Acesse /logistica para ver todas as OS")
        print(f"   2. Clique em 'Atribuir' nas OS com status PENDENTE")
        print(f"   3. Selecione um motorista e veículo")
        print(f"   4. A OS mudará para status AGENDADA")
        print(f"   5. O motorista pode acessar /app-motorista para iniciar a rota")

if __name__ == '__main__':
    criar_dados_logistica()
