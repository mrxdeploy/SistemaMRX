#!/usr/bin/env python3
"""
Script de População Completa do Sistema MRX
============================================
Popula o banco de dados com dados realistas e interconectados para demonstração.

Estrutura de dados:
- Vendedores
- Materiais Base (leve, médio, pesado)
- Preços de materiais por estrelas (1★, 2★, 3★)
- Tipos de Lote
- Usuários de diferentes perfis
- Fornecedores com classificações por estrelas
- Solicitações vinculadas a fornecedores
- Ordens de Compra
- Veículos e Motoristas
- Ordens de Serviço com motoristas atribuídos
- Conferências de Recebimento com dados completos
- Lotes com status variados
- Entradas de Estoque

Autor: MRX Systems
Data: 23/11/2025
"""

import sys
import os
from datetime import datetime, timedelta
import random

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import (
    Vendedor, MaterialBase, TabelaPreco, TabelaPrecoItem, TipoLote,
    Usuario, Perfil, Fornecedor, FornecedorTipoLote, FornecedorClassificacaoEstrela,
    FornecedorTipoLotePreco, FornecedorTipoLoteClassificacao,
    Solicitacao, ItemSolicitacao, OrdemCompra, Veiculo, Motorista,
    OrdemServico, ConferenciaRecebimento, Lote, EntradaEstoque, Notificacao
)
from app.auth import hash_senha


def limpar_dados_antigos():
    """Remove todos os dados gerados anteriormente, preservando os essenciais"""
    print("\n🗑️  Limpando dados antigos...")
    
    try:
        # Importar AuditoriaLog
        from app.models import AuditoriaLog, AuditoriaOC
        
        # Deletar logs de auditoria ANTES de deletar usuários
        db.session.query(AuditoriaLog).delete()
        db.session.query(AuditoriaOC).delete()
        
        # ORDEM CORRETA: deletar filhos antes dos pais
        # 1. Entradas de estoque (referencia lotes)
        db.session.query(EntradaEstoque).delete()
        
        # 2. Lotes (referencia conferencias, OS, OC, solicitacao, fornecedor, tipo_lote)
        db.session.query(Lote).delete()
        
        # 3. Conferências (referencia OS e OC)
        db.session.query(ConferenciaRecebimento).delete()
        
        # 4. Ordens de Serviço (referencia OC, motorista, veiculo)
        db.session.query(OrdemServico).delete()
        
        # 5. Ordens de Compra (referencia solicitacao e fornecedor)
        db.session.query(OrdemCompra).delete()
        
        # 6. Itens de Solicitação (referencia solicitacao)
        db.session.query(ItemSolicitacao).delete()
        
        # 7. Solicitações (referencia fornecedor e usuario)
        db.session.query(Solicitacao).delete()
        
        # 8. Motoristas (referencia usuario e veiculo)
        db.session.query(Motorista).delete()
        
        # 9. Veículos
        db.session.query(Veiculo).delete()
        
        # 10. Relações de fornecedores
        db.session.query(FornecedorTipoLotePreco).delete()
        db.session.query(FornecedorTipoLoteClassificacao).delete()
        db.session.query(FornecedorClassificacaoEstrela).delete()
        db.session.query(FornecedorTipoLote).delete()
        
        # 11. Fornecedores
        db.session.query(Fornecedor).delete()
        
        # 12. Vendedores
        db.session.query(Vendedor).delete()
        
        # 13. Preços e materiais
        db.session.query(TabelaPrecoItem).delete()
        db.session.query(MaterialBase).delete()
        
        # 14. Notificações
        db.session.query(Notificacao).delete()
        
        # 15. Manter apenas admin e tipos de lote padrão
        db.session.query(Usuario).filter(Usuario.email != 'admin@sistema.com').delete()
        db.session.query(TipoLote).filter(TipoLote.id != 1).delete()
        
        db.session.commit()
        print("✅ Dados antigos removidos com sucesso!")
    except Exception as e:
        db.session.rollback()
        print(f"❌ Erro ao limpar dados: {str(e)}")
        raise


def criar_vendedores():
    """Cria vendedores para os fornecedores"""
    print("\n👨‍💼 Criando vendedores...")
    
    vendedores_data = [
        {
            'nome': 'Carlos Eduardo Silva',
            'email': 'carlos.silva@vendas.com',
            'telefone': '(11) 98765-4321',
            'cpf': '123.456.789-01'
        },
        {
            'nome': 'Marina Santos Costa',
            'email': 'marina.costa@comercial.com',
            'telefone': '(11) 97654-3210',
            'cpf': '234.567.890-12'
        },
        {
            'nome': 'Roberto Alves Lima',
            'email': 'roberto.lima@negocios.com',
            'telefone': '(11) 96543-2109',
            'cpf': '345.678.901-23'
        },
        {
            'nome': 'Juliana Ferreira',
            'email': 'juliana.ferreira@parceiros.com',
            'telefone': '(11) 95432-1098',
            'cpf': '456.789.012-34'
        },
        {
            'nome': 'Fernando Oliveira',
            'email': 'fernando.oliveira@representante.com',
            'telefone': '(11) 94321-0987',
            'cpf': '567.890.123-45'
        },
        {
            'nome': 'Patricia Souza',
            'email': 'patricia.souza@vendedor.com',
            'telefone': '(11) 93210-9876',
            'cpf': '678.901.234-56'
        }
    ]
    
    vendedores = []
    for data in vendedores_data:
        vendedor = Vendedor(**data)
        db.session.add(vendedor)
        vendedores.append(vendedor)
    
    db.session.commit()
    print(f"✅ {len(vendedores)} vendedores criados!")
    return vendedores


