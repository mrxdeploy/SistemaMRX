import sys
import os

# Adicionar o diretório pai ao PYTHONPATH
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.models import db, Usuario, Perfil
from app import create_app
from werkzeug.security import generate_password_hash
import logging

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_producao_user():
    app = create_app()
    with app.app_context():
        try:
            perfil = Perfil.query.filter_by(nome='Produção').first()
            if not perfil:
                logger.error("Perfil 'Produção' não encontrado. Execute create_producao_profile.py primeiro.")
                return

            email = 'producao@mrx.com'
            usuario = Usuario.query.filter_by(email=email).first()

            if usuario:
                logger.info(f"Usuário {email} já existe. Atualizando perfil...")
                usuario.perfil_id = perfil.id
                usuario.tipo = 'funcionario' # Ensure tipo is logical
                usuario.senha_hash = generate_password_hash('producao123')
            else:
                logger.info(f"Criando usuário {email}...")
                usuario = Usuario(
                    nome='Usuário Produção',
                    email=email,
                    senha_hash=generate_password_hash('producao123'),
                    tipo='funcionario',
                    perfil_id=perfil.id,
                    ativo=True
                )
                db.session.add(usuario)
            
            db.session.commit()
            logger.info(f"Usuário {email} configurado com sucesso! Senha: producao123")
            
        except Exception as e:
            logger.error(f"Erro ao criar usuário: {str(e)}")
            db.session.rollback()

if __name__ == "__main__":
    create_producao_user()
