"""
Script de Correção Retroativa - Criar OCs Faltantes
Este script identifica solicitações aprovadas sem OC e cria as OCs com valores corretos
"""
import os
os.environ['DATABASE_URL'] = os.environ.get('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/mrx_db')

from app import create_app
from app.models import db, Solicitacao, OrdemCompra, Lote, ItemSolicitacao, AuditoriaOC
from app.utils.auditoria import registrar_auditoria_oc
from datetime import datetime

def corrigir_ocs_faltantes():
    app = create_app()
    
    with app.app_context():
        print(f"\n{'='*80}")
        print(f"🔧 SCRIPT DE CORREÇÃO RETROATIVA - OCs FALTANTES")
        print(f"{'='*80}\n")
        
        # Buscar solicitações aprovadas sem OC
        solicitacoes_sem_oc = db.session.query(Solicitacao).filter(
            Solicitacao.status == 'aprovada',
            ~Solicitacao.id.in_(
                db.session.query(OrdemCompra.solicitacao_id)
            )
        ).all()
        
        print(f"📊 Total de solicitações aprovadas sem OC: {len(solicitacoes_sem_oc)}\n")
        
        if len(solicitacoes_sem_oc) == 0:
            print("✅ Não há solicitações aprovadas sem OC. Sistema está consistente!")
            print(f"{'='*80}\n")
            return
        
        ocs_criadas = []
        ocs_com_erro = []
        
        for solicitacao in solicitacoes_sem_oc:
            try:
                print(f"\n{'='*60}")
                print(f"🔄 Processando Solicitação #{solicitacao.id}")
                print(f"{'='*60}")
                print(f"   Fornecedor: {solicitacao.fornecedor.nome if solicitacao.fornecedor else 'N/A'}")
                print(f"   Data de aprovação: {solicitacao.data_confirmacao}")
                print(f"   Total de itens: {len(solicitacao.itens)}")
                
                # Validar que tem itens
                if not solicitacao.itens or len(solicitacao.itens) == 0:
                    print(f"   ⚠️ PULANDO: Solicitação sem itens")
                    ocs_com_erro.append({
                        'solicitacao_id': solicitacao.id,
                        'erro': 'Sem itens'
                    })
                    continue
                
                # Validar que todos os itens têm preços válidos
                itens_invalidos = [
                    item for item in solicitacao.itens 
                    if item.valor_calculado is None or item.valor_calculado < 0
                ]
                
                if itens_invalidos:
                    print(f"   ⚠️ PULANDO: {len(itens_invalidos)} itens sem preço válido")
                    ocs_com_erro.append({
                        'solicitacao_id': solicitacao.id,
                        'erro': f'{len(itens_invalidos)} itens sem preço válido'
                    })
                    continue
                
                # Calcular valor total
                valor_total = sum((item.valor_calculado or 0.0) for item in solicitacao.itens)
                print(f"   💰 Valor total calculado: R$ {valor_total:.2f}")
                
                if valor_total < 0:
                    print(f"   ⚠️ PULANDO: Valor total negativo")
                    ocs_com_erro.append({
                        'solicitacao_id': solicitacao.id,
                        'erro': 'Valor total negativo'
                    })
                    continue
                
                # Verificar se já tem lotes criados
                lotes_existentes = Lote.query.filter_by(
                    solicitacao_origem_id=solicitacao.id
                ).all()
                
                if lotes_existentes:
                    print(f"   ✅ Lotes já existem: {len(lotes_existentes)}")
                else:
                    print(f"   ⚠️ AVISO: Solicitação não tem lotes criados (pode ser esperado)")
                
                # Criar OC
                print(f"   🆕 Criando Ordem de Compra...")
                oc = OrdemCompra(
                    solicitacao_id=solicitacao.id,
                    fornecedor_id=solicitacao.fornecedor_id,
                    valor_total=valor_total,
                    status='em_analise',
                    criado_por=solicitacao.admin_id if solicitacao.admin_id else 1,
                    observacao=f'OC criada retroativamente pelo script de correção para solicitação #{solicitacao.id}'
                )
                
                db.session.add(oc)
                db.session.flush()
                
                print(f"   ✅ OC #{oc.id} criada com sucesso!")
                print(f"      Status: {oc.status}")
                print(f"      Valor: R$ {oc.valor_total:.2f}")
                
                # Registrar auditoria
                registrar_auditoria_oc(
                    oc_id=oc.id,
                    usuario_id=solicitacao.admin_id if solicitacao.admin_id else 1,
                    acao='criacao',
                    status_anterior=None,
                    status_novo='em_analise',
                    observacao=f'OC criada retroativamente pelo script de correção',
                    ip='127.0.0.1',
                    gps=None,
                    dispositivo='Script de Correção'
                )
                
                print(f"   ✅ Auditoria registrada")
                
                ocs_criadas.append({
                    'solicitacao_id': solicitacao.id,
                    'oc_id': oc.id,
                    'valor_total': valor_total
                })
                
            except Exception as e:
                print(f"   ❌ ERRO ao processar solicitação #{solicitacao.id}: {str(e)}")
                ocs_com_erro.append({
                    'solicitacao_id': solicitacao.id,
                    'erro': str(e)
                })
                db.session.rollback()
                continue
        
        # Commit final
        try:
            db.session.commit()
            print(f"\n{'='*80}")
            print(f"✅ CORREÇÃO CONCLUÍDA COM SUCESSO!")
            print(f"{'='*80}")
        except Exception as e:
            print(f"\n{'='*80}")
            print(f"❌ ERRO AO SALVAR ALTERAÇÕES: {str(e)}")
            print(f"{'='*80}")
            db.session.rollback()
            return
        
        # Relatório final
        print(f"\n📊 RELATÓRIO FINAL:")
        print(f"   OCs criadas: {len(ocs_criadas)}")
        print(f"   Erros: {len(ocs_com_erro)}")
        
        if ocs_criadas:
            print(f"\n✅ OCs CRIADAS:")
            for oc_info in ocs_criadas:
                print(f"   - Solicitação #{oc_info['solicitacao_id']} → OC #{oc_info['oc_id']} (R$ {oc_info['valor_total']:.2f})")
        
        if ocs_com_erro:
            print(f"\n⚠️ SOLICITAÇÕES COM ERRO:")
            for erro_info in ocs_com_erro:
                print(f"   - Solicitação #{erro_info['solicitacao_id']}: {erro_info['erro']}")
        
        print(f"\n{'='*80}\n")

if __name__ == '__main__':
    corrigir_ocs_faltantes()