def criar_materiais_base():
    """Cria materiais base com classificações (leve, médio, pesado)"""
    print("\n📦 Criando materiais base...")
    
    materiais_data = [
        # Materiais LEVES
        {'codigo': 'MAT-001', 'nome': 'Placas de Circuito (PCB) Limpas', 'classificacao': 'leve', 
         'descricao': 'Placas de circuito impresso sem componentes, alta pureza de cobre'},
        {'codigo': 'MAT-002', 'nome': 'Conectores e Cabos', 'classificacao': 'leve',
         'descricao': 'Conectores diversos, cabos de rede, cabos USB limpos'},
        {'codigo': 'MAT-003', 'nome': 'Alumínio de Dissipadores', 'classificacao': 'leve',
         'descricao': 'Dissipadores de calor de alumínio separados'},
        {'codigo': 'MAT-004', 'nome': 'Fios de Cobre', 'classificacao': 'leve',
         'descricao': 'Fios e cabos de cobre puro, sem isolamento'},
        
        # Materiais MÉDIOS
        {'codigo': 'MAT-005', 'nome': 'Placas-Mãe Completas', 'classificacao': 'medio',
         'descricao': 'Placas-mãe de computadores com componentes integrados'},
        {'codigo': 'MAT-006', 'nome': 'Placas de Vídeo', 'classificacao': 'medio',
         'descricao': 'Placas de vídeo com chips GPU e memória'},
        {'codigo': 'MAT-007', 'nome': 'Fontes de Alimentação', 'classificacao': 'medio',
         'descricao': 'Fontes de computadores desmontadas'},
        {'codigo': 'MAT-008', 'nome': 'Processadores (CPU)', 'classificacao': 'medio',
         'descricao': 'Processadores Intel e AMD, diversas gerações'},
        {'codigo': 'MAT-009', 'nome': 'Memórias RAM', 'classificacao': 'medio',
         'descricao': 'Memórias RAM DDR3, DDR4, diversos modelos'},
        {'codigo': 'MAT-010', 'nome': 'HD e SSD', 'classificacao': 'medio',
         'descricao': 'Discos rígidos e SSDs diversos'},
        
        # Materiais PESADOS
        {'codigo': 'MAT-011', 'nome': 'Sucata Mista de Informática', 'classificacao': 'pesado',
         'descricao': 'Mix de componentes eletrônicos variados'},
        {'codigo': 'MAT-012', 'nome': 'Gabinetes e Carcaças', 'classificacao': 'pesado',
         'descricao': 'Gabinetes metálicos de computadores e servidores'},
        {'codigo': 'MAT-013', 'nome': 'Impressoras e Copiadoras', 'classificacao': 'pesado',
         'descricao': 'Impressoras laser, jato de tinta e copiadoras'},
        {'codigo': 'MAT-014', 'nome': 'Monitores e TVs', 'classificacao': 'pesado',
         'descricao': 'Monitores LCD/LED e televisores para desmonte'},
        {'codigo': 'MAT-015', 'nome': 'Eletrodomésticos', 'classificacao': 'pesado',
         'descricao': 'Micro-ondas, liquidificadores e outros eletrodomésticos'}
    ]
    
    materiais = []
    for data in materiais_data:
        material = MaterialBase(**data)
        db.session.add(material)
        materiais.append(material)
    
    db.session.commit()
    print(f"✅ {len(materiais)} materiais base criados!")
    return materiais


def criar_precos_materiais(materiais):
    """Cria preços dos materiais para as 3 tabelas de preço (1★, 2★, 3★)"""
    print("\n💰 Criando preços dos materiais...")
    
    tabelas = db.session.query(TabelaPreco).order_by(TabelaPreco.nivel_estrelas).all()
    
    # Preços base por classificação e estrela
    precos_base = {
        'leve': {1: 12.50, 2: 15.00, 3: 18.50},
        'medio': {1: 8.00, 2: 10.50, 3: 13.00},
        'pesado': {1: 3.50, 2: 5.00, 3: 6.50}
    }
    
    total_precos = 0
    for material in materiais:
        for tabela in tabelas:
            preco_base = precos_base[material.classificacao][tabela.nivel_estrelas]
            # Adicionar variação de ±15%
            variacao = random.uniform(-0.15, 0.15)
            preco_final = round(preco_base * (1 + variacao), 2)
            
            preco_item = TabelaPrecoItem(
                tabela_preco_id=tabela.id,
                material_id=material.id,
                preco_por_kg=preco_final
            )
            db.session.add(preco_item)
            total_precos += 1
    
    db.session.commit()
    print(f"✅ {total_precos} preços de materiais criados!")


def criar_tipos_lote():
    """Cria tipos de lote adicionais com classificações para popular os gráficos"""
    print("\n📋 Criando tipos de lote...")
    
    tipos_data = [
        {'nome': 'Material de Informática', 'codigo': 'INF', 'descricao': 'Equipamentos e componentes de informática', 'classificacao': 'media'},
        {'nome': 'Material de Telecomunicações', 'codigo': 'TEL', 'descricao': 'Equipamentos de telecomunicações', 'classificacao': 'leve'},
        {'nome': 'Linha Branca', 'codigo': 'LBR', 'descricao': 'Eletrodomésticos de linha branca', 'classificacao': 'pesada'},
        {'nome': 'Áudio e Vídeo', 'codigo': 'AVD', 'descricao': 'Equipamentos de áudio e vídeo', 'classificacao': 'media'},
        {'nome': 'Material Industrial', 'codigo': 'IND', 'descricao': 'Equipamentos e materiais industriais', 'classificacao': 'pesada'}
    ]
    
    tipos = []
    for data in tipos_data:
        tipo = TipoLote(**data)
        db.session.add(tipo)
        tipos.append(tipo)
    
    db.session.commit()
    print(f"✅ {len(tipos)} tipos de lote criados!")
    
    # Atualizar tipo de lote padrão (id=1) com classificação
    tipo_padrao = db.session.query(TipoLote).filter_by(id=1).first()
    if tipo_padrao and not tipo_padrao.classificacao:
        tipo_padrao.classificacao = 'leve'
        db.session.commit()
        print("✅ Tipo de lote padrão atualizado com classificação 'leve'")
    
    # Retornar todos os tipos (incluindo o padrão)
    return db.session.query(TipoLote).all()


