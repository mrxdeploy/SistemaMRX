import psycopg2
import sys
import logging
from psycopg2.extras import DictCursor

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

DATABASE_URL = "postgresql://postgres:dWldGAyqtVAsQvMYvTIqBKXTkHedCLAS@shortline.proxy.rlwy.net:26559/railway"
FORNECEDOR_ID = 92

def cleanup():
    logging.info(f"Conectando ao banco de dados em {DATABASE_URL.split('@')[-1]}...")
    
    try:
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = False
        cursor = conn.cursor(cursor_factory=DictCursor)
        
        logging.info(f"Iniciando transação de limpeza para o fornecedor_id = {FORNECEDOR_ID} (RODRIGO GASPAR)...")
        
        # 1. Identificar IDs bases
        cursor.execute("SELECT id FROM lotes WHERE fornecedor_id = %s", (FORNECEDOR_ID,))
        lote_ids = [row['id'] for row in cursor.fetchall()]
        
        # Buscar sublotes também (caso haja)
        sublote_ids = []
        if lote_ids:
            cursor.execute("SELECT id FROM lotes WHERE lote_pai_id = ANY(%s)", (lote_ids,))
            sublote_ids = [row['id'] for row in cursor.fetchall()]
            lote_ids.extend(sublote_ids)
            lote_ids = list(set(lote_ids)) # remover duplicatas
            
        cursor.execute("SELECT id FROM ordens_compra WHERE fornecedor_id = %s", (FORNECEDOR_ID,))
        oc_ids = [row['id'] for row in cursor.fetchall()]
        
        cursor.execute("SELECT id FROM solicitacoes WHERE fornecedor_id = %s", (FORNECEDOR_ID,))
        solicitacao_ids = [row['id'] for row in cursor.fetchall()]

        os_ids = []
        if oc_ids:
            cursor.execute("SELECT id FROM ordens_servico WHERE oc_id = ANY(%s)", (oc_ids,))
            os_ids = [row['id'] for row in cursor.fetchall()]

        logging.info(f"IDs encontrados para exclusão: {len(lote_ids)} lotes, {len(oc_ids)} OCs, {len(solicitacao_ids)} solicitacoes, {len(os_ids)} OSs")

        # 2. Deletar dependências de Lotes e Solicitacoes (Estoque, Separação, Itens)
        if lote_ids:
            # Residuos de LoteSeparacao
            cursor.execute("DELETE FROM residuos WHERE separacao_id IN (SELECT id FROM lotes_separacao WHERE lote_id = ANY(%s))", (lote_ids,))
            logging.info(f"Deletados {cursor.rowcount} registros de residuos")
            
            # LotesSeparacao
            cursor.execute("DELETE FROM lotes_separacao WHERE lote_id = ANY(%s)", (lote_ids,))
            logging.info(f"Deletados {cursor.rowcount} registros de lotes_separacao")

            # MovimentacoesEstoque
            cursor.execute("DELETE FROM movimentacoes_estoque WHERE lote_id = ANY(%s)", (lote_ids,))
            logging.info(f"Deletados {cursor.rowcount} registros de movimentacoes_estoque")

            # EntradasEstoque
            cursor.execute("DELETE FROM entradas_estoque WHERE lote_id = ANY(%s)", (lote_ids,))
            logging.info(f"Deletados {cursor.rowcount} registros de entradas_estoque")

            # InventarioContagens
            cursor.execute("DELETE FROM inventario_contagens WHERE lote_id = ANY(%s)", (lote_ids,))
            logging.info(f"Deletados {cursor.rowcount} registros de inventario_contagens")

            # ItensSolicitacao via Lotes
            cursor.execute("DELETE FROM itens_solicitacao WHERE lote_id = ANY(%s)", (lote_ids,))
            logging.info(f"Deletados {cursor.rowcount} registros de itens_solicitacao vinculados a lotes")

        # ItensSolicitacao via Solicitacoes
        if solicitacao_ids:
            cursor.execute("DELETE FROM itens_solicitacao WHERE solicitacao_id = ANY(%s)", (solicitacao_ids,))
            logging.info(f"Deletados {cursor.rowcount} registros de itens_solicitacao vinculados a solicitacoes")

        # 3. Deletar dependências de Ordens de Servico e OCs
        if os_ids:
            cursor.execute("DELETE FROM rotas_operacionais WHERE os_id = ANY(%s)", (os_ids,))
            logging.info(f"Deletados {cursor.rowcount} registros de rotas_operacionais")

            cursor.execute("DELETE FROM gps_logs WHERE os_id = ANY(%s)", (os_ids,))
            logging.info(f"Deletados {cursor.rowcount} registros de gps_logs")

            cursor.execute("DELETE FROM conferencias_recebimento WHERE os_id = ANY(%s)", (os_ids,))
            logging.info(f"Deletados {cursor.rowcount} registros de conferencias_recebimento (via OS)")

            # Há um foreign key solto nas OS que apontam de Lotes para OS? Sim, ns models lotes tem os_id
            cursor.execute("UPDATE lotes SET os_id = NULL WHERE os_id = ANY(%s)", (os_ids,))

            cursor.execute("DELETE FROM ordens_servico WHERE id = ANY(%s)", (os_ids,))
            logging.info(f"Deletados {cursor.rowcount} registros de ordens_servico")

        if oc_ids:
            cursor.execute("DELETE FROM conferencias_recebimento WHERE oc_id = ANY(%s)", (oc_ids,))
            logging.info(f"Deletados {cursor.rowcount} registros de conferencias_recebimento (via OC)")

            cursor.execute("DELETE FROM auditoria_oc WHERE oc_id = ANY(%s)", (oc_ids,))
            logging.info(f"Deletados {cursor.rowcount} registros de auditoria_oc")

            # Update lotes to remove oc_id just in case
            cursor.execute("UPDATE lotes SET oc_id = NULL WHERE oc_id = ANY(%s)", (oc_ids,))

        # 4. Deletar as Entidades Principais vinculadas ao Fornecedor
        if sublote_ids:
            cursor.execute("DELETE FROM lotes WHERE id = ANY(%s)", (sublote_ids,))
            logging.info(f"Deletados {cursor.rowcount} registros de sublotes")

        logging.info("Deletando lotes pai...")
        cursor.execute("DELETE FROM lotes WHERE fornecedor_id = %s", (FORNECEDOR_ID,))
        logging.info(f"Deletados {cursor.rowcount} registros de lotes (fornecedor direto)")

        logging.info("Deletando ordens de compra (OCs)...")
        cursor.execute("DELETE FROM ordens_compra WHERE fornecedor_id = %s", (FORNECEDOR_ID,))
        logging.info(f"Deletados {cursor.rowcount} registros de ordens_compra")

        logging.info("Deletando solicitações...")
        cursor.execute("DELETE FROM solicitacoes WHERE fornecedor_id = %s", (FORNECEDOR_ID,))
        logging.info(f"Deletados {cursor.rowcount} registros de solicitacoes")
        
        logging.info("=== CONFIRMAÇÃO ===")
        logging.info("Perfil Fornecedor e Tabelas de Preço MANTIDOS INTACTOS.")
        logging.info("Operações (OC, OS, Lote, Estoque, etc.) APAGADAS com sucesso.")

        # Efetivar no banco:
        conn.commit()
        logging.info("Transação COMMIT efetuada. Alterações salvas no banco do Railway com sucesso!")
        
    except Exception as e:
        if 'conn' in locals() and conn:
            conn.rollback()
            logging.error("Ocorreu um erro, ROLLBACK executado.")
        logging.error(f"Erro detalhado: {e}")
        sys.exit(1)
    finally:
        if 'cursor' in locals() and cursor:
            cursor.close()
        if 'conn' in locals() and conn:
            conn.close()

if __name__ == "__main__":
    cleanup()
