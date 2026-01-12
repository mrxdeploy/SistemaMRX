#!/usr/bin/env python3
"""
Script para popular o módulo de Produção com dados de teste.
Permite testar todo o fluxo do módulo.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from decimal import Decimal
from datetime import datetime, timedelta
from app import create_app, db
from app.models import (
    Usuario, Fornecedor, Lote, ClassificacaoGrade,
    OrdemProducao, ItemSeparadoProducao, BagProducao
)

def seed_classificacoes_adicionais():
    """Adiciona classificações MID_GRADE, LOW_GRADE e RESIDUO"""
    classificacoes = [
        {'nome': 'SUCATA PLACA VERDE COMUM', 'categoria': 'MID_GRADE', 'preco_estimado_kg': 15.00},
        {'nome': 'SUCATA PLACA MARROM', 'categoria': 'MID_GRADE', 'preco_estimado_kg': 12.00},
        {'nome': 'SUCATA FONTE ATX', 'categoria': 'MID_GRADE', 'preco_estimado_kg': 8.00},
        {'nome': 'SUCATA COOLER ALUMÍNIO', 'categoria': 'MID_GRADE', 'preco_estimado_kg': 5.00},
        {'nome': 'SUCATA DISSIPADOR COBRE', 'categoria': 'MID_GRADE', 'preco_estimado_kg': 25.00},
        {'nome': 'SUCATA CABO ELÉTRICO', 'categoria': 'LOW_GRADE', 'preco_estimado_kg': 3.00},
        {'nome': 'SUCATA PLÁSTICO ELETRÔNICO', 'categoria': 'LOW_GRADE', 'preco_estimado_kg': 0.50},
        {'nome': 'SUCATA CARCAÇA METÁLICA', 'categoria': 'LOW_GRADE', 'preco_estimado_kg': 2.00},
        {'nome': 'SUCATA PARAFUSOS', 'categoria': 'LOW_GRADE', 'preco_estimado_kg': 1.50},
        {'nome': 'RESÍDUO NÃO APROVEITÁVEL', 'categoria': 'RESIDUO', 'preco_estimado_kg': 0},
        {'nome': 'RESÍDUO PLÁSTICO COMUM', 'categoria': 'RESIDUO', 'preco_estimado_kg': 0},
        {'nome': 'RESÍDUO ISOPOR', 'categoria': 'RESIDUO', 'preco_estimado_kg': 0},
    ]
    
    count = 0
    for c in classificacoes:
        existente = ClassificacaoGrade.query.filter_by(nome=c['nome']).first()
        if not existente:
            nova = ClassificacaoGrade(
                nome=c['nome'],
                categoria=c['categoria'],
                preco_estimado_kg=c['preco_estimado_kg'],
                ativo=True
            )
            db.session.add(nova)
            count += 1
    
    db.session.commit()
    print(f"✓ {count} classificações adicionais criadas")

def seed_fornecedores():
    """Cria fornecedores de teste"""
    fornecedores = [
        {'nome': 'TechRecycle Ltda', 'email': 'contato@techrecycle.com', 'telefone': '11999998888', 'cidade': 'São Paulo', 'estado': 'SP'},
        {'nome': 'E-Lixo Reciclagem', 'email': 'comercial@elixo.com', 'telefone': '21988887777', 'cidade': 'Rio de Janeiro', 'estado': 'RJ'},
        {'nome': 'Green Components', 'email': 'vendas@greencomp.com', 'telefone': '31977776666', 'cidade': 'Belo Horizonte', 'estado': 'MG'},
        {'nome': 'Sucata Digital SP', 'email': 'sucatadigital@email.com', 'telefone': '11966665555', 'cidade': 'Campinas', 'estado': 'SP'},
        {'nome': 'MetalTech Recicláveis', 'email': 'metaltech@email.com', 'telefone': '41955554444', 'cidade': 'Curitiba', 'estado': 'PR'},
    ]
    
    count = 0
    for f in fornecedores:
        existente = Fornecedor.query.filter_by(email=f['email']).first()
        if not existente:
            novo = Fornecedor(
                nome=f['nome'],
                email=f['email'],
                telefone=f['telefone'],
                cidade=f['cidade'],
                estado=f['estado'],
                ativo=True
            )
            db.session.add(novo)
            count += 1
    
    db.session.commit()
    print(f"✓ {count} fornecedores de teste criados")

def seed_lotes_estoque():
    """Cria lotes no estoque para teste"""
    from app.models import TipoLote
    
    fornecedores = Fornecedor.query.filter_by(ativo=True).limit(3).all()
    if not fornecedores:
        print("! Nenhum fornecedor encontrado, criando fornecedores primeiro...")
        seed_fornecedores()
        fornecedores = Fornecedor.query.filter_by(ativo=True).limit(3).all()
    
    tipo_lote = TipoLote.query.first()
    if not tipo_lote:
        tipo_lote = TipoLote(nome='Material Eletrônico', descricao='Tipo padrão')
        db.session.add(tipo_lote)
        db.session.flush()
    
    lotes_existentes = Lote.query.filter(Lote.status.in_(['em_estoque', 'conferido'])).count()
    if lotes_existentes > 5:
        print(f"✓ Já existem {lotes_existentes} lotes no estoque")
        return
    
    materiais = [
        'Placas-mãe diversas',
        'Processadores Intel/AMD',
        'Memórias DDR3/DDR4',
        'Celulares usados',
        'HD e SSD diversos',
    ]
    
    count = 0
    for i, material in enumerate(materiais):
        fornecedor = fornecedores[i % len(fornecedores)]
        numero = f'LT-{datetime.now().strftime("%Y%m")}-{1000+i}'
        
        existente = Lote.query.filter_by(numero_lote=numero).first()
        if not existente:
            lote = Lote(
                numero_lote=numero,
                fornecedor_id=fornecedor.id,
                tipo_lote_id=tipo_lote.id,
                peso_bruto_recebido=float(100 + i * 50),
                peso_liquido=float(95 + i * 48),
                peso_total_kg=float(95 + i * 48),
                status='em_estoque'
            )
            db.session.add(lote)
            count += 1
    
    db.session.commit()
    print(f"✓ {count} lotes de teste criados")

def seed_ordens_producao():
    """Cria ordens de produção em diferentes estados"""
    admin = Usuario.query.filter_by(tipo='admin').first()
    if not admin:
        print("! Admin não encontrado")
        return
    
    fornecedores = Fornecedor.query.filter_by(ativo=True).limit(3).all()
    classificacoes_hg = ClassificacaoGrade.query.filter_by(categoria='HIGH_GRADE', ativo=True).limit(10).all()
    classificacoes_mg = ClassificacaoGrade.query.filter_by(categoria='MID_GRADE', ativo=True).limit(5).all()
    classificacoes_lg = ClassificacaoGrade.query.filter_by(categoria='LOW_GRADE', ativo=True).limit(3).all()
    
    ops_existentes = OrdemProducao.query.count()
    if ops_existentes > 3:
        print(f"✓ Já existem {ops_existentes} OPs no sistema")
        return
    
    ops_data = [
        {
            'tipo_material': 'Placas-mãe Desktop',
            'descricao': 'Lote de placas-mãe de computadores desktop para separação',
            'peso_entrada': 25.0,
            'quantidade_entrada': 50,
            'custo_total': 1500.00,
            'status': 'aberta',
            'fornecedor_idx': 0,
            'itens': []
        },
        {
            'tipo_material': 'Celulares Diversos',
            'descricao': 'Celulares usados para desmontagem',
            'peso_entrada': 15.0,
            'quantidade_entrada': 100,
            'custo_total': 2500.00,
            'status': 'em_separacao',
            'fornecedor_idx': 1,
            'itens': [
                {'peso': 0.8, 'qtd': 20, 'classificacao_idx': 'HG', 'classificacao_num': 0},
                {'peso': 1.5, 'qtd': 30, 'classificacao_idx': 'HG', 'classificacao_num': 1},
                {'peso': 2.0, 'qtd': 15, 'classificacao_idx': 'MG', 'classificacao_num': 0},
            ]
        },
        {
            'tipo_material': 'Processadores Intel',
            'descricao': 'Processadores diversos para classificação',
            'peso_entrada': 8.5,
            'quantidade_entrada': 200,
            'custo_total': 5000.00,
            'status': 'finalizada',
            'fornecedor_idx': 2,
            'itens': [
                {'peso': 2.0, 'qtd': 50, 'classificacao_idx': 'HG', 'classificacao_num': 0},
                {'peso': 1.8, 'qtd': 45, 'classificacao_idx': 'HG', 'classificacao_num': 1},
                {'peso': 1.5, 'qtd': 40, 'classificacao_idx': 'HG', 'classificacao_num': 2},
                {'peso': 1.2, 'qtd': 35, 'classificacao_idx': 'HG', 'classificacao_num': 3},
                {'peso': 0.5, 'qtd': 20, 'classificacao_idx': 'LG', 'classificacao_num': 0},
            ]
        },
        {
            'tipo_material': 'HD e SSD',
            'descricao': 'Discos rígidos e SSDs para reciclagem',
            'peso_entrada': 35.0,
            'quantidade_entrada': 80,
            'custo_total': 1200.00,
            'status': 'em_separacao',
            'fornecedor_idx': 0,
            'itens': [
                {'peso': 5.0, 'qtd': 15, 'classificacao_idx': 'HG', 'classificacao_num': 4},
                {'peso': 8.0, 'qtd': 25, 'classificacao_idx': 'MG', 'classificacao_num': 1},
            ]
        },
    ]
    
    for op_data in ops_data:
        fornecedor = fornecedores[op_data['fornecedor_idx']] if fornecedores else None
        peso_entrada = Decimal(str(op_data['peso_entrada']))
        custo_total = Decimal(str(op_data['custo_total']))
        
        ordem = OrdemProducao(
            numero_op=OrdemProducao.gerar_numero_op(),
            origem_tipo='fornecedor',
            fornecedor_id=fornecedor.id if fornecedor else None,
            tipo_material=op_data['tipo_material'],
            descricao_material=op_data['descricao'],
            peso_entrada=peso_entrada,
            quantidade_entrada=op_data['quantidade_entrada'],
            custo_total=custo_total,
            custo_unitario=custo_total / peso_entrada if peso_entrada > 0 else Decimal('0'),
            responsavel_id=admin.id,
            status=op_data['status']
        )
        
        if op_data['status'] in ['em_separacao', 'finalizada']:
            ordem.data_inicio_separacao = datetime.utcnow() - timedelta(hours=2)
        
        db.session.add(ordem)
        db.session.flush()
        
        peso_total_separado = Decimal('0')
        valor_estimado_total = Decimal('0')
        
        for item_data in op_data['itens']:
            if item_data['classificacao_idx'] == 'HG' and len(classificacoes_hg) > item_data['classificacao_num']:
                classificacao = classificacoes_hg[item_data['classificacao_num']]
            elif item_data['classificacao_idx'] == 'MG' and len(classificacoes_mg) > item_data['classificacao_num']:
                classificacao = classificacoes_mg[item_data['classificacao_num']]
            elif item_data['classificacao_idx'] == 'LG' and len(classificacoes_lg) > item_data['classificacao_num']:
                classificacao = classificacoes_lg[item_data['classificacao_num']]
            else:
                continue
            
            peso_kg = Decimal(str(item_data['peso']))
            custo_prop = (peso_kg / peso_entrada) * custo_total
            preco_kg = classificacao.preco_estimado_kg or Decimal('0')
            valor_est = peso_kg * preco_kg
            
            item = ItemSeparadoProducao(
                ordem_producao_id=ordem.id,
                classificacao_grade_id=classificacao.id,
                nome_item=classificacao.nome,
                peso_kg=peso_kg,
                quantidade=item_data['qtd'],
                custo_proporcional=custo_prop,
                valor_estimado=valor_est,
                separado_por_id=admin.id
            )
            
            bag = BagProducao.query.filter(
                BagProducao.classificacao_grade_id == classificacao.id,
                BagProducao.status == 'aberto'
            ).first()
            
            if not bag:
                bag = BagProducao(
                    codigo=BagProducao.gerar_codigo_bag(classificacao.nome),
                    classificacao_grade_id=classificacao.id,
                    criado_por_id=admin.id,
                    status='aberto'
                )
                db.session.add(bag)
                db.session.flush()
            
            item.bag_id = bag.id
            bag.peso_acumulado = Decimal(str(float(bag.peso_acumulado or 0) + float(peso_kg)))
            bag.quantidade_itens = (bag.quantidade_itens or 0) + item_data['qtd']
            
            if float(bag.peso_acumulado) >= float(bag.peso_capacidade_max or 50):
                bag.status = 'cheio'
            
            db.session.add(item)
            peso_total_separado += peso_kg
            valor_estimado_total += valor_est
        
        if op_data['status'] == 'finalizada':
            ordem.peso_total_separado = peso_total_separado
            ordem.peso_perdas = peso_entrada - peso_total_separado
            ordem.percentual_perda = ((peso_entrada - peso_total_separado) / peso_entrada * 100) if peso_entrada > 0 else Decimal('0')
            ordem.valor_estimado_total = valor_estimado_total
            ordem.lucro_prejuizo = valor_estimado_total - custo_total
            ordem.finalizado_por_id = admin.id
            ordem.data_finalizacao = datetime.utcnow() - timedelta(hours=1)
    
    db.session.commit()
    print(f"✓ {len(ops_data)} ordens de produção criadas com itens e bags")

def seed_precos_classificacoes():
    """Define preços estimados para as classificações HIGH GRADE"""
    precos = {
        'SUCATA PROCESSADOR CERAMICO A': 1500.00,
        'SUCATA PROCESSADOR CERAMICO B': 1200.00,
        'SUCATA PROCESSADOR CERAMICO C': 900.00,
        'SUCATA PROCESSADOR SLOT': 600.00,
        'SUCATA PROCESSADOR PLASTICO A': 400.00,
        'SUCATA PROCESSADOR PLASTICO B': 300.00,
        'SUCATA PROCESSADOR CHAPA A': 250.00,
        'SUCATA PROCESSADOR CHAPA B': 200.00,
        'SUCATA MEMORIA DOURADA': 350.00,
        'SUCATA MEMORIA PRATA': 150.00,
        'SUCATA PLACA DOURADA A': 180.00,
        'SUCATA PLACA DOURADA B': 120.00,
        'SUCATA PLACA CENTRAL A': 100.00,
        'SUCATA PLACA CENTRAL B': 80.00,
        'SUCATA PLACA CENTRAL S': 70.00,
        'SUCATA PLACA TAPETE A': 60.00,
        'SUCATA PLACA TAPETE B': 50.00,
        'SUCATA PLACA TAPETE C': 40.00,
        'SUCATA PLACA HD': 55.00,
        'SUCATA PLACA DE CELULAR': 200.00,
        'SUCATA APARELHO CELULAR A': 25.00,
        'SUCATA PLACA NOTEBOOK A': 85.00,
        'SUCATA PLACA NOTEBOOK B': 65.00,
        'SUCATA PLACA TABLET': 90.00,
        'SUCATA PLACA DRIVE': 45.00,
        'SUCATA METAL PRECIOSO': 500.00,
        'SUCATA PLACA LEVE A': 35.00,
    }
    
    count = 0
    for nome, preco in precos.items():
        classificacao = ClassificacaoGrade.query.filter_by(nome=nome).first()
        if classificacao and (not classificacao.preco_estimado_kg or float(classificacao.preco_estimado_kg) == 0):
            classificacao.preco_estimado_kg = Decimal(str(preco))
            count += 1
    
    db.session.commit()
    print(f"✓ {count} preços de classificações HIGH GRADE atualizados")

def main():
    app = create_app()
    with app.app_context():
        print("\n=== SEED MÓDULO DE PRODUÇÃO ===\n")
        
        print("1. Definindo preços das classificações...")
        seed_precos_classificacoes()
        
        print("\n2. Adicionando classificações MID/LOW/RESIDUO...")
        seed_classificacoes_adicionais()
        
        print("\n3. Criando fornecedores de teste...")
        seed_fornecedores()
        
        print("\n4. Criando lotes no estoque...")
        seed_lotes_estoque()
        
        print("\n5. Criando ordens de produção com itens...")
        seed_ordens_producao()
        
        print("\n=== SEED CONCLUÍDO ===")
        
        print("\n--- RESUMO ---")
        print(f"Classificações HIGH GRADE: {ClassificacaoGrade.query.filter_by(categoria='HIGH_GRADE').count()}")
        print(f"Classificações MID GRADE: {ClassificacaoGrade.query.filter_by(categoria='MID_GRADE').count()}")
        print(f"Classificações LOW GRADE: {ClassificacaoGrade.query.filter_by(categoria='LOW_GRADE').count()}")
        print(f"Classificações RESIDUO: {ClassificacaoGrade.query.filter_by(categoria='RESIDUO').count()}")
        print(f"Fornecedores ativos: {Fornecedor.query.filter_by(ativo=True).count()}")
        print(f"Lotes em estoque: {Lote.query.filter_by(status='em_estoque').count()}")
        print(f"OPs abertas: {OrdemProducao.query.filter_by(status='aberta').count()}")
        print(f"OPs em separação: {OrdemProducao.query.filter_by(status='em_separacao').count()}")
        print(f"OPs finalizadas: {OrdemProducao.query.filter_by(status='finalizada').count()}")
        print(f"Bags abertos: {BagProducao.query.filter_by(status='aberto').count()}")
        print(f"Bags cheios: {BagProducao.query.filter_by(status='cheio').count()}")

if __name__ == '__main__':
    main()