def criar_usuarios():
    """Cria usuários de diferentes perfis"""
    print("\n👥 Criando usuários...")
    
    perfis = {p.nome: p for p in db.session.query(Perfil).all()}
    admin = db.session.query(Usuario).filter_by(email='admin@sistema.com').first()
    
    usuarios_data = [
        {
            'nome': 'João Comprador',
            'email': 'joao.comprador@mrx.com',
            'senha': 'senha123',
            'tipo': 'funcionario',
            'perfil_id': perfis['Comprador (PJ)'].id
        },
        {
            'nome': 'Maria Conferente',
            'email': 'maria.conferente@mrx.com',
            'senha': 'senha123',
            'tipo': 'funcionario',
            'perfil_id': perfis['Conferente / Estoque'].id
        },
        {
            'nome': 'Pedro Separador',
            'email': 'pedro.separador@mrx.com',
            'senha': 'senha123',
            'tipo': 'funcionario',
            'perfil_id': perfis['Separação'].id
        },
        {
            'nome': 'Ana Financeiro',
            'email': 'ana.financeiro@mrx.com',
            'senha': 'senha123',
            'tipo': 'funcionario',
            'perfil_id': perfis['Financeiro'].id
        },
        {
            'nome': 'Carlos Auditoria',
            'email': 'carlos.auditoria@mrx.com',
            'senha': 'senha123',
            'tipo': 'funcionario',
            'perfil_id': perfis['Auditoria / BI'].id
        },
        {
            'nome': 'Lucas Motorista',
            'email': 'lucas.motorista@mrx.com',
            'senha': 'senha123',
            'tipo': 'funcionario',
            'perfil_id': perfis['Motorista'].id
        },
        {
            'nome': 'Rafael Motorista',
            'email': 'rafael.motorista@mrx.com',
            'senha': 'senha123',
            'tipo': 'funcionario',
            'perfil_id': perfis['Motorista'].id
        },
        {
            'nome': 'Fernanda Compradora',
            'email': 'fernanda.compradora@mrx.com',
            'senha': 'senha123',
            'tipo': 'funcionario',
            'perfil_id': perfis['Comprador (PJ)'].id
        }
    ]
    
    usuarios = {'admin': admin}
    for data in usuarios_data:
        senha = data.pop('senha')
        usuario = Usuario(**data, senha_hash=hash_senha(senha), criado_por=admin.id)
        db.session.add(usuario)
        usuarios[data['email'].split('@')[0].replace('.', '_')] = usuario
    
    db.session.commit()
    print(f"✅ {len(usuarios_data)} usuários criados!")
    return usuarios


