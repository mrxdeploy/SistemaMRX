import os
from app import create_app
from app.models import db, Usuario, Vendedor, TipoLote, TipoLotePrecoEstrela, Fornecedor, FornecedorTipoLotePreco, Solicitacao, ItemSolicitacao, Lote, EntradaEstoque, Notificacao, Configuracao
import bcrypt

app = create_app()

def drop_all_tables():
    with app.app_context():
        print("Deletando todas as tabelas antigas...")
        db.drop_all()
        print("Tabelas antigas deletadas com sucesso!")

def create_all_tables():
    with app.app_context():
        print("Criando novo esquema de banco de dados...")
        db.create_all()
        print("Novo esquema criado com sucesso!")

def seed_initial_data():
    with app.app_context():
        print("Inserindo dados iniciais...")
        
        admin_email = os.getenv('ADMIN_EMAIL', 'admin@sistema.com')
        admin_password = os.getenv('ADMIN_PASSWORD', 'admin123')
        senha_hash = bcrypt.hashpw(admin_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        admin = Usuario.query.filter_by(email=admin_email).first()
        if not admin:
            admin = Usuario(
                nome='Administrador',
                email=admin_email,
                senha_hash=senha_hash,
                tipo='admin',
                ativo=True
            )
            db.session.add(admin)
            print(f"Usuário administrador criado: {admin_email}")
        else:
            print(f"Administrador já existe: {admin_email}")
        
        tipos_lote_padrao = [
            {"nome": "Placa Mãe", "codigo": "PM001", "descricao": "Placas mãe de computadores e notebooks"},
            {"nome": "Placa de Vídeo", "codigo": "PV001", "descricao": "Placas gráficas e GPUs"},
            {"nome": "Placa de Memória RAM", "codigo": "RAM001", "descricao": "Módulos de memória"},
            {"nome": "Placa de Rede", "codigo": "PR001", "descricao": "Placas de rede ethernet e wi-fi"},
            {"nome": "Placa de Som", "codigo": "PS001", "descricao": "Placas de áudio"},
            {"nome": "HD/SSD", "codigo": "HD001", "descricao": "Discos rígidos e SSDs"},
            {"nome": "Fonte de Alimentação", "codigo": "FA001", "descricao": "Fontes de energia"},
            {"nome": "Processador", "codigo": "PROC001", "descricao": "CPUs e processadores"},
            {"nome": "Cooler/Ventilador", "codigo": "COOL001", "descricao": "Sistemas de resfriamento"},
            {"nome": "Cabo de Dados", "codigo": "CD001", "descricao": "Cabos SATA, IDE, etc"},
            {"nome": "Conector USB", "codigo": "USB001", "descricao": "Conectores e portas USB"},
            {"nome": "Bateria", "codigo": "BAT001", "descricao": "Baterias de notebooks e dispositivos"},
            {"nome": "Teclado", "codigo": "TEC001", "descricao": "Teclados de computador"},
            {"nome": "Mouse", "codigo": "MOU001", "descricao": "Mouses e trackpads"},
            {"nome": "WebCam", "codigo": "WEB001", "descricao": "Câmeras web"},
            {"nome": "Placa WiFi/Bluetooth", "codigo": "WBT001", "descricao": "Placas de comunicação sem fio"},
            {"nome": "Placa de Expansão PCI", "codigo": "PCI001", "descricao": "Placas de expansão diversas"},
            {"nome": "Módulo Bluetooth", "codigo": "BT001", "descricao": "Módulos Bluetooth"},
            {"nome": "Display/Tela", "codigo": "DIS001", "descricao": "Telas LCD e LED"},
            {"nome": "Carregador", "codigo": "CAR001", "descricao": "Carregadores e adaptadores de energia"}
        ]
        
        tipos_criados = 0
        for tipo_data in tipos_lote_padrao:
            tipo_existente = TipoLote.query.filter_by(codigo=tipo_data['codigo']).first()
            if not tipo_existente:
                tipo_lote = TipoLote(
                    nome=tipo_data['nome'],
                    codigo=tipo_data['codigo'],
                    descricao=tipo_data['descricao'],
                    ativo=True
                )
                db.session.add(tipo_lote)
                tipos_criados += 1
        
        db.session.commit()
        print(f"{tipos_criados} tipos de lote criados (20 total disponíveis)")
        print("Dados iniciais inseridos com sucesso!")

if __name__ == '__main__':
    import sys
    
    print("=== MIGRAÇÃO DE BANCO DE DADOS ===")
    print("ATENÇÃO: Este script irá DELETAR todas as tabelas existentes!")
    
    force_migrate = os.getenv('FORCE_MIGRATE', 'false').lower() == 'true' or '--force' in sys.argv
    
    if force_migrate:
        print("Migração forçada ativada via FORCE_MIGRATE=true ou --force")
        drop_all_tables()
        create_all_tables()
        seed_initial_data()
        print("\n✅ Migração concluída com sucesso!")
        print("\n📋 Configuração:")
        print("1. DATABASE_URL configurado")
        print("2. JWT_SECRET_KEY configurado")
        print("3. Acesse o sistema com: admin@sistema.com / admin123")
    else:
        print("Para executar a migração, use:")
        print("  python migrate_database.py --force")
        print("  ou defina FORCE_MIGRATE=true no ambiente")
        print("\nMigração NÃO executada (modo de segurança).")
