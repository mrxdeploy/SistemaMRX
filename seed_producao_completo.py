
#!/usr/bin/env python3
"""
Script para popular o módulo de Produção com dados completos de teste
Inclui: classificações, OPs, itens separados, bags e lotes ativos
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from decimal import Decimal
from datetime import datetime, timedelta
import random
from app import create_app, db
from app.models import (
    Usuario, Fornecedor, Lote, ClassificacaoGrade,
    OrdemProducao, ItemSeparadoProducao, BagProducao, TipoLote
)

def criar_classificacoes():
    """Cria classificações de grade completas"""
    print("\n📋 Criando classificações...")
    
    classificacoes = [
        # HIGH GRADE
        {'nome': 'PROCESSADOR CERÂMICO OURO A', 'categoria': 'HIGH_GRADE', 'preco_estimado_kg': 1800.00, 'codigo': 'PROC-CER-A'},
        {'nome': 'PROCESSADOR CERÂMICO OURO B', 'categoria': 'HIGH_GRADE', 'preco_estimado_kg': 1500.00, 'codigo': 'PROC-CER-B'},
        {'nome': 'MEMÓRIA DOURADA DDR', 'categoria': 'HIGH_GRADE', 'preco_estimado_kg': 400.00, 'codigo': 'MEM-DDR'},
        {'nome': 'PLACA DOURADA TIPO A', 'categoria': 'HIGH_GRADE', 'preco_estimado_kg': 200.00, 'codigo': 'PLC-DOU-A'},
        {'nome': 'PLACA CENTRAL PREMIUM', 'categoria': 'HIGH_GRADE', 'preco_estimado_kg': 150.00, 'codigo': 'PLC-CENT'},
        {'nome': 'CONECTORES BANHADOS OURO', 'categoria': 'HIGH_GRADE', 'preco_estimado_kg': 350.00, 'codigo': 'CONECT-AU'},
        
        # MID GRADE
        {'nome': 'PLACA-MÃE DESKTOP', 'categoria': 'MID_GRADE', 'preco_estimado_kg': 25.00, 'codigo': 'PCB-DESK'},
        {'nome': 'PLACA DE VÍDEO', 'categoria': 'MID_GRADE', 'preco_estimado_kg': 35.00, 'codigo': 'PCB-VGA'},
        {'nome': 'FONTE ATX', 'categoria': 'MID_GRADE', 'preco_estimado_kg': 8.00, 'codigo': 'FONTE-ATX'},
        {'nome': 'HD/SSD COMPONENTES', 'categoria': 'MID_GRADE', 'preco_estimado_kg': 12.00, 'codigo': 'HDD-SSD'},
        {'nome': 'COOLER ALUMÍNIO', 'categoria': 'MID_GRADE', 'preco_estimado_kg': 5.00, 'codigo': 'COOL-ALU'},
        
        # LOW GRADE
        {'nome': 'CABOS E FIOS', 'categoria': 'LOW_GRADE', 'preco_estimado_kg': 3.00, 'codigo': 'CABO-FIO'},
        {'nome': 'PLÁSTICO ELETRÔNICO', 'categoria': 'LOW_GRADE', 'preco_estimado_kg': 0.50, 'codigo': 'PLAST-ELE'},
        {'nome': 'CARCAÇA METÁLICA', 'categoria': 'LOW_GRADE', 'preco_estimado_kg': 2.00, 'codigo': 'CARC-MET'},
        
        # RESÍDUO
        {'nome': 'RESÍDUO MISTO', 'categoria': 'RESIDUO', 'preco_estimado_kg': 0.00, 'codigo': 'RES-MIST'},
        {'nome': 'DESCARTE ISOPOR', 'categoria': 'RESIDUO', 'preco_estimado_kg': 0.00, 'codigo': 'DESC-ISO'},
    ]
    
    count = 0
    criadas = []
    for c in classificacoes:
        existente = ClassificacaoGrade.query.filter_by(nome=c['nome']).first()
        if not existente:
            nova = ClassificacaoGrade(**c, ativo=True)
            db.session.add(nova)
            criadas.append(nova)
            count += 1
        else:
            criadas.append(existente)
    
    db.session.commit()
    print(f"✅ {count} novas classificações criadas")
    return criadas

def criar_fornecedores():
    """Cria fornecedores de teste"""
    print("\n🏢 Criando fornecedores...")
    
    fornecedores_data = [
        {'nome': 'TechRecycle Brasil', 'cnpj': '12.345.678/0001-90', 'telefone': '(11) 99999-0001', 'email': 'contato@techrecycle.com.br'},
        {'nome': 'GreenTech Eletrônicos', 'cnpj': '23.456.789/0001-01', 'telefone': '(11) 99999-0002', 'email': 'vendas@greentech.com.br'},
        {'nome': 'Recicla Digital SP', 'cnpj': '34.567.890/0001-12', 'telefone': '(11) 99999-0003', 'email': 'comercial@recicladigital.com.br'},
    ]
    
    count = 0
    criados = []
    for f in fornecedores_data:
        existente = Fornecedor.query.filter_by(cnpj=f['cnpj']).first()
        if not existente:
            novo = Fornecedor(**f, ativo=True, cidade='São Paulo', estado='SP')
            db.session.add(novo)
            criados.append(novo)
            count += 1
        else:
            criados.append(existente)
    
    db.session.commit()
    print(f"✅ {count} novos fornecedores criados")
    return criados

def criar_lotes_estoque(fornecedores):
    """Cria lotes no estoque"""
    print("\n📦 Criando lotes em estoque...")
    
    tipo_lote = TipoLote.query.first()
    if not tipo_lote:
        tipo_lote = TipoLote(nome='Eletrônicos', codigo='ELET', ativo=True)
        db.session.add(tipo_lote)
        db.session.flush()
    
    lotes_data = [
        {'peso': 150.5, 'fornecedor_idx': 0, 'status': 'em_estoque'},
        {'peso': 280.3, 'fornecedor_idx': 1, 'status': 'em_estoque'},
        {'peso': 95.7, 'fornecedor_idx': 2, 'status': 'disponivel'},
        {'peso': 420.8, 'fornecedor_idx': 0, 'status': 'em_estoque'},
    ]
    
    criados = []
    for i, data in enumerate(lotes_data):
        fornecedor = fornecedores[data['fornecedor_idx']] if fornecedores else None
        numero = f'LT-{datetime.now().strftime("%Y%m")}-{2000+i}'
        
        lote = Lote(
            numero_lote=numero,
            fornecedor_id=fornecedor.id if fornecedor else None,
            tipo_lote_id=tipo_lote.id,
            peso_bruto_recebido=data['peso'],
            peso_liquido=data['peso'] * 0.95,
            peso_total_kg=data['peso'],
            status=data['status'],
            data_criacao=datetime.utcnow() - timedelta(days=random.randint(1, 15))
        )
        db.session.add(lote)
        criados.append(lote)
    
    db.session.commit()
    print(f"✅ {len(criados)} lotes criados")
    return criados

def criar_ordens_producao(fornecedores, lotes, classificacoes, admin):
    """Cria ordens de produção em diferentes estados"""
    print("\n🔧 Criando ordens de produção...")
    
    ops_data = [
        {
            'tipo_material': 'Placas-mãe Desktop',
            'descricao': 'Lote de placas-mãe variadas para separação completa',
            'peso_entrada': 45.5,
            'quantidade': 85,
            'custo_total': 2500.00,
            'status': 'aberta',
            'fornecedor_idx': 0,
            'lote_idx': None,
            'criar_itens': False
        },
        {
            'tipo_material': 'Celulares Diversos',
            'descricao': 'Smartphones variados para desmontagem',
            'peso_entrada': 28.3,
            'quantidade': 120,
            'custo_total': 3500.00,
            'status': 'em_separacao',
            'fornecedor_idx': 1,
            'lote_idx': 0,
            'criar_itens': True,
            'itens': [
                {'peso': 2.5, 'qtd': 30, 'classificacao': 'PROCESSADOR CERÂMICO OURO A'},
                {'peso': 1.8, 'qtd': 25, 'classificacao': 'MEMÓRIA DOURADA DDR'},
                {'peso': 3.2, 'qtd': 40, 'classificacao': 'PLACA DOURADA TIPO A'},
                {'peso': 5.1, 'qtd': 15, 'classificacao': 'PLACA-MÃE DESKTOP'},
            ]
        },
        {
            'tipo_material': 'Processadores Intel/AMD',
            'descricao': 'Mix de processadores para classificação',
            'peso_entrada': 12.8,
            'quantidade': 250,
            'custo_total': 8000.00,
            'status': 'finalizada',
            'fornecedor_idx': 2,
            'lote_idx': 1,
            'criar_itens': True,
            'itens': [
                {'peso': 3.2, 'qtd': 80, 'classificacao': 'PROCESSADOR CERÂMICO OURO A'},
                {'peso': 2.8, 'qtd': 70, 'classificacao': 'PROCESSADOR CERÂMICO OURO B'},
                {'peso': 2.5, 'qtd': 60, 'classificacao': 'CONECTORES BANHADOS OURO'},
                {'peso': 1.8, 'qtd': 30, 'classificacao': 'PLACA CENTRAL PREMIUM'},
                {'peso': 0.5, 'qtd': 10, 'classificacao': 'RESÍDUO MISTO'},
            ]
        },
        {
            'tipo_material': 'Computadores Completos',
            'descricao': 'Desktops para desmontagem total',
            'peso_entrada': 85.0,
            'quantidade': 25,
            'custo_total': 1800.00,
            'status': 'em_separacao',
            'fornecedor_idx': 0,
            'lote_idx': 2,
            'criar_itens': True,
            'itens': [
                {'peso': 12.5, 'qtd': 8, 'classificacao': 'PLACA-MÃE DESKTOP'},
                {'peso': 8.3, 'qtd': 6, 'classificacao': 'PLACA DE VÍDEO'},
                {'peso': 6.2, 'qtd': 10, 'classificacao': 'FONTE ATX'},
                {'peso': 15.4, 'qtd': 12, 'classificacao': 'HD/SSD COMPONENTES'},
                {'peso': 5.8, 'qtd': 15, 'classificacao': 'COOLER ALUMÍNIO'},
                {'peso': 8.5, 'qtd': 20, 'classificacao': 'CABOS E FIOS'},
                {'peso': 12.3, 'qtd': 25, 'classificacao': 'CARCAÇA METÁLICA'},
            ]
        },
    ]
    
    criadas = []
    for op_data in ops_data:
        fornecedor = fornecedores[op_data['fornecedor_idx']] if fornecedores else None
        lote = lotes[op_data['lote_idx']] if op_data.get('lote_idx') is not None and lotes else None
        
        peso_entrada = Decimal(str(op_data['peso_entrada']))
        custo_total = Decimal(str(op_data['custo_total']))
        custo_unitario = custo_total / peso_entrada if peso_entrada > 0 else Decimal('0')
        
        origem_tipo = 'estoque' if lote else 'fornecedor'
        
        ordem = OrdemProducao(
            numero_op=OrdemProducao.gerar_numero_op(),
            origem_tipo=origem_tipo,
            fornecedor_id=fornecedor.id if fornecedor else None,
            lote_origem_id=lote.id if lote else None,
            tipo_material=op_data['tipo_material'],
            descricao_material=op_data['descricao'],
            peso_entrada=peso_entrada,
            quantidade_entrada=op_data['quantidade'],
            custo_total=custo_total,
            custo_unitario=custo_unitario,
            responsavel_id=admin.id,
            status=op_data['status'],
            data_abertura=datetime.utcnow() - timedelta(days=random.randint(0, 30))
        )
        
        if op_data['status'] in ['em_separacao', 'finalizada']:
            ordem.data_inicio_separacao = ordem.data_abertura + timedelta(hours=2)
        
        db.session.add(ordem)
        db.session.flush()
        
        # Marcar lote como em produção se aplicável
        if lote:
            lote.status = 'em_producao'
        
        # Criar itens se necessário
        if op_data.get('criar_itens') and op_data.get('itens'):
            peso_total_separado = Decimal('0')
            valor_estimado_total = Decimal('0')
            
            for item_data in op_data['itens']:
                classificacao = next((c for c in classificacoes if c.nome == item_data['classificacao']), None)
                if not classificacao:
                    continue
                
                peso_kg = Decimal(str(item_data['peso']))
                custo_prop = (peso_kg / peso_entrada) * custo_total
                preco_kg = classificacao.preco_estimado_kg or Decimal('0')
                valor_est = peso_kg * preco_kg
                
                # Encontrar ou criar bag
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
                
                item = ItemSeparadoProducao(
                    ordem_producao_id=ordem.id,
                    classificacao_grade_id=classificacao.id,
                    nome_item=classificacao.nome,
                    peso_kg=peso_kg,
                    quantidade=item_data['qtd'],
                    custo_proporcional=custo_prop,
                    valor_estimado=valor_est,
                    separado_por_id=admin.id,
                    bag_id=bag.id
                )
                db.session.add(item)
                
                # Atualizar bag
                bag.peso_acumulado = Decimal(str(float(bag.peso_acumulado or 0) + float(peso_kg)))
                bag.quantidade_itens = (bag.quantidade_itens or 0) + item_data['qtd']
                
                if ordem.id not in (bag.lotes_origem or []):
                    lotes_origem = bag.lotes_origem or []
                    lotes_origem.append(ordem.id)
                    bag.lotes_origem = lotes_origem
                
                # Marcar bag como cheio se necessário
                if float(bag.peso_acumulado) >= float(bag.peso_capacidade_max or 50):
                    bag.status = 'cheio'
                
                peso_total_separado += peso_kg
                valor_estimado_total += valor_est
            
            # Se finalizada, calcular totais
            if op_data['status'] == 'finalizada':
                ordem.peso_total_separado = peso_total_separado
                ordem.peso_perdas = peso_entrada - peso_total_separado
                ordem.percentual_perda = ((peso_entrada - peso_total_separado) / peso_entrada * 100) if peso_entrada > 0 else Decimal('0')
                ordem.valor_estimado_total = valor_estimado_total
                ordem.lucro_prejuizo = valor_estimado_total - custo_total
                ordem.finalizado_por_id = admin.id
                ordem.data_finalizacao = datetime.utcnow() - timedelta(hours=random.randint(1, 24))
        
        criadas.append(ordem)
    
    db.session.commit()
    print(f"✅ {len(criadas)} ordens de produção criadas")
    return criadas

def main():
    app = create_app()
    with app.app_context():
        print("\n" + "="*60)
        print("🚀 POPULANDO MÓDULO DE PRODUÇÃO COM DADOS DE TESTE")
        print("="*60)
        
        # Verificar admin
        admin = Usuario.query.filter_by(tipo='admin').first()
        if not admin:
            print("❌ Usuário admin não encontrado!")
            return
        
        print(f"👤 Admin: {admin.nome}")
        
        # Criar dados
        classificacoes = criar_classificacoes()
        fornecedores = criar_fornecedores()
        lotes = criar_lotes_estoque(fornecedores)
        ordens = criar_ordens_producao(fornecedores, lotes, classificacoes, admin)
        
        # Resumo
        print("\n" + "="*60)
        print("✅ DADOS CRIADOS COM SUCESSO!")
        print("="*60)
        print(f"📋 Classificações: {ClassificacaoGrade.query.count()}")
        print(f"   - HIGH_GRADE: {ClassificacaoGrade.query.filter_by(categoria='HIGH_GRADE').count()}")
        print(f"   - MID_GRADE: {ClassificacaoGrade.query.filter_by(categoria='MID_GRADE').count()}")
        print(f"   - LOW_GRADE: {ClassificacaoGrade.query.filter_by(categoria='LOW_GRADE').count()}")
        print(f"   - RESIDUO: {ClassificacaoGrade.query.filter_by(categoria='RESIDUO').count()}")
        print(f"\n🏢 Fornecedores: {Fornecedor.query.filter_by(ativo=True).count()}")
        print(f"\n📦 Lotes:")
        print(f"   - Em estoque: {Lote.query.filter_by(status='em_estoque').count()}")
        print(f"   - Disponíveis: {Lote.query.filter_by(status='disponivel').count()}")
        print(f"   - Em produção: {Lote.query.filter_by(status='em_producao').count()}")
        print(f"\n🔧 Ordens de Produção:")
        print(f"   - Abertas: {OrdemProducao.query.filter_by(status='aberta').count()}")
        print(f"   - Em separação: {OrdemProducao.query.filter_by(status='em_separacao').count()}")
        print(f"   - Finalizadas: {OrdemProducao.query.filter_by(status='finalizada').count()}")
        print(f"\n📊 Itens Separados: {ItemSeparadoProducao.query.count()}")
        print(f"\n🎒 Bags:")
        print(f"   - Abertos: {BagProducao.query.filter_by(status='aberto').count()}")
        print(f"   - Cheios: {BagProducao.query.filter_by(status='cheio').count()}")
        print("="*60)
        print("\n💡 Acesse /api/producao/ para visualizar os dados!")
        print("="*60 + "\n")

if __name__ == '__main__':
    main()