def criar_fornecedores(vendedores, usuarios, tipos_lote):
    """Cria fornecedores com diferentes classificações de estrelas"""
    print("\n🏢 Criando fornecedores...")
    
    tabelas_preco = {1: 1, 2: 2, 3: 3}  # ID das tabelas por estrelas
    admin = usuarios['admin']
    comprador = usuarios['joao_comprador']
    
    # Cidades da região de SP
    cidades_sp = [
        ('São Paulo', 'SP', '01000-000', 'Centro', -23.5505, -46.6333),
        ('Guarulhos', 'SP', '07000-000', 'Centro', -23.4543, -46.5339),
        ('Campinas', 'SP', '13000-000', 'Cambuí', -22.9099, -47.0626),
        ('São Bernardo do Campo', 'SP', '09700-000', 'Centro', -23.6914, -46.5646),
        ('Santo André', 'SP', '09000-000', 'Centro', -23.6633, -46.5342),
        ('Osasco', 'SP', '06000-000', 'Centro', -23.5329, -46.7919),
        ('Sorocaba', 'SP', '18000-000', 'Centro', -23.5015, -47.4526),
        ('Ribeirão Preto', 'SP', '14000-000', 'Centro', -21.1704, -47.8103),
        ('São José dos Campos', 'SP', '12200-000', 'Centro', -23.1791, -45.8872),
        ('Mogi das Cruzes', 'SP', '08700-000', 'Centro', -23.5227, -46.1882)
    ]
    
    fornecedores_data = [
        {
            'nome': 'Tech Recycling Ltda',
            'nome_social': 'Tech Recycling',
            'cnpj': '12.345.678/0001-90',
            'telefone': '(11) 3456-7890',
            'email': 'contato@techrecycling.com.br',
            'tabela_preco_id': tabelas_preco[3],
            'banco': 'Banco do Brasil',
            'agencia': '1234-5',
            'conta_bancaria': '12345-6',
            'chave_pix': '12.345.678/0001-90'
        },
        {
            'nome': 'GreenTech Soluções Ambientais',
            'nome_social': 'GreenTech',
            'cnpj': '23.456.789/0001-01',
            'telefone': '(11) 2345-6789',
            'email': 'comercial@greentech.com.br',
            'tabela_preco_id': tabelas_preco[2],
            'banco': 'Itaú',
            'agencia': '2345-6',
            'conta_bancaria': '23456-7',
            'chave_pix': 'comercial@greentech.com.br'
        },
        {
            'nome': 'Recicla SP Eletrônicos',
            'nome_social': 'Recicla SP',
            'cnpj': '34.567.890/0001-12',
            'telefone': '(11) 3456-7891',
            'email': 'vendas@reciclasp.com.br',
            'tabela_preco_id': tabelas_preco[3],
            'banco': 'Santander',
            'agencia': '3456-7',
            'conta_bancaria': '34567-8',
            'chave_pix': '(11) 3456-7891'
        },
        {
            'nome': 'EcoMateriais Reciclagem',
            'nome_social': 'EcoMateriais',
            'cnpj': '45.678.901/0001-23',
            'telefone': '(11) 4567-8901',
            'email': 'contato@ecomateriais.com.br',
            'tabela_preco_id': tabelas_preco[1],
            'banco': 'Bradesco',
            'agencia': '4567-8',
            'conta_bancaria': '45678-9',
            'chave_pix': 'contato@ecomateriais.com.br'
        },
        {
            'nome': 'Sustenta Comércio de Sucatas',
            'nome_social': 'Sustenta',
            'cnpj': '56.789.012/0001-34',
            'telefone': '(11) 5678-9012',
            'email': 'comercial@sustenta.com.br',
            'tabela_preco_id': tabelas_preco[2],
            'banco': 'Caixa Econômica',
            'agencia': '5678-9',
            'conta_bancaria': '56789-0',
            'chave_pix': '56.789.012/0001-34'
        },
        {
            'nome': 'MetalTech Reciclagem',
            'nome_social': 'MetalTech',
            'cnpj': '67.890.123/0001-45',
            'telefone': '(11) 6789-0123',
            'email': 'vendas@metaltech.com.br',
            'tabela_preco_id': tabelas_preco[3],
            'banco': 'Banco do Brasil',
            'agencia': '6789-0',
            'conta_bancaria': '67890-1',
            'chave_pix': 'vendas@metaltech.com.br'
        },
        {
            'nome': 'Digital Waste Solutions',
            'nome_social': 'Digital Waste',
            'cnpj': '78.901.234/0001-56',
            'telefone': '(11) 7890-1234',
            'email': 'contato@digitalwaste.com.br',
            'tabela_preco_id': tabelas_preco[2],
            'banco': 'Itaú',
            'agencia': '7890-1',
            'conta_bancaria': '78901-2',
            'chave_pix': '(11) 7890-1234'
        },
        {
            'nome': 'ReciclaTudo Ltda',
            'nome_social': 'ReciclaTudo',
            'cnpj': '89.012.345/0001-67',
            'telefone': '(11) 8901-2345',
            'email': 'comercial@reciclatudo.com.br',
            'tabela_preco_id': tabelas_preco[1],
            'banco': 'Santander',
            'agencia': '8901-2',
            'conta_bancaria': '89012-3',
            'chave_pix': 'comercial@reciclatudo.com.br'
        },
        {
            'nome': 'SmartRecycle Tecnologia',
            'nome_social': 'SmartRecycle',
            'cnpj': '90.123.456/0001-78',
            'telefone': '(11) 9012-3456',
            'email': 'vendas@smartrecycle.com.br',
            'tabela_preco_id': tabelas_preco[3],
            'banco': 'Bradesco',
            'agencia': '9012-3',
            'conta_bancaria': '90123-4',
            'chave_pix': 'vendas@smartrecycle.com.br'
        },
        {
            'nome': 'CircularTech Materiais',
            'nome_social': 'CircularTech',
            'cnpj': '01.234.567/0001-89',
            'telefone': '(11) 0123-4567',
            'email': 'contato@circulartech.com.br',
            'tabela_preco_id': tabelas_preco[2],
            'banco': 'Caixa Econômica',
            'agencia': '0123-4',
            'conta_bancaria': '01234-5',
            'chave_pix': '01.234.567/0001-89'
        }
    ]
    
    fornecedores = []
    for i, data in enumerate(fornecedores_data):
        cidade_data = cidades_sp[i]
        
        fornecedor = Fornecedor(
            **data,
            cidade=cidade_data[0],
            estado=cidade_data[1],
            cep=cidade_data[2],
            bairro=cidade_data[3],
            rua=f'Rua {random.choice(["das Flores", "Principal", "São João", "Comercial", "Industrial"])}',
            numero=str(random.randint(100, 999)),
            latitude=cidade_data[4],
            longitude=cidade_data[5],
            vendedor_id=vendedores[i % len(vendedores)].id,
            criado_por_id=admin.id,
            comprador_responsavel_id=comprador.id,
            condicao_pagamento='avista',
            forma_pagamento='pix'
        )
        db.session.add(fornecedor)
        fornecedores.append(fornecedor)
    
    db.session.commit()
    
    # Criar relações de tipos de lote para cada fornecedor
    print("   Vinculando tipos de lote aos fornecedores...")
    for fornecedor in fornecedores:
        # Cada fornecedor trabalha com 2-4 tipos de lote
        num_tipos = random.randint(2, 4)
        tipos_escolhidos = random.sample(tipos_lote, num_tipos)
        
        for tipo in tipos_escolhidos:
            rel = FornecedorTipoLote(
                fornecedor_id=fornecedor.id,
                tipo_lote_id=tipo.id
            )
            db.session.add(rel)
            
            # Criar classificação de estrelas para este tipo de lote
            classificacao = FornecedorTipoLoteClassificacao(
                fornecedor_id=fornecedor.id,
                tipo_lote_id=tipo.id,
                leve_estrelas=fornecedor.tabela_preco_id,
                medio_estrelas=fornecedor.tabela_preco_id,
                pesado_estrelas=fornecedor.tabela_preco_id
            )
            db.session.add(classificacao)
    
    db.session.commit()
    print(f"✅ {len(fornecedores)} fornecedores criados com tipos de lote vinculados!")
    return fornecedores


