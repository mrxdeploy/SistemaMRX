
import psycopg2
from psycopg2.extras import RealDictCursor

db_url = "postgresql://postgres:dWldGAyqtVAsQvMYvTIqBKXTkHedCLAS@shortline.proxy.rlwy.net:26559/railway"

def inspect_supplier():
    conn = psycopg2.connect(db_url)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # 1. Find supplier ID
    cur.execute("SELECT id, nome FROM fornecedores WHERE nome ILIKE %s", ('%RODRIGO GASPAR%',))
    suppliers = cur.fetchall()
    
    if not suppliers:
        print("Supplier 'RODRIGO GASPAR' not found.")
        return
    
    for supplier in suppliers:
        s_id = supplier['id']
        name = supplier['nome']
        print(f"Checking Supplier: {name} (ID: {s_id})")
        
        # Counts in various tables
        tables = [
            ('solicitacoes', 'fornecedor_id'),
            ('ordens_compra', 'fornecedor_id'),
            ('lotes', 'fornecedor_id'),
            ('fornecedor_tipo_lote_precos', 'fornecedor_id'),
            ('fornecedor_tabela_precos', 'fornecedor_id'),
            ('fornecedor_tipo_lote', 'fornecedor_id'),
            ('fornecedor_classificacao_estrela', 'fornecedor_id'),
            ('fornecedor_funcionario_atribuicao', 'fornecedor_id')
        ]
        
        for table, col in tables:
            cur.execute(f"SELECT COUNT(*) FROM {table} WHERE {col} = %s", (s_id,))
            count = cur.fetchone()['count']
            print(f"  Table {table}: {count} records")

        # Indirectly related (via solicitacoes)
        cur.execute("SELECT id FROM solicitacoes WHERE fornecedor_id = %s", (s_id,))
        sol_ids = [r['id'] for r in cur.fetchall()]
        if sol_ids:
            cur.execute("SELECT COUNT(*) FROM itens_solicitacao WHERE solicitacao_id IN %s", (tuple(sol_ids),))
            count = cur.fetchone()['count']
            print(f"  Table itens_solicitacao: {count} records")

        # Indirectly related (via ordens_compra)
        cur.execute("SELECT id FROM ordens_compra WHERE fornecedor_id = %s", (s_id,))
        oc_ids = [r['id'] for r in cur.fetchall()]
        if oc_ids:
            cur.execute("SELECT COUNT(*) FROM ordens_servico WHERE oc_id IN %s", (tuple(oc_ids),))
            count = cur.fetchone()['count']
            print(f"  Table ordens_servico: {count} records")
            
            # Via OS
            cur.execute("SELECT id FROM ordens_servico WHERE oc_id IN %s", (tuple(oc_ids),))
            os_ids = [r['id'] for r in cur.fetchall()]
            if os_ids:
                for t in ['gps_logs', 'rotas_operacionais', 'conferencias_recebimento']:
                    cur.execute(f"SELECT COUNT(*) FROM {t} WHERE os_id IN %s", (tuple(os_ids),))
                    count = cur.fetchone()['count']
                    print(f"    Table {t}: {count} records")

        # Indirectly related (via lotes)
        cur.execute("SELECT id FROM lotes WHERE fornecedor_id = %s", (s_id,))
        lote_ids = [r['id'] for r in cur.fetchall()]
        if lote_ids:
            for t in ['entradas_estoque', 'movimentacoes_estoque', 'lotes_separacao', 'inventario_contagens']:
                cur.execute(f"SELECT COUNT(*) FROM {t} WHERE lote_id IN %s", (tuple(lote_ids),))
                count = cur.fetchone()['count']
                print(f"  Table {t}: {count} records")
            
            # Via Lotes Separacao
            cur.execute("SELECT id FROM lotes_separacao WHERE lote_id IN %s", (tuple(lote_ids),))
            sep_ids = [r['id'] for r in cur.fetchall()]
            if sep_ids:
                cur.execute("SELECT COUNT(*) FROM residuos WHERE separacao_id IN %s", (tuple(sep_ids),))
                count = cur.fetchone()['count']
                print(f"    Table residuos: {count} records")

    cur.close()
    conn.close()

if __name__ == "__main__":
    inspect_supplier()
