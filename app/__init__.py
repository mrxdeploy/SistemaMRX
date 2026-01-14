from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_socketio import SocketIO
from app.models import db
import os

socketio = SocketIO()

def create_app():
    app = Flask(__name__, 
                static_folder='static',
                static_url_path='/static',
                template_folder='templates')

    from datetime import timedelta

    app.config['SECRET_KEY'] = os.getenv('SESSION_SECRET', 'dev-secret-key')
    app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', os.getenv('SESSION_SECRET', 'jwt-secret-key'))
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=24)
    app.config['JWT_REFRESH_TOKEN_EXPIRES'] = timedelta(days=30)

    database_url = os.getenv('DATABASE_URL')
    # Forçar URL do Railway explicitamente
    if not database_url or 'helium' in database_url or 'localhost' in database_url:
        database_url = "postgresql://postgres:JLNFuhSFMbRaQlBAxuFynwIOMtLyalqt@centerbeam.proxy.rlwy.net:35419/railway"
    
    if database_url and database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
    app.config['UPLOAD_FOLDER'] = 'uploads'

    db.init_app(app)
    CORS(app)
    jwt = JWTManager(app)
    socketio.init_app(app, cors_allowed_origins="*")

    from flask import jsonify

    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return jsonify({
            'erro': 'Token expirado',
            'mensagem': 'Por favor, faça login novamente'
        }), 401

    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        return jsonify({
            'erro': 'Token inválido',
            'mensagem': 'Por favor, faça login novamente'
        }), 401

    @jwt.unauthorized_loader
    def unauthorized_callback(error):
        return jsonify({
            'erro': 'Token não fornecido',
            'mensagem': 'Por favor, faça login'
        }), 401

    @jwt.revoked_token_loader
    def revoked_token_callback(jwt_header, jwt_payload):
        return jsonify({
            'erro': 'Token revogado',
            'mensagem': 'Por favor, faça login novamente'
        }), 401

    with app.app_context():
        from app.routes import (auth, usuarios, notificacoes, vendedores,
                                fornecedores, tipos_lote, dashboard, solicitacao_lotes,
                                fornecedor_tipo_lote_classificacoes, fornecedor_tipo_lote_precos,
                                perfis, veiculos, motoristas, auditoria, ordens_compra,
                                ordens_servico, conferencias, estoque, separacao, wms, pages,
                                materiais_base, tabelas_preco, autorizacoes_preco, compras,
                                fornecedor_tabela_precos, metais, conquistas, assistente, scanner, rh, visitas,
                                producao, estoque_ativo)
        from app.routes import solicitacoes_new as solicitacoes
        from app.routes import lotes_new as lotes
        from app.routes import entradas_new as entradas

        app.register_blueprint(auth.bp)
        app.register_blueprint(usuarios.bp)
        app.register_blueprint(vendedores.bp)
        app.register_blueprint(notificacoes.bp)
        app.register_blueprint(dashboard.bp)
        app.register_blueprint(fornecedores.bp)
        app.register_blueprint(tipos_lote.bp)
        app.register_blueprint(solicitacoes.bp)
        app.register_blueprint(lotes.bp)
        app.register_blueprint(entradas.bp)
        app.register_blueprint(solicitacao_lotes.bp)
        app.register_blueprint(fornecedor_tipo_lote_classificacoes.bp)
        app.register_blueprint(fornecedor_tipo_lote_precos.bp)
        app.register_blueprint(perfis.bp)
        app.register_blueprint(veiculos.bp, url_prefix='/api/veiculos')
        app.register_blueprint(motoristas.bp, url_prefix='/api/motoristas')
        app.register_blueprint(auditoria.bp)
        app.register_blueprint(ordens_compra.bp)
        app.register_blueprint(ordens_servico.bp, url_prefix='/api/os')
        app.register_blueprint(conferencias.bp)
        app.register_blueprint(estoque.bp)
        app.register_blueprint(separacao.bp)
        app.register_blueprint(wms.bp)
        app.register_blueprint(materiais_base.bp)
        app.register_blueprint(tabelas_preco.bp)
        app.register_blueprint(autorizacoes_preco.bp)
        app.register_blueprint(compras.bp)
        app.register_blueprint(fornecedor_tabela_precos.bp)
        app.register_blueprint(pages.bp)
        app.register_blueprint(metais.bp)
        app.register_blueprint(conquistas.bp)
        app.register_blueprint(assistente.bp)
        app.register_blueprint(scanner.bp)
        app.register_blueprint(rh.bp)
        app.register_blueprint(visitas.bp)
        app.register_blueprint(producao.bp)
        app.register_blueprint(estoque_ativo.bp)

        def run_hr_migration():
            try:
                from sqlalchemy import text
                columns_to_add = [
                    ("foto_path", "VARCHAR(255)"),
                    ("foto_data", "BYTEA"),
                    ("foto_mimetype", "VARCHAR(50)"),
                    ("percentual_comissao", "NUMERIC(5,2) DEFAULT 0"),
                    ("telefone", "VARCHAR(20)"),
                    ("cpf", "VARCHAR(14)"),
                    ("data_atualizacao", "TIMESTAMP")
                ]
                
                with db.engine.connect() as conn:
                    for column_name, column_type in columns_to_add:
                        result = conn.execute(text(f"""
                            SELECT column_name 
                            FROM information_schema.columns 
                            WHERE table_name = 'usuarios' AND column_name = '{column_name}'
                        """))
                        
                        if result.fetchone() is None:
                            conn.execute(text(f"ALTER TABLE usuarios ADD COLUMN {column_name} {column_type}"))
                            conn.commit()
                            print(f"✓ Added column usuarios.{column_name}")
            except Exception as e:
                print(f"Migration check: {e}")

        run_hr_migration()
        
        def run_profiles_migration():
            try:
                from app.models import Perfil
                
                # Check / Create 'Producao'
                perfil_nome = 'Producao'
                perfil = Perfil.query.filter_by(nome=perfil_nome).first()
                if not perfil:
                    # Tentar achar com nome antigo
                    perfil_old = Perfil.query.filter_by(nome='Produção').first()
                    if perfil_old:
                        print(f"Migrating profile 'Produção' to '{perfil_nome}'...")
                        perfil_old.nome = perfil_nome
                        perfil_old.ativo = True
                        db.session.commit()
                    else:
                        print(f"Creating profile '{perfil_nome}'...")
                        novo_perfil = Perfil(
                            nome=perfil_nome,
                            descricao='Perfil para equipe de produção com acesso a estoque e separação',
                            permissoes={'visualizar_producao': True}, # Basic flag
                            ativo=True
                        )
                        db.session.add(novo_perfil)
                        db.session.commit()
                else:
                    if not perfil.ativo:
                        perfil.ativo = True
                        db.session.commit()
                        print(f"Activated existing profile '{perfil_nome}'.")
                
                # Check / Create 'Gestor'
                gestor_nome = 'Gestor'
                perfil_gestor = Perfil.query.filter_by(nome=gestor_nome).first()
                if not perfil_gestor:
                    print(f"Creating profile '{gestor_nome}'...")
                    novo_gestor = Perfil(
                        nome=gestor_nome,
                        descricao='Perfil de gestão com acesso a compras, fornecedores, estoque ativo e WMS',
                        permissoes={'visualizar_producao': True, 'visualizar_estoque': True},
                        ativo=True
                    )
                    db.session.add(novo_gestor)
                    db.session.commit()
                else:
                    if not perfil_gestor.ativo:
                        perfil_gestor.ativo = True
                        db.session.commit()
                        print(f"Activated existing profile '{gestor_nome}'.")

            except Exception as e:
                print(f"Profiles migration error: {e}")

        run_profiles_migration()
        
        def run_producao_migration():
            try:
                from sqlalchemy import text
                columns_to_add = [
                    ("lotes_ids", "JSONB DEFAULT '[]'"),
                    ("fornecedores_ids", "JSONB DEFAULT '[]'"),
                    ("outros_origens", "JSONB DEFAULT '[]'")
                ]
                
                with db.engine.connect() as conn:
                    result = conn.execute(text("""
                        SELECT table_name FROM information_schema.tables 
                        WHERE table_name = 'ordens_producao'
                    """))
                    
                    if result.fetchone() is not None:
                        for column_name, column_type in columns_to_add:
                            result = conn.execute(text(f"""
                                SELECT column_name 
                                FROM information_schema.columns 
                                WHERE table_name = 'ordens_producao' AND column_name = '{column_name}'
                            """))
                            
                            if result.fetchone() is None:
                                conn.execute(text(f"ALTER TABLE ordens_producao ADD COLUMN {column_name} {column_type}"))
                                conn.commit()
                                print(f"✓ Added column ordens_producao.{column_name}")
            except Exception as e:
                print(f"Producao migration check: {e}")
        
        run_producao_migration()
        db.create_all()

        # Inicializar tabelas de preço
        from app.models import TabelaPreco, Perfil, TipoLote
        tabelas_existentes = TabelaPreco.query.all()
        if len(tabelas_existentes) < 3:
            niveis_necessarios = {1, 2, 3}
            niveis_existentes = {t.nivel_estrelas for t in tabelas_existentes}
            niveis_faltantes = niveis_necessarios - niveis_existentes

            for nivel in sorted(niveis_faltantes):
                nome_estrelas = "Estrela" if nivel == 1 else "Estrelas"
                tabela = TabelaPreco(
                    nome=f'{nivel} {nome_estrelas}',
                    nivel_estrelas=nivel,
                    ativo=True
                )
                db.session.add(tabela)

            db.session.commit()
            print(f"✓ Inicializadas {len(niveis_faltantes)} tabela(s) de preço")

        # Inicializar tipo de lote padrão
        tipo_lote_padrao = TipoLote.query.first()
        if not tipo_lote_padrao:
            tipo_lote_padrao = TipoLote(
                nome='Material Eletrônico',
                descricao='Tipo de lote padrão para materiais eletrônicos'
            )
            db.session.add(tipo_lote_padrao)
            db.session.commit()
            print("✓ Inicializado tipo de lote padrão")

        from app.auth import criar_admin_padrao
        criar_admin_padrao()

        from app.models import ClassificacaoGrade
        classificacoes_high_grade = [
            'SUCATA PROCESSADOR CERAMICO A',
            'SUCATA PROCESSADOR CERAMICO B',
            'SUCATA PROCESSADOR CERAMICO C',
            'SUCATA PROCESSADOR SLOT',
            'SUCATA PROCESSADOR PLASTICO A',
            'SUCATA PROCESSADOR PLASTICO B',
            'SUCATA PROCESSADOR CHAPA A',
            'SUCATA PROCESSADOR CHAPA B',
            'SUCATA MEMORIA DOURADA',
            'SUCATA MEMORIA PRATA',
            'SUCATA PLACA DOURADA A',
            'SUCATA PLACA DOURADA B',
            'SUCATA PLACA CENTRAL A',
            'SUCATA PLACA CENTRAL B',
            'SUCATA PLACA CENTRAL S',
            'SUCATA PLACA TAPETE A',
            'SUCATA PLACA TAPETE B',
            'SUCATA PLACA TAPETE C',
            'SUCATA PLACA HD',
            'SUCATA PLACA DE CELULAR',
            'SUCATA APARELHO CELULAR A',
            'SUCATA PLACA NOTEBOOK A',
            'SUCATA PLACA NOTEBOOK B',
            'SUCATA PLACA TABLET',
            'SUCATA PLACA DRIVE',
            'SUCATA METAL PRECIOSO',
            'SUCATA PLACA LEVE A'
        ]
        nomes_existentes = {c.nome for c in ClassificacaoGrade.query.filter_by(categoria='HIGH_GRADE').all()}
        nomes_faltantes = [n for n in classificacoes_high_grade if n not in nomes_existentes]
        if nomes_faltantes:
            for nome in nomes_faltantes:
                classificacao = ClassificacaoGrade(
                    nome=nome,
                    categoria='HIGH_GRADE',
                    ativo=True
                )
                db.session.add(classificacao)
            db.session.commit()
            print(f"✓ Adicionadas {len(nomes_faltantes)} classificações HIGH GRADE faltantes")

    return app