def criar_solicitacoes(fornecedores, usuarios, materiais, tipos_lote):
    """Cria solicitações vinculadas a fornecedores"""
    print("\n📝 Criando solicitações...")
    
    comprador = usuarios['joao_comprador']
    comprador2 = usuarios['fernanda_compradora']
    admin = usuarios['admin']
    
    solicitacoes = []
    
    # Criar 40 solicitações com diferentes status (mais dados para os gráficos)
    for i in range(40):
        fornecedor = random.choice(fornecedores)
        funcionario = random.choice([comprador, comprador2])
        
        # Datas distribuídas nos últimos 6 meses para popular o gráfico mensal
        dias_atras = random.randint(0, 180)
        data_envio = datetime.now() - timedelta(days=dias_atras)
        
        # Status variados - mais aprovadas para popular os gráficos
        if i < 25:
            status = 'aprovada'  # 25 aprovadas
        elif i < 30:
            status = 'pendente'  # 5 pendentes
        elif i < 35:
            status = 'confirmada'  # 5 confirmadas
        else:
            status = 'em_coleta'  # 5 em coleta
        
        solicitacao = Solicitacao(
            funcionario_id=funcionario.id,
            fornecedor_id=fornecedor.id,
            tipo_retirada=random.choice(['buscar', 'entregar']),
            modalidade_frete='FOB' if random.random() > 0.3 else 'CIF',
            status=status,
            data_envio=data_envio,
            data_confirmacao=data_envio + timedelta(hours=random.randint(2, 48)) if status in ['aprovada', 'confirmada', 'em_coleta'] else None,
            admin_id=admin.id if status in ['aprovada', 'em_coleta'] else None,
            rua=fornecedor.rua,
            numero=fornecedor.numero,
            cep=fornecedor.cep,
            localizacao_lat=fornecedor.latitude,
            localizacao_lng=fornecedor.longitude,
            endereco_completo=f"{fornecedor.rua}, {fornecedor.numero} - {fornecedor.bairro}, {fornecedor.cidade}/{fornecedor.estado}",
            observacoes=f"Solicitação de coleta #{i+1} - Material de qualidade"
        )
        db.session.add(solicitacao)
        solicitacoes.append(solicitacao)
    
    db.session.commit()
    
    # Criar itens para cada solicitação
    print("   Adicionando itens às solicitações...")
    for solicitacao in solicitacoes:
        # Cada solicitação tem 2-5 itens
        num_itens = random.randint(2, 5)
        
        # Pegar tipos de lote do fornecedor
        tipos_fornecedor = db.session.query(FornecedorTipoLote).filter_by(
            fornecedor_id=solicitacao.fornecedor_id
        ).all()
        
        if not tipos_fornecedor:
            continue
            
        for _ in range(num_itens):
            tipo_lote = random.choice(tipos_fornecedor).tipo_lote
            material = random.choice([m for m in materiais if m.classificacao in ['leve', 'medio', 'pesado']])
            
            peso_kg = round(random.uniform(50, 500), 2)
            estrelas = random.randint(1, 3)
            
            # Buscar preço do material
            preco_item = db.session.query(TabelaPrecoItem).filter_by(
                material_id=material.id,
                tabela_preco_id=estrelas
            ).first()
            
            preco_kg = float(preco_item.preco_por_kg) if preco_item else 5.0
            valor_calculado = round(peso_kg * preco_kg, 2)
            
            item = ItemSolicitacao(
                solicitacao_id=solicitacao.id,
                tipo_lote_id=tipo_lote.id,
                material_id=material.id,
                peso_kg=peso_kg,
                estrelas_final=estrelas,
                estrelas_sugeridas_ia=estrelas,
                classificacao=material.classificacao,
                classificacao_sugerida_ia=material.classificacao,
                valor_calculado=valor_calculado,
                preco_por_kg_snapshot=preco_kg,
                estrelas_snapshot=estrelas,
                justificativa_ia=f"Material classificado como {material.classificacao} - {estrelas} estrelas baseado em análise visual"
            )
            db.session.add(item)
    
    db.session.commit()
    print(f"✅ {len(solicitacoes)} solicitações criadas com itens!")
    return solicitacoes


def criar_ordens_compra(solicitacoes, usuarios):
    """Cria ordens de compra a partir das solicitações aprovadas"""
    print("\n🛒 Criando ordens de compra...")
    
    admin = usuarios['admin']
    comprador = usuarios['joao_comprador']
    
    ordens = []
    
    # Criar OC para solicitações confirmadas/aprovadas/em_coleta
    solicitacoes_aprovadas = [s for s in solicitacoes if s.status in ['confirmada', 'aprovada', 'em_coleta']]
    
    for solicitacao in solicitacoes_aprovadas[:30]:  # Criar 30 OCs
        # Calcular valor total da solicitação
        valor_total = sum(item.valor_calculado for item in solicitacao.itens)
        
        status_oc = random.choice(['em_analise', 'aprovada', 'processando', 'finalizada'])
        
        oc = OrdemCompra(
            solicitacao_id=solicitacao.id,
            fornecedor_id=solicitacao.fornecedor_id,
            valor_total=valor_total,
            status=status_oc,
            aprovado_por=admin.id if status_oc in ['aprovada', 'processando', 'finalizada'] else None,
            aprovado_em=datetime.now() - timedelta(days=random.randint(0, 10)) if status_oc in ['aprovada', 'processando', 'finalizada'] else None,
            criado_por=comprador.id,
            observacao=f"OC gerada automaticamente para solicitação #{solicitacao.id}"
        )
        db.session.add(oc)
        ordens.append(oc)
    
    db.session.commit()
    print(f"✅ {len(ordens)} ordens de compra criadas!")
    return ordens


