#!/usr/bin/env python3
"""
Script para popular o banco de dados com dados de teste
para validar os gráficos do dashboard
"""

from app import create_app
from app.models import db, Fornecedor, TipoLote, Solicitacao, ItemSolicitacao, Lote, Usuario
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import random

app = create_app()

def popular_banco():
    """Função principal para popular o banco"""
    print("=" * 60)
    print("🚀 INICIANDO POPULAÇÃO DO BANCO DE DADOS")
    print("=" * 60)
    
    with app.app_context():
        try:
            # Limpar dados anteriores
            print("🗑️  Limpando dados de teste anteriores...")
            
            # Deletar na ordem correta (respeitando foreign keys)
            ItemSolicitacao.query.delete()
            Lote.query.delete()
            Solicitacao.query.delete()
            TipoLote.query.delete()
            
            # Deletar fornecedores de teste por CNPJ
            cnpjs_teste = [
                "11111111000101", "22222222000102", "33333333000103", "44444444000104",
                "55555555000105", "66666666000106", "77777777000107", "88888888000108",
                "99999999000109", "10101010000110"
            ]
            fornecedores_teste = Fornecedor.query.filter(Fornecedor.cnpj.in_(cnpjs_teste)).all()
            for f in fornecedores_teste:
                db.session.delete(f)
            
            db.session.commit()
            print("✅ Dados de teste anteriores removidos")
            
            # Criar fornecedores
            print("\n👥 Criando fornecedores...")
            
            fornecedores_data = [
                {"nome": "Eletrônica Silva LTDA", "cnpj": "11111111000101", "telefone": "(11) 98888-1111"},
                {"nome": "Tech Components BR", "cnpj": "22222222000102", "telefone": "(11) 98888-2222"},
                {"nome": "Placas e Componentes S/A", "cnpj": "33333333000103", "telefone": "(21) 98888-3333"},
                {"nome": "Reciclagem Digital LTDA", "cnpj": "44444444000104", "telefone": "(11) 98888-4444"},
                {"nome": "MRX Parceiros EIRELI", "cnpj": "55555555000105", "telefone": "(19) 98888-5555"},
                {"nome": "Componentes Premium", "cnpj": "66666666000106", "telefone": "(11) 98888-6666"},
                {"nome": "Eletrônicos ABC", "cnpj": "77777777000107", "telefone": "(48) 98888-7777"},
                {"nome": "Tech Supply Brasil", "cnpj": "88888888000108", "telefone": "(11) 98888-8888"},
                {"nome": "Placas Industriais", "cnpj": "99999999000109", "telefone": "(11) 98888-9999"},
                {"nome": "ReTech Componentes", "cnpj": "10101010000110", "telefone": "(11) 98888-0000"},
            ]
            
            fornecedores = []
            for data in fornecedores_data:
                fornecedor = Fornecedor(
                    nome=data["nome"],
                    cnpj=data["cnpj"],
                    telefone=data["telefone"],
                    email=f"{data['nome'].lower().replace(' ', '').replace('/', '')}@email.com",
                    ativo=True
                )
                db.session.add(fornecedor)
                fornecedores.append(fornecedor)
            
            db.session.commit()
            print(f"✅ {len(fornecedores)} fornecedores criados")
            
            # Criar tipos de lote
            print("\n📦 Criando tipos de lote...")
            
            tipos_data = [
                {"nome": "Placa Mãe Desktop", "codigo": "TL001", "classificacao": "media", "descricao": "Placas mãe de computadores desktop"},
                {"nome": "Placa Mãe Notebook", "codigo": "TL002", "classificacao": "leve", "descricao": "Placas mãe de notebooks"},
                {"nome": "Placa de Vídeo", "codigo": "TL003", "classificacao": "pesada", "descricao": "Placas de vídeo diversas"},
                {"nome": "Fonte de Alimentação", "codigo": "TL004", "classificacao": "pesada", "descricao": "Fontes ATX e similares"},
                {"nome": "Memória RAM", "codigo": "TL005", "classificacao": "leve", "descricao": "Módulos de memória RAM"},
                {"nome": "HD/SSD", "codigo": "TL006", "classificacao": "media", "descricao": "Discos rígidos e SSDs"},
                {"nome": "Placas de Rede", "codigo": "TL007", "classificacao": "leve", "descricao": "Placas de rede ethernet/wifi"},
                {"nome": "Processadores", "codigo": "TL008", "classificacao": "media", "descricao": "CPUs diversas"},
            ]
            
            tipos_lote = []
            for data in tipos_data:
                tipo = TipoLote(
                    nome=data["nome"],
                    codigo=data["codigo"],
                    classificacao=data["classificacao"],
                    descricao=data["descricao"],
                    ativo=True
                )
                db.session.add(tipo)
                tipos_lote.append(tipo)
            
            db.session.commit()
            print(f"✅ {len(tipos_lote)} tipos de lote criados")
            
            # Criar solicitações e lotes
            print("\n📋 Criando solicitações e lotes...")
            
            # Buscar usuário comprador para criar solicitações
            usuario_comprador = Usuario.query.filter_by(email='comprador@teste.com').first()
            if not usuario_comprador:
                # Usar o admin se não existir comprador
                usuario_comprador = Usuario.query.filter_by(email='admin@teste.com').first()
            
            usuario_admin = Usuario.query.filter_by(email='admin@teste.com').first()
            
            if not usuario_comprador or not usuario_admin:
                print("❌ Erro: Usuários necessários não encontrados")
                return
            
            hoje = datetime.now()
            
            total_solicitacoes = 0
            total_lotes = 0
            total_aprovadas = 0
            
            # Pré-calcular quantidade de solicitações por mês para garantir mínimo de 30 aprovadas
            # Distribuir 8 solicitações por mês (48 total), sendo ~5 aprovadas por mês (30 total garantido)
            solicitacoes_por_mes = 8
            aprovadas_por_mes = 5
            
            # Criar solicitações nos últimos 6 meses
            for mes_offset in range(5, -1, -1):
                # Data base para este mês
                data_mes = hoje - relativedelta(months=mes_offset)
                
                # Criar lista de status para este mês (5 aprovadas, 2 pendentes, 1 rejeitada)
                status_mes = ['aprovada'] * aprovadas_por_mes + ['pendente'] * 2 + ['rejeitada'] * 1
                random.shuffle(status_mes)
                
                for i in range(solicitacoes_por_mes):
                    # Data aleatória dentro do mês
                    dia = random.randint(1, 28)
                    data_envio = datetime(data_mes.year, data_mes.month, dia, 
                                         random.randint(8, 18), random.randint(0, 59))
                    
                    # Selecionar fornecedor aleatório
                    fornecedor = random.choice(fornecedores)
                    
                    # Status determinístico para este mês
                    status = status_mes[i]
                    
                    solicitacao = Solicitacao(
                        funcionario_id=usuario_comprador.id,
                        fornecedor_id=fornecedor.id,
                        tipo_retirada=random.choice(['buscar', 'entregar']),
                        status=status,
                        observacoes=f"Solicitação de teste - {data_envio.strftime('%B/%Y')}",
                        data_envio=data_envio,
                        data_confirmacao=data_envio + timedelta(days=random.randint(1, 3)) if status in ['aprovada', 'rejeitada'] else None,
                        admin_id=usuario_admin.id if status in ['aprovada', 'rejeitada'] else None,
                        endereco_completo=f"Rua Teste, {random.randint(100, 999)}, São Paulo - SP"
                    )
                    db.session.add(solicitacao)
                    db.session.flush()  # Para obter o ID
                    
                    # Criar 1-3 itens por solicitação
                    num_itens = random.randint(1, 3)
                    
                    # Mapeamento de classificação (TipoLote usa feminino, ItemSolicitacao usa masculino)
                    class_map = {"media": "medio", "pesada": "pesado", "leve": "leve"}
                    
                    for _ in range(num_itens):
                        tipo_lote = random.choice(tipos_lote)
                        peso_kg = round(random.uniform(5.0, 50.0), 2)
                        estrelas = random.randint(1, 5)
                        
                        # Converter classificação de feminino para masculino
                        classificacao_item = class_map.get(tipo_lote.classificacao, tipo_lote.classificacao)
                        
                        item = ItemSolicitacao(
                            solicitacao_id=solicitacao.id,
                            tipo_lote_id=tipo_lote.id,
                            peso_kg=peso_kg,
                            estrelas_final=estrelas,
                            classificacao=classificacao_item,
                            observacoes=f"{tipo_lote.nome} - Lote {random.randint(1, 100)}",
                            valor_calculado=round(peso_kg * random.uniform(10.0, 50.0), 2)
                        )
                        db.session.add(item)
                    
                    total_solicitacoes += 1
                    if status == 'aprovada':
                        total_aprovadas += 1
                    
                    # Se aprovada, criar lote
                    if status == 'aprovada':
                        tipo_lote = random.choice(tipos_lote)
                        peso_total = round(random.uniform(50.0, 500.0), 2)
                        valor_total = round(peso_total * random.uniform(15.0, 60.0), 2)
                        data_criacao_lote = data_envio + timedelta(days=random.randint(1, 5))
                        
                        lote = Lote(
                            numero_lote=f"LT{data_mes.year}{data_mes.month:02d}{random.randint(1000, 9999)}",
                            fornecedor_id=fornecedor.id,
                            tipo_lote_id=tipo_lote.id,
                            solicitacao_origem_id=solicitacao.id,
                            peso_total_kg=peso_total,
                            valor_total=valor_total,
                            status='aprovado',
                            data_criacao=data_criacao_lote,
                            data_aprovacao=data_criacao_lote + timedelta(hours=random.randint(1, 24)),
                            observacoes=f"Lote automático - {tipo_lote.nome}"
                        )
                        db.session.add(lote)
                        total_lotes += 1
            
            db.session.commit()
            print(f"✅ {total_solicitacoes} solicitações criadas")
            print(f"✅ {total_lotes} lotes criados")
            
            print("\n" + "=" * 60)
            print("✅ BANCO DE DADOS POPULADO COM SUCESSO!")
            print("=" * 60)
            print("\n📊 Agora você pode acessar o dashboard e ver os gráficos")
            print("   com dados realistas distribuídos nos últimos 6 meses.\n")
            
        except Exception as e:
            db.session.rollback()
            print(f"\n❌ Erro ao popular banco: {e}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    popular_banco()
