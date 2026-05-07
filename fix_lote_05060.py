import psycopg2
import sys
from decimal import Decimal
from datetime import datetime

# Fix encoding for Windows console
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

conn = psycopg2.connect('postgresql://postgres:dWldGAyqtVAsQvMYvTIqBKXTkHedCLAS@shortline.proxy.rlwy.net:26559/railway')
cur = conn.cursor()

LOTE_PAI_ID = 6511
LOTE_PAI_NUM = '2026-05060'
SEP_ID = 156

print('=' * 70)
print(f'DIAGNÓSTICO FINAL - LOTE {LOTE_PAI_NUM}')
print('=' * 70)

# 1. Confirmar itens
cur.execute("""
    SELECT is_.id, mb.nome, mb.id as mat_id, is_.peso_kg, is_.tipo_lote_id,
           is_.valor_calculado
    FROM itens_solicitacao is_
    LEFT JOIN materiais_base mb ON mb.id = is_.material_id
    WHERE is_.lote_id = %s
    ORDER BY is_.id
""", (LOTE_PAI_ID,))
itens = cur.fetchall()
print(f'\n[OK] {len(itens)} itens encontrados no lote {LOTE_PAI_NUM}:')
for it in itens:
    print(f'  item_id={it[0]}, mat={it[1]}, mat_id={it[2]}, peso={it[3]}kg, tipo_id={it[4]}')

# 2. Confirmar dados do lote pai
cur.execute("SELECT peso_total_kg, peso_liquido, fornecedor_id, tipo_lote_id, valor_total FROM lotes WHERE id = %s", (LOTE_PAI_ID,))
lote_pai = cur.fetchone()
peso_pai = float(lote_pai[0] or lote_pai[1] or 0)
fornecedor_id = lote_pai[2]
tipo_lote_id_pai = lote_pai[3]
valor_total_pai = Decimal(str(lote_pai[4] or 0))
print(f'\n[OK] Lote pai: peso={peso_pai}kg, fornecedor_id={fornecedor_id}, tipo_lote_id={tipo_lote_id_pai}, valor_total={valor_total_pai}')

# 3. Verificar sublotes existentes (devem ser 0)
cur.execute("SELECT count(*) FROM lotes WHERE lote_pai_id = %s", (LOTE_PAI_ID,))
sublotes_existentes = cur.fetchone()[0]
print(f'\n[OK] Sublotes existentes: {sublotes_existentes}')

if sublotes_existentes > 0:
    print('AVISO: Já existem sublotes! Abortando para não duplicar.')
    conn.close()
    sys.exit(1)

# 4. Buscar o maior numero_lote para continuar a sequência
cur.execute("SELECT MAX(numero_lote) FROM lotes WHERE numero_lote LIKE '2026-%'")
ultimo = cur.fetchone()[0]
try:
    seq_atual = int(ultimo.split('-')[1])
except:
    seq_atual = 6511
print(f'\n[OK] Último número de lote: {ultimo} -> próximo sequencial: {seq_atual+1}')

# 5. Verificar tipo_lote fallback (tipo do pai)
cur.execute("SELECT id, nome FROM tipos_lote WHERE id = %s", (tipo_lote_id_pai,))
tipo_pai = cur.fetchone()
print(f'[OK] Tipo lote do pai: id={tipo_pai[0]}, nome={tipo_pai[1]}')

# 6. CRIAR OS 25 SUBLOTES
print('\n' + '='*70)
print('CRIANDO 25 SUBLOTES...')
print('='*70)

# Primeiro reverter o lote pai e a separação para status correto
print('\n[1] Revertendo lote pai para EM_SEPARACAO temporariamente...')
cur.execute("UPDATE lotes SET status = 'EM_SEPARACAO' WHERE id = %s", (LOTE_PAI_ID,))
cur.execute("UPDATE lotes_separacao SET status = 'EM_SEPARACAO', data_finalizacao = NULL WHERE id = %s", (SEP_ID,))

# Resetar peso_total_sublotes
cur.execute("UPDATE lotes_separacao SET peso_total_sublotes = 0.0 WHERE id = %s", (SEP_ID,))

print('[OK] Status revertido para EM_SEPARACAO')

# Criar sublotes
novos_sublotes = []
peso_total_criado = 0.0
peso_pai_decimal = Decimal(str(peso_pai)) if peso_pai > 0 else Decimal('1')

