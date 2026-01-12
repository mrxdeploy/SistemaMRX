import sys
import os

# Adicionar o diretório pai ao PYTHONPATH
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.models import db, Perfil
from app import create_app
import logging

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_producao_profile():
    app = create_app()
    with app.app_context():
        try:
            # Verificar se o perfil já existe
            perfil = Perfil.query.filter_by(nome='Produção').first()
            
            if perfil:
                logger.info("Perfil 'Produção' já existe.")
                # Atualizar permissões se necessário (opcional, aqui estamos apenas criando)
                perfil.descricao = 'Perfil para acesso ao módulo de produção e estoque ativo'
                perfil.permissoes = {
                    'producao': True,
                    'estoque_ativo': True
                }
            else:
                logger.info("Criando perfil 'Produção'...")
                perfil = Perfil(
                    nome='Produção',
                    descricao='Perfil para acesso ao módulo de produção e estoque ativo',
                    permissoes={
                        'producao': True,
                        'estoque_ativo': True
                    },
                    ativo=True
                )
                db.session.add(perfil)
            
            db.session.commit()
            logger.info("Perfil 'Produção' configurado com sucesso!")
            
        except Exception as e:
            logger.error(f"Erro ao criar perfil: {str(e)}")
            db.session.rollback()

if __name__ == "__main__":
    create_producao_profile()