def criar_veiculos_motoristas(usuarios):
    """Cria veículos e motoristas"""
    print("\n🚚 Criando veículos e motoristas...")
    
    admin = usuarios['admin']
    motorista1 = usuarios['lucas_motorista']
    motorista2 = usuarios['rafael_motorista']
    
    # Criar veículos
    veiculos_data = [
        {'placa': 'ABC-1234', 'tipo': 'Caminhão 3/4', 'capacidade': 3500, 'marca': 'Ford', 'modelo': 'Cargo 816', 'ano': 2020},
        {'placa': 'DEF-5678', 'tipo': 'Caminhão Toco', 'capacidade': 7000, 'marca': 'Mercedes', 'modelo': 'Accelo 1016', 'ano': 2021},
        {'placa': 'GHI-9012', 'tipo': 'Van', 'capacidade': 1500, 'marca': 'Fiat', 'modelo': 'Ducato', 'ano': 2019},
        {'placa': 'JKL-3456', 'tipo': 'Caminhão Truck', 'capacidade': 14000, 'marca': 'Volvo', 'modelo': 'VM 260', 'ano': 2022}
    ]
    
    veiculos = []
    for data in veiculos_data:
        veiculo = Veiculo(
            **data,
            renavam=f"{random.randint(10000000000, 99999999999)}",
            criado_por=admin.id
        )
        db.session.add(veiculo)
        veiculos.append(veiculo)
    
    db.session.commit()
    
    # Criar motoristas
    motoristas_data = [
        {
            'usuario_id': motorista1.id,
            'nome': motorista1.nome,
            'cpf': '111.222.333-44',
            'telefone': '(11) 91111-1111',
            'email': motorista1.email,
            'cnh': 'CNH123456789',
            'categoria_cnh': 'D',
            'veiculo_id': veiculos[0].id
        },
        {
            'usuario_id': motorista2.id,
            'nome': motorista2.nome,
            'cpf': '222.333.444-55',
            'telefone': '(11) 92222-2222',
            'email': motorista2.email,
            'cnh': 'CNH987654321',
            'categoria_cnh': 'E',
            'veiculo_id': veiculos[1].id
        },
        {
            'nome': 'Marcos Silva',
            'cpf': '333.444.555-66',
            'telefone': '(11) 93333-3333',
            'email': 'marcos.silva@mrx.com',
            'cnh': 'CNH456789123',
            'categoria_cnh': 'D',
            'veiculo_id': veiculos[2].id
        },
        {
            'nome': 'Paulo Santos',
            'cpf': '444.555.666-77',
            'telefone': '(11) 94444-4444',
            'email': 'paulo.santos@mrx.com',
            'cnh': 'CNH789123456',
            'categoria_cnh': 'E',
            'veiculo_id': veiculos[3].id
        }
    ]
    
    motoristas = []
    for data in motoristas_data:
        motorista = Motorista(**data, criado_por=admin.id)
        db.session.add(motorista)
        motoristas.append(motorista)
    
    db.session.commit()
    print(f"✅ {len(veiculos)} veículos e {len(motoristas)} motoristas criados!")
    return veiculos, motoristas


def criar_ordens_servico(ordens_compra, motoristas, veiculos, usuarios):
    """Cria ordens de serviço com motoristas atribuídos"""
    print("\n🚛 Criando ordens de serviço...")
    
    admin = usuarios['admin']
    
    ordens_servico = []
    
    # Criar OS para OCs aprovadas/processando
    ocs_para_os = [oc for oc in ordens_compra if oc.status in ['aprovada', 'processando', 'finalizada']]
    
    for i, oc in enumerate(ocs_para_os[:10]):  # Criar 10 OSs
        motorista = motoristas[i % len(motoristas)]
        veiculo = veiculos[i % len(veiculos)]
        fornecedor = oc.fornecedor
        
        status_os = random.choice(['PENDENTE', 'EM_ROTA', 'CHEGOU_LOCAL', 'COLETANDO', 'RETORNANDO', 'FINALIZADA'])
        
        # Janela de coleta
        dias_futuro = random.randint(1, 7)
        janela_inicio = datetime.now() + timedelta(days=dias_futuro, hours=8)
        janela_fim = janela_inicio + timedelta(hours=4)
        
        os = OrdemServico(
            oc_id=oc.id,
            numero_os=f"OS-{datetime.now().year}-{str(i+1).zfill(5)}",
            fornecedor_snapshot={
                'nome': fornecedor.nome,
                'endereco': f"{fornecedor.rua}, {fornecedor.numero}",
                'cidade': fornecedor.cidade,
                'telefone': fornecedor.telefone,
                'latitude': fornecedor.latitude,
                'longitude': fornecedor.longitude
            },
            tipo='COLETA',
            janela_coleta_inicio=janela_inicio,
            janela_coleta_fim=janela_fim,
            motorista_id=motorista.id,
            veiculo_id=veiculo.id,
            status=status_os,
            created_by=admin.id,
            rota={
                'origem': {'lat': -23.5505, 'lng': -46.6333, 'endereco': 'Base MRX - São Paulo'},
                'destino': {
                    'lat': fornecedor.latitude,
                    'lng': fornecedor.longitude,
                    'endereco': f"{fornecedor.rua}, {fornecedor.numero} - {fornecedor.cidade}"
                },
                'distancia_km': round(random.uniform(10, 100), 2),
                'tempo_estimado': random.randint(30, 180)
            }
        )
        db.session.add(os)
        ordens_servico.append(os)
    
    db.session.commit()
    print(f"✅ {len(ordens_servico)} ordens de serviço criadas!")
    return ordens_servico


