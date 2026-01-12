import os
os.environ.setdefault('DATABASE_URL', os.environ.get('DATABASE_URL', ''))

from app import create_app
from app.models import db, Usuario, TipoLote
import bcrypt

def recreate_database():
    print("=" * 60)
    print("RECRIANDO ESTRUTURA DO BANCO DE DADOS")
    print("=" * 60)
    
    app = create_app()
    
    with app.app_context():
        print("\n🗑️  Removendo todas as tabelas antigas...")
        db.drop_all()
        
        print("🆕 Criando nova estrutura de tabelas...")
        db.create_all()
        
        print("👤 Criando usuário admin...")
        senha = bcrypt.hashpw('admin123'.encode('utf-8'), bcrypt.gensalt())
        admin = Usuario(
            nome='Administrador',
            email='admin@sistema.com',
            senha_hash=senha.decode('utf-8'),
            tipo='admin'
        )
        db.session.add(admin)
        
        print("📦 Criando tipos de lote padrão...")
        tipos_padrao = [
            ('Placa Leve Tipo A', 'Placas eletrônicas leves categoria A', 'PL-A'),
            ('Placa Pesada Tipo A', 'Placas eletrônicas pesadas categoria A', 'PP-A'),
            ('Placa Média Tipo A', 'Placas eletrônicas médias categoria A', 'PM-A'),
            ('Placa Leve Tipo B', 'Placas eletrônicas leves categoria B', 'PL-B'),
            ('Placa Pesada Tipo B', 'Placas eletrônicas pesadas categoria B', 'PP-B'),
            ('Placa Média Tipo B', 'Placas eletrônicas médias categoria B', 'PM-B'),
            ('Processadores', 'Processadores de computador', 'PROC'),
            ('Memórias RAM', 'Módulos de memória RAM', 'RAM'),
            ('Placas de Vídeo', 'Placas de vídeo/GPU', 'GPU'),
            ('Placas-Mãe', 'Placas-mãe de computadores', 'MB'),
            ('Fonte de Alimentação', 'Fontes de alimentação ATX', 'PSU'),
            ('Discos Rígidos', 'HD e SSD', 'HDD'),
            ('Cabos e Conectores', 'Cabos e conectores diversos', 'CABO'),
            ('Baterias', 'Baterias de notebook e celular', 'BAT'),
            ('Teclados', 'Teclados de computador', 'KBD'),
            ('Mouses', 'Mouses de computador', 'MSE'),
            ('Monitores', 'Monitores e displays', 'MON'),
            ('Notebooks', 'Notebooks completos', 'NB'),
            ('Celulares', 'Telefones celulares', 'CEL'),
            ('Tablets', 'Tablets e iPads', 'TAB'),
        ]
        
        for nome, descricao, codigo in tipos_padrao:
            tipo = TipoLote(nome=nome, descricao=descricao, codigo=codigo)
            db.session.add(tipo)
        
        db.session.commit()
        
        print("\n✅ Migração concluída com sucesso!")
        print()
        print("📊 Resumo:")
        print(f"   - Usuários admin: {Usuario.query.filter_by(tipo='admin').count()}")
        print(f"   - Tipos de lote: {TipoLote.query.count()}")
        print()
        print("🔐 Credenciais de acesso:")
        print("   Email: admin@sistema.com")
        print("   Senha: admin123")
        print()
        print("⚠️  IMPORTANTE: Altere a senha padrão em produção!")
        print("=" * 60)

if __name__ == '__main__':
    recreate_database()
