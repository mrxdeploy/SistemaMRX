import psycopg2
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

conn = psycopg2.connect('postgresql://postgres:dWldGAyqtVAsQvMYvTIqBKXTkHedCLAS@shortline.proxy.rlwy.net:26559/railway')
cur = conn.cursor()

def check_lote(lote_num):
    print(f"\n{'='*60}")
    print(f"ANÁLISE DO LOTE: {lote_num}")
    print(f"{'='*60}")
    
    # 1. Dados do lote principal
    cur.execute("""
        SELECT id, status, peso_total_kg, lote_pai_id, data_criacao 
        FROM lotes WHERE numero_lote = %s
    """, (lote_num,))
    lote = cur.fetchone()
    if not lote:
        print(f"Lote {lote_num} não encontrado no banco de dados!")
        return
        
    lote_id, status, peso, pai_id, criado = lote
    print(f"[LOTE PRINCIPAL] ID: {lote_id} | Status: {status} | Peso: {peso}kg | Lote Pai: {pai_id} | Criado em: {criado}")
    
    # 2. Dados da Separação
    cur.execute("""
        SELECT id, status, data_inicio, data_finalizacao, peso_total_sublotes 
        FROM lotes_separacao WHERE lote_id = %s
    """, (lote_id,))
    sep = cur.fetchone()
    if sep:
        sep_id, sep_status, ini, fim, peso_subs = sep
        print(f"\n[SEPARAÇÃO] ID: {sep_id} | Status: {sep_status}")
        print(f"  Início: {ini}")
        print(f"  Fim: {fim}")
        print(f"  Peso Sublotes na Separação: {peso_subs}kg")
        
        # Último evento de auditoria da separação
        cur.execute("SELECT auditoria FROM lotes_separacao WHERE id = %s", (sep_id,))
        audit = cur.fetchone()[0]
        if audit and len(audit) > 0:
            last_event = audit[-1]
            print(f"  Último evento de auditoria: {last_event.get('acao')} em {last_event.get('timestamp')}")
    else:
        print("\n[SEPARAÇÃO] Nenhuma separação encontrada para este lote!")

    # 3. Sublotes existentes no banco
    cur.execute("""
        SELECT count(*), sum(peso_total_kg) 
        FROM lotes WHERE lote_pai_id = %s
    """, (lote_id,))
    sub_count, sub_peso = cur.fetchone()
    print(f"\n[SUBLOTES] Quantidade no BD: {sub_count} sublote(s) | Peso total: {sub_peso or 0}kg")
    
    # 4. Itens da solicitação (Pedidos de Compra)
    cur.execute("""
        SELECT count(*), sum(peso_kg) 
        FROM itens_solicitacao WHERE lote_id = %s
    """, (lote_id,))
    it_count, it_peso = cur.fetchone()
    print(f"\n[ITENS DA OC] Quantidade vinculada: {it_count} item(ns) | Peso total: {it_peso or 0}kg")

# Analisar os dois lotes
check_lote('2026-05094')
check_lote('2026-05042')

conn.close()