for i, item in enumerate(itens):
    item_id, mat_nome, mat_id, peso_kg, tipo_lote_id, valor_item = item
    
    seq_atual += 1
    numero_sublote = f'2026-{str(seq_atual).zfill(5)}'
    
    peso_sublote = Decimal(str(peso_kg or 0))
    
    # Calcular valor proporcional
    valor_proporcional = (peso_sublote / peso_pai_decimal) * valor_total_pai if peso_pai_decimal > 0 else Decimal('0')
    valor_proporcional = round(float(valor_proporcional), 2)
    
    # Determinar tipo_lote_id: usar do item se disponível, senão fallback para o pai
    tipo_id_final = tipo_lote_id if tipo_lote_id else tipo_lote_id_pai
    
    # Montar observacoes
    obs = f'MATERIAL:{mat_nome}' if mat_nome else f'Item do lote {LOTE_PAI_NUM}'
    
    # Auditoria
    auditoria = [{
        'acao': 'SUBLOTE_CRIADO_CORRECAO_MANUAL',
        'usuario_id': 'sistema',
        'timestamp': datetime.utcnow().isoformat(),
        'origem': 'SCRIPT_CORRECAO_BUG',
        'lote_pai_id': LOTE_PAI_ID,
        'lote_pai_numero': LOTE_PAI_NUM,
        'item_solicitacao_id': item_id,
        'material_nome': mat_nome,
        'valor_proporcional': valor_proporcional
    }]
    
    import json
    cur.execute("""
        INSERT INTO lotes (
            numero_lote, fornecedor_id, tipo_lote_id,
            peso_total_kg, peso_liquido, valor_total,
            qualidade_recebida, status, lote_pai_id,
            quantidade_itens, observacoes, auditoria,
            data_criacao, bloqueado, reservado
        ) VALUES (
            %s, %s, %s,
            %s, %s, %s,
            %s, %s, %s,
            %s, %s, %s,
            NOW(), FALSE, FALSE
        ) RETURNING id
    """, (
        numero_sublote,
        fornecedor_id,
        tipo_id_final,
        float(peso_sublote),
        float(peso_sublote),
        valor_proporcional,
        'A',
        'CRIADO_SEPARACAO',
        LOTE_PAI_ID,
        1,
        obs,
        json.dumps(auditoria)
    ))
    
    novo_id = cur.fetchone()[0]
    novos_sublotes.append((novo_id, numero_sublote, mat_nome, float(peso_sublote)))
    peso_total_criado += float(peso_sublote)
    
    print(f'  [{i+1:02d}/25] Criado sublote {numero_sublote} (id={novo_id}): {mat_nome} | {float(peso_sublote):.2f}kg')

print(f'\n[OK] {len(novos_sublotes)} sublotes criados | Peso total: {peso_total_criado:.2f}kg')

# 7. Atualizar a separação
percentual = (peso_total_criado / peso_pai * 100) if peso_pai > 0 else 0.0
cur.execute("""
    UPDATE lotes_separacao 
    SET status = 'FINALIZADA',
        peso_total_sublotes = %s,
        percentual_aproveitamento = %s,
        data_finalizacao = NOW(),
        observacoes = 'Sublotes criados via script de correção de bug - separação finalizada sem itens'
    WHERE id = %s
""", (peso_total_criado, percentual, SEP_ID))

# 8. Atualizar o lote pai de volta para PROCESSADO
cur.execute("UPDATE lotes SET status = 'PROCESSADO' WHERE id = %s", (LOTE_PAI_ID,))

print(f'\n[OK] Separação {SEP_ID} atualizada: peso_total_sublotes={peso_total_criado:.2f}kg, percentual={percentual:.1f}%')
print(f'[OK] Lote pai {LOTE_PAI_NUM} marcado como PROCESSADO')

# Confirmar
conn.commit()
print('\n' + '='*70)
print('[SUCESSO] Todos os dados commitados!')
print('='*70)
print(f'\nResumo:')
print(f'  Lote pai: {LOTE_PAI_NUM} (id={LOTE_PAI_ID})')
print(f'  Sublotes criados: {len(novos_sublotes)}')
print(f'  Peso total separado: {peso_total_criado:.2f}kg de {peso_pai:.2f}kg ({percentual:.1f}%)')

# Verificar
cur.execute("SELECT count(*) FROM lotes WHERE lote_pai_id = %s", (LOTE_PAI_ID,))
print(f'\n[VERIFICACAO] Sublotes no BD: {cur.fetchone()[0]}')
cur.execute("SELECT status FROM lotes WHERE id = %s", (LOTE_PAI_ID,))
print(f'[VERIFICACAO] Status lote pai: {cur.fetchone()[0]}')
cur.execute("SELECT status, peso_total_sublotes FROM lotes_separacao WHERE id = %s", (SEP_ID,))
sep_final = cur.fetchone()
print(f'[VERIFICACAO] Separação: status={sep_final[0]}, peso_sublotes={sep_final[1]}')

conn.close()
print('\nFIM - Lote corrigido com sucesso!')