def criar_conferencias_lotes(ordens_servico, usuarios):
    """Cria conferências de recebimento e lotes com dados completos e pesos distribuídos"""
    print("\n✅ Criando conferências e lotes...")
    
    conferente = usuarios['maria_conferente']
    admin = usuarios['admin']
    
    conferencias = []
    lotes = []
    
    # Criar conferências para OSs finalizadas
    os_finalizadas = [os for os in ordens_servico if os.status in ['FINALIZADA', 'RETORNANDO']]
    
    # Garantir pelo menos 30 lotes para popular bem os gráficos
    num_lotes = max(30, len(os_finalizadas))
    os_para_processar = os_finalizadas * (num_lotes // len(os_finalizadas) + 1) if os_finalizadas else []
    
    # Pesos base por classificação (em kg) para garantir valores realistas
    pesos_base = {
        'leve': random.uniform(100, 300),
        'media': random.uniform(500, 1000), 
        'pesada': random.uniform(1500, 3000)
    }
    
    for idx, os in enumerate(os_para_processar[:num_lotes]):
        oc = os.ordem_compra
        
        # Peso previsto baseado nos itens da solicitação ou peso base
        peso_previsto = sum(item.peso_kg for item in oc.solicitacao.itens)
        
        # Se o peso é muito baixo, usar peso base da classificação
        if peso_previsto < 50:
            classificacao_idx = idx % 3
            classificacoes = ['leve', 'media', 'pesada']
            classificacao = classificacoes[classificacao_idx]
            peso_previsto = pesos_base[classificacao] + random.uniform(-50, 50)
        
        quantidade_prevista = len(oc.solicitacao.itens)
        
        # Peso real com variação de ±10%
        variacao = random.uniform(-0.10, 0.10)
        peso_real = round(peso_previsto * (1 + variacao), 2)
        quantidade_real = quantidade_prevista + random.randint(-1, 1)
        
        # Calcular divergência
        divergencia = abs(variacao) > 0.05
        percentual_diferenca = round(abs(variacao) * 100, 2)
        tipo_divergencia = 'peso_menor' if variacao < 0 else ('peso_maior' if variacao > 0 else None)
        
        qualidade = random.choice(['excelente', 'boa', 'regular', 'ruim'])
        conf_status = 'APROVADA' if not divergencia else random.choice(['APROVADA', 'PENDENTE_DECISAO'])
        
        conferencia = ConferenciaRecebimento(
            os_id=os.id,
            oc_id=oc.id,
            peso_fornecedor=peso_previsto,
            peso_real=peso_real,
            quantidade_prevista=quantidade_prevista,
            quantidade_real=quantidade_real,
            qualidade=qualidade,
            divergencia=divergencia,
            tipo_divergencia=tipo_divergencia,
            percentual_diferenca=percentual_diferenca if divergencia else 0,
            conferencia_status=conf_status,
            conferente_id=conferente.id,
            observacoes=f"Conferência realizada em {datetime.now().strftime('%d/%m/%Y')} - Qualidade: {qualidade}",
            decisao_adm='aprovar' if conf_status == 'APROVADA' else None,
            decisao_adm_por=admin.id if conf_status == 'APROVADA' else None,
            decisao_adm_em=datetime.now() if conf_status == 'APROVADA' else None,
            gps_conferencia={'lat': -23.5505, 'lng': -46.6333},
            device_id_conferencia=f"DEVICE-{random.randint(1000, 9999)}"
        )
        db.session.add(conferencia)
        conferencias.append(conferencia)
        db.session.flush()
        
        # Obter todos os tipos de lote com classificação para distribuição balanceada
        tipos_lote_com_classificacao = db.session.query(TipoLote).filter(
            TipoLote.classificacao.isnot(None)
        ).all()
        
        # Selecionar tipo de lote de forma rotativa para garantir boa distribuição
        if tipos_lote_com_classificacao:
            tipo_lote = tipos_lote_com_classificacao[idx % len(tipos_lote_com_classificacao)]
        else:
            # Fallback para o tipo de lote da solicitação
            tipo_lote = oc.solicitacao.itens[0].tipo_lote if oc.solicitacao.itens else None
        
        if tipo_lote:
            # Usar a classificação do tipo de lote selecionado para garantir consistência
            if tipo_lote.classificacao:
                classificacao_predominante = tipo_lote.classificacao
            else:
                # Calcular classificação predominante baseada nos itens da solicitação
                classificacoes = [item.classificacao for item in oc.solicitacao.itens if item.classificacao]
                if classificacoes:
                    # Contar ocorrências e pegar a mais frequente
                    from collections import Counter
                    classificacao_counts = Counter(classificacoes)
                    classificacao_predominante = classificacao_counts.most_common(1)[0][0]
                else:
                    # Se não houver classificações, distribuir uniformemente
                    classificacao_predominante = ['leve', 'media', 'pesada'][idx % 3]
            
            # Status variados, com maioria aprovado/em_estoque para aparecer nos gráficos
            status_opcoes = ['aprovado', 'em_estoque', 'separado', 'finalizado'] * 3 + ['recebido', 'em_conferencia', 'conferido']
            status = random.choice(status_opcoes)
            
            lote = Lote(
                numero_lote=f"LOTE-{datetime.now().year}-{str(len(lotes)+1).zfill(5)}",
                fornecedor_id=oc.fornecedor_id,
                tipo_lote_id=tipo_lote.id,
                solicitacao_origem_id=oc.solicitacao_id,
                oc_id=oc.id,
                os_id=os.id,
                conferencia_id=conferencia.id,
                peso_bruto_recebido=peso_real,
                peso_liquido=round(peso_real * 0.95, 2),
                peso_total_kg=peso_real,
                valor_total=oc.valor_total,
                quantidade_itens=quantidade_real,
                estrelas_media=round(sum(item.estrelas_final for item in oc.solicitacao.itens) / len(oc.solicitacao.itens), 1) if oc.solicitacao.itens else 2.0,
                classificacao_predominante=classificacao_predominante,
                qualidade_recebida=qualidade,
                status=status,
                tipo_retirada=oc.solicitacao.tipo_retirada,
                localizacao_atual=random.choice(['A1', 'A2', 'B1', 'B2', 'C1']),
                conferente_id=conferente.id,
                observacoes=f"Lote recebido via OS {os.numero_os}"
            )
            db.session.add(lote)
            lotes.append(lote)
    
    db.session.commit()
    print(f"✅ {len(conferencias)} conferências e {len(lotes)} lotes criados!")
    return conferencias, lotes


def criar_entradas_estoque(lotes, usuarios):
    """Cria entradas de estoque para os lotes"""
    print("\n📥 Criando entradas de estoque...")
    
    admin = usuarios['admin']
    
    entradas = []
    
    # Criar entrada para lotes conferidos/disponíveis
    lotes_para_entrada = [l for l in lotes if l.status in ['conferido', 'disponivel']]
    
    for lote in lotes_para_entrada:
        entrada = EntradaEstoque(
            lote_id=lote.id,
            admin_id=admin.id,
            status='processada',
            data_processamento=datetime.now() - timedelta(hours=random.randint(1, 24)),
            observacoes=f"Entrada processada para lote {lote.numero_lote}"
        )
        db.session.add(entrada)
        entradas.append(entrada)
    
    db.session.commit()
    print(f"✅ {len(entradas)} entradas de estoque criadas!")
    return entradas


def criar_notificacoes(usuarios):
    """Cria notificações para os usuários"""
    print("\n🔔 Criando notificações...")
    
    comprador = usuarios['joao_comprador']
    conferente = usuarios['maria_conferente']
    admin = usuarios['admin']
    
    notificacoes_data = [
        {
            'usuario_id': comprador.id,
            'titulo': 'Nova Solicitação Aprovada',
            'mensagem': 'Sua solicitação #SOL-001 foi aprovada pelo administrador',
            'tipo': 'solicitacao',
            'lida': False
        },
        {
            'usuario_id': comprador.id,
            'titulo': 'Ordem de Compra Criada',
            'mensagem': 'OC #OC-001 foi gerada para sua solicitação',
            'tipo': 'ordem_compra',
            'lida': True
        },
        {
            'usuario_id': conferente.id,
            'titulo': 'Nova Coleta Chegando',
            'mensagem': 'OS #OS-001 está em rota para conferência',
            'tipo': 'ordem_servico',
            'lida': False
        },
        {
            'usuario_id': conferente.id,
            'titulo': 'Divergência Detectada',
            'mensagem': 'Conferência com divergência de peso requer análise',
            'tipo': 'conferencia',
            'lida': False
        },
        {
            'usuario_id': admin.id,
            'titulo': 'Sistema Atualizado',
            'mensagem': 'Sistema atualizado com sucesso - Versão 2.0',
            'tipo': 'sistema',
            'lida': True
        }
    ]
    
    notificacoes = []
    for data in notificacoes_data:
        notif = Notificacao(**data)
        db.session.add(notif)
        notificacoes.append(notif)
    
    db.session.commit()
    print(f"✅ {len(notificacoes)} notificações criadas!")
    return notificacoes


def exibir_resumo():
    """Exibe resumo final dos dados criados"""
    print("\n" + "="*60)
    print("📊 RESUMO FINAL DO BANCO DE DADOS")
    print("="*60)
    
    contagens = {
        'Vendedores': db.session.query(Vendedor).count(),
        'Materiais Base': db.session.query(MaterialBase).count(),
        'Preços de Materiais': db.session.query(TabelaPrecoItem).count(),
        'Tipos de Lote': db.session.query(TipoLote).count(),
        'Usuários': db.session.query(Usuario).count(),
        'Perfis': db.session.query(Perfil).count(),
        'Fornecedores': db.session.query(Fornecedor).count(),
        'Solicitações': db.session.query(Solicitacao).count(),
        'Itens de Solicitação': db.session.query(ItemSolicitacao).count(),
        'Ordens de Compra': db.session.query(OrdemCompra).count(),
        'Veículos': db.session.query(Veiculo).count(),
        'Motoristas': db.session.query(Motorista).count(),
        'Ordens de Serviço': db.session.query(OrdemServico).count(),
        'Conferências': db.session.query(ConferenciaRecebimento).count(),
        'Lotes': db.session.query(Lote).count(),
        'Entradas de Estoque': db.session.query(EntradaEstoque).count(),
        'Notificações': db.session.query(Notificacao).count()
    }
    
    for item, count in contagens.items():
        print(f"  {item:.<40} {count:>5}")
    
    print("="*60)
    print("\n✅ SISTEMA TOTALMENTE POPULADO E PRONTO PARA DEMONSTRAÇÃO!")
    print("\n🔐 Credenciais de Acesso:")
    print("   Email: admin@sistema.com")
    print("   Senha: admin123")
    print("\n📱 Outros usuários:")
    print("   joao.comprador@mrx.com (Comprador)")
    print("   maria.conferente@mrx.com (Conferente)")
    print("   pedro.separador@mrx.com (Separação)")
    print("   lucas.motorista@mrx.com (Motorista)")
    print("   Senha para todos: senha123")
    print("="*60 + "\n")


def main():
    """Função principal que executa todo o processo de população"""
    print("\n" + "="*60)
    print("🚀 INICIANDO POPULAÇÃO DO SISTEMA MRX")
    print("="*60)
    
    app = create_app()
    
    with app.app_context():
        try:
            # 1. Limpar dados antigos
            limpar_dados_antigos()
            
            # 2. Criar vendedores
            vendedores = criar_vendedores()
            
            # 3. Criar materiais base
            materiais = criar_materiais_base()
            
            # 4. Criar preços dos materiais
            criar_precos_materiais(materiais)
            
            # 5. Criar tipos de lote
            tipos_lote = criar_tipos_lote()
            
            # 6. Criar usuários
            usuarios = criar_usuarios()
            
            # 7. Criar fornecedores
            fornecedores = criar_fornecedores(vendedores, usuarios, tipos_lote)
            
            # 8. Criar solicitações
            solicitacoes = criar_solicitacoes(fornecedores, usuarios, materiais, tipos_lote)
            
            # 9. Criar ordens de compra
            ordens_compra = criar_ordens_compra(solicitacoes, usuarios)
            
            # 10. Criar veículos e motoristas
            veiculos, motoristas = criar_veiculos_motoristas(usuarios)
            
            # 11. Criar ordens de serviço
            ordens_servico = criar_ordens_servico(ordens_compra, motoristas, veiculos, usuarios)
            
            # 12. Criar conferências e lotes
            conferencias, lotes = criar_conferencias_lotes(ordens_servico, usuarios)
            
            # 13. Criar entradas de estoque
            entradas = criar_entradas_estoque(lotes, usuarios)
            
            # 14. Criar notificações
            notificacoes = criar_notificacoes(usuarios)
            
            # 15. Exibir resumo
            exibir_resumo()
            
        except Exception as e:
            print(f"\n❌ ERRO: {str(e)}")
            import traceback
            traceback.print_exc()
            db.session.rollback()
            return 1
    
    return 0


if __name__ == '__main__':
    exit(main())
