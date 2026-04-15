from flask import Blueprint, jsonify
from app.models import db
from sqlalchemy import text

bp = Blueprint('cleanup_temp', __name__)

# Chave secreta para proteger o endpoint - delete após uso!
SECRET_KEY = "MRX_CLEANUP_2026_TEMP_APAGAR_LOTES_TESTE"

LOTES_ALVO = [
    '2026-03326',
    '2026-03327',
    '2026-03062',
    '2026-03061',
    '2026-03060'
]

@bp.route(f'/admin/cleanup-temp-{SECRET_KEY}', methods=['GET'])
def cleanup_test_lots():
    """
    ROTA TEMPORÁRIA - APAGAR APÓS USO!
    Remove completamente os lotes de teste e todo o fluxo associado.
    """
    log = []
    
    try:
        with db.engine.connect() as conn:
            # 1. Buscar IDs dos lotes alvo
            res = conn.execute(
                text("SELECT id, numero_lote, solicitacao_origem_id, oc_id, os_id, conferencia_id FROM lotes WHERE numero_lote = ANY(:nums)"),
                {"nums": LOTES_ALVO}
            )
            rows = res.fetchall()
            
            if not rows:
                return jsonify({"status": "ok", "mensagem": "Nenhum lote encontrado. Já foram removidos ou não existem."})
            
            lot_ids = [r[0] for r in rows]
            sol_ids = [r[2] for r in rows if r[2]]
            oc_ids  = [r[3] for r in rows if r[3]]
            os_ids  = [r[4] for r in rows if r[4]]
            conf_ids = [r[5] for r in rows if r[5]]
            
            log.append(f"Lotes encontrados: {[r[1] for r in rows]}")
            log.append(f"IDs: lots={lot_ids}, sol={sol_ids}, oc={oc_ids}, os={os_ids}, conf={conf_ids}")

            # ----------------------------------------------------------------
            # FASE 1: Remover filhos diretos dos lotes
            # ----------------------------------------------------------------

            # 1a. Residuos (filhos das separacoes)
            if lot_ids:
                sep_res = conn.execute(text("SELECT id FROM lotes_separacao WHERE lote_id = ANY(:ids)"), {"ids": lot_ids})
                sep_ids = [r[0] for r in sep_res.fetchall()]
                if sep_ids:
                    r = conn.execute(text("DELETE FROM residuos WHERE separacao_id = ANY(:ids)"), {"ids": sep_ids})
                    log.append(f"Residuos deletados: {r.rowcount}")
                    conn.commit()

            # 1b. Lotes separacao
            if lot_ids:
                r = conn.execute(text("DELETE FROM lotes_separacao WHERE lote_id = ANY(:ids)"), {"ids": lot_ids})
                log.append(f"LotesSeparacao deletados: {r.rowcount}")
                conn.commit()

            # 1c. Movimentacoes de estoque
            if lot_ids:
                r = conn.execute(text("DELETE FROM movimentacoes_estoque WHERE lote_id = ANY(:ids)"), {"ids": lot_ids})
                log.append(f"MovimentacoesEstoque deletadas: {r.rowcount}")
                conn.commit()

            # 1d. Entradas de estoque
            if lot_ids:
                r = conn.execute(text("DELETE FROM entradas_estoque WHERE lote_id = ANY(:ids)"), {"ids": lot_ids})
                log.append(f"EntradasEstoque deletadas: {r.rowcount}")
                conn.commit()

            # 1e. Itens de solicitacao ligados aos lotes
            if lot_ids:
                r = conn.execute(text("DELETE FROM itens_solicitacao WHERE lote_id = ANY(:ids)"), {"ids": lot_ids})
                log.append(f"ItensSolicitacao (via lote) deletados: {r.rowcount}")
                conn.commit()

            # 1f. Itens de solicitacao ligados às solicitacoes
            if sol_ids:
                r = conn.execute(text("DELETE FROM itens_solicitacao WHERE solicitacao_id = ANY(:ids)"), {"ids": sol_ids})
                log.append(f"ItensSolicitacao (via sol) deletados: {r.rowcount}")
                conn.commit()

            # ----------------------------------------------------------------
            # FASE 2: Remover os Lotes em si (zerar FK para conferencia e os)
            # ----------------------------------------------------------------
            if lot_ids:
                conn.execute(text("UPDATE lotes SET conferencia_id = NULL, os_id = NULL, oc_id = NULL, solicitacao_origem_id = NULL WHERE id = ANY(:ids)"), {"ids": lot_ids})
                r = conn.execute(text("DELETE FROM lotes WHERE id = ANY(:ids)"), {"ids": lot_ids})
                log.append(f"Lotes deletados: {r.rowcount}")
                conn.commit()

            # ----------------------------------------------------------------
            # FASE 3: Remover Logística (Conferências e Ordens de Serviço)
            # ----------------------------------------------------------------
            if conf_ids:
                r = conn.execute(text("DELETE FROM conferencias_recebimento WHERE id = ANY(:ids)"), {"ids": conf_ids})
                log.append(f"ConferenciasRecebimento deletadas: {r.rowcount}")
                conn.commit()

            if os_ids:
                r = conn.execute(text("DELETE FROM ordens_servico WHERE id = ANY(:ids)"), {"ids": os_ids})
                log.append(f"OrdensServico deletadas: {r.rowcount}")
                conn.commit()

            # ----------------------------------------------------------------
            # FASE 4: Remover Ordens de Compra
            # ----------------------------------------------------------------
            if oc_ids:
                try:
                    r = conn.execute(text("DELETE FROM auditoria_oc WHERE oc_id = ANY(:ids)"), {"ids": oc_ids})
                    log.append(f"AuditoriaOC deletada: {r.rowcount}")
                    conn.commit()
                except Exception as e:
                    log.append(f"AuditoriaOC skip: {str(e)}")
                    conn.rollback()

                r = conn.execute(text("DELETE FROM ordens_compra WHERE id = ANY(:ids)"), {"ids": oc_ids})
                log.append(f"OrdensCompra deletadas: {r.rowcount}")
                conn.commit()

            # ----------------------------------------------------------------
            # FASE 5: Remover Solicitações
            # ----------------------------------------------------------------
            if sol_ids:
                r = conn.execute(text("DELETE FROM solicitacoes WHERE id = ANY(:ids)"), {"ids": sol_ids})
                log.append(f"Solicitacoes deletadas: {r.rowcount}")
                conn.commit()

            # ----------------------------------------------------------------
            # VERIFICAÇÃO FINAL
            # ----------------------------------------------------------------
            verify = conn.execute(
                text("SELECT count(*) FROM lotes WHERE numero_lote = ANY(:nums)"),
                {"nums": LOTES_ALVO}
            )
            restantes = verify.fetchone()[0]
            log.append(f"Verificação final: {restantes} lotes restantes (deve ser 0)")

        return jsonify({
            "status": "✅ SUCESSO",
            "mensagem": "Todos os lotes de teste foram removidos completamente.",
            "lotes_removidos": [r[1] for r in rows],
            "log": log
        })

    except Exception as e:
        return jsonify({
            "status": "❌ ERRO",
            "mensagem": str(e),
            "log": log
        }), 500
