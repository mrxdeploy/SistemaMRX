import psycopg2

conn = psycopg2.connect('postgresql://postgres:dWldGAyqtVAsQvMYvTIqBKXTkHedCLAS@shortline.proxy.rlwy.net:26559/railway')
cur = conn.cursor()

print('=' * 70)
print('DIAGNÓSTICO DEFINITIVO - POR QUE O SYNC NAO CRIOU SUBLOTES?')
print('=' * 70)

# O sync-sublotes faz:
# itens = lote_pai.itens  (itens_solicitacao com lote_id=6511)
# for item in itens: cria sublote
# MAS: ele checa primeiro se sublotes_existentes_query.all() -> se tiver, nao cria

# PASSO 1: Verificar se o sync foi chamado ANTES de algum sublote existir
# A auditoria da separacao 156 mostra apenas 3 eventos, nenhum é SUBLOTE_CRIADO
# Isso significa que o sync foi chamado MAS os sublotes nao foram criados

# HIPOTESE: o sync falhou silenciosamente por causa de algum item com problema

# Verificar itens do lote 6511 - algum tem peso_kg = 0 ou None?
print('\n[1] Verificando itens problemáticos do lote 6511:')
cur.execute("""
    SELECT is_.id, mb.nome, is_.peso_kg, is_.material_id, is_.tipo_lote_id,
           is_.valor_calculado
    FROM itens_solicitacao is_
    LEFT JOIN materiais_base mb ON mb.id = is_.material_id
    WHERE is_.lote_id = 6511
    ORDER BY is_.id
""")
itens = cur.fetchall()
print(f'  Total de itens: {len(itens)}')
problemas = []
for it in itens:
    peso_ok = it[2] is not None and float(it[2]) > 0
    mat_ok = it[3] is not None
    if not peso_ok or not mat_ok:
        problemas.append(it)
        print(f'  ⚠️ PROBLEMA - item_id={it[0]}: mat={it[1]}, peso={it[2]}, mat_id={it[3]}, tipo_id={it[4]}, valor={it[5]}')
    
if not problemas:
    print('  ✅ Todos os itens têm peso e material OK')

# PASSO 2: Verificar se os materiais do lote existem em materiais_base
print('\n[2] Verificando materiais_base:')
cur.execute("""
    SELECT is_.id, mb.id as mat_id, mb.nome, mb.ativo
    FROM itens_solicitacao is_
    LEFT JOIN materiais_base mb ON mb.id = is_.material_id
    WHERE is_.lote_id = 6511
    ORDER BY is_.id
""")
for row in cur.fetchall():
    if not row[3]:  # não ativo
        print(f'  ⚠️ Material INATIVO - item={row[0]}, mat_id={row[1]}, nome={row[2]}')
    
# PASSO 3: Verificar TipoLote - qual é o tipo_lote_id do pai?
print('\n[3] Tipo lote do lote pai (6511):')
cur.execute("SELECT tipo_lote_id, tipo_lote_id FROM lotes WHERE id = 6511")
r = cur.fetchone()
print(f'  tipo_lote_id: {r[0]}')

# PASSO 4: O REAL PROBLEMA - verificar o codigo do sync-sublotes
# O sync só cria sublotes se sublotes_existentes_query.all() retornar VAZIO
# Mas o sync é chamado ANTES de criar sublotes, então deveria funcionar

# PASSO 5: Verificar se o sync foi chamado e deu erro silencioso
# O endpoint /sync-sublotes verifica: status in ['AGUARDANDO_SEPARACAO', 'EM_SEPARACAO']
print('\n[4] Status da separação quando o sync foi chamado:')
cur.execute("SELECT status FROM lotes_separacao WHERE id = 156")
print(f'  Status atual: {cur.fetchone()[0]}')
# Status era EM_SEPARACAO quando o operador abriu a tela -> sync deveria funcionar

# PASSO 6: SIMULACAO - o que o sync teria feito
print('\n[5] SIMULAÇÃO DO SYNC-SUBLOTES:')
cur.execute("""
    SELECT is_.id, mb.nome, is_.peso_kg
    FROM itens_solicitacao is_
    LEFT JOIN materiais_base mb ON mb.id = is_.material_id
    WHERE is_.lote_id = 6511
    ORDER BY is_.id
""")
itens2 = cur.fetchall()
print(f'  Itens que o sync processaria: {len(itens2)}')
# O sync cria um sublote para cada item -> deveria criar 25 sublotes

# PASSO 7: Verificar se houve erro de numero_lote duplicado (race condition)
print('\n[6] Verificar lotes criados entre 18:52 e 18:53 (janela da separação):')
cur.execute("""
    SELECT id, numero_lote, status, lote_pai_id, data_criacao
    FROM lotes
    WHERE data_criacao >= '2026-05-07 18:52:00'
    AND data_criacao <= '2026-05-07 18:54:00'
    ORDER BY data_criacao
""")
lotes = cur.fetchall()
print(f'  Lotes criados neste período: {len(lotes)}')
for l in lotes:
    print(f'    id={l[0]}, num={l[1]}, status={l[2]}, pai={l[3]}, criado={l[4]}')

# PASSO 8: Verificar se o sync foi bloqueado porque a separacao ja estava em outro status
# Ou se o lote.itens retorna os itens correctamente
print('\n[7] Verificar lotes-separacao com status EM_SEPARACAO no momento da separacao:')
cur.execute("""
    SELECT id, lote_id, status, data_inicio, data_finalizacao
    FROM lotes_separacao
    WHERE status = 'EM_SEPARACAO'
    OR (data_inicio >= '2026-05-07 18:00:00' AND data_inicio <= '2026-05-07 19:00:00')
    ORDER BY data_inicio
""")
for row in cur.fetchall():
    print(f'  sep_id={row[0]}, lote_id={row[1]}, status={row[2]}, inicio={row[3]}, fim={row[4]}')

# CONCLUSAO DEFINITIVA
print('\n' + '='*70)
print('CONCLUSÃO DEFINITIVA:')
print('='*70)
print('''
  O lote 2026-05060 tem 25 itens válidos vinculados (lote_id=6511).
  
  O fluxo da tela separacao-workflow.html:
  1. Abre tela -> chama sincronizarSublotes() -> POST /sync-sublotes
  2. O sync DEVERIA criar 25 sublotes automaticamente
  
  POR QUE NÃO CRIOU:
  A separação (id=156) foi iniciada em 18:52:58 e finalizada em 18:53:20.
  O sync-sublotes foi chamado ao abrir a tela, mas:
  
  ⚠️ HIPÓTESE MAIS PROVÁVEL: O operador NÃO abriu a tela de workflow
  (separacao-workflow.html). Ele pode ter finalizado a separação DIRETAMENTE
  via outro caminho (ex: botão na fila), passando confirmar_sem_sublotes=True.
  
  Ou a tela abriu mas o sync deu erro silencioso e o operador não viu.
  
  SOLUÇÃO NECESSÁRIA:
  1. Reverter o lote 2026-05060 para EM_SEPARACAO  
  2. Criar os 25 sublotes a partir dos itens da solicitação
  3. Marcar o lote como PROCESSADO novamente
''')
conn.close()
