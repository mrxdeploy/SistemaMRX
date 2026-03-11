
const { Client } = require('pg');

const connectionString = "postgresql://postgres:dWldGAyqtVAsQvMYvTIqBKXTkHedCLAS@shortline.proxy.rlwy.net:26559/railway";
const SUPPLIER_ID = 92;

async function runCleanup() {
    const client = new Client({ 
        connectionString,
        ssl: { rejectUnauthorized: false },
        connectionTimeoutMillis: 30000,
    });

    try {
        await client.connect();
        console.log("Conectado ao banco de dados Railway.");

        const sql = `
        BEGIN;

        -- 1. Residuos (via lotes_separacao -> lotes)
        DELETE FROM residuos WHERE separacao_id IN (
            SELECT id FROM lotes_separacao WHERE lote_id IN (
                SELECT id FROM lotes WHERE fornecedor_id = ${SUPPLIER_ID}
            )
        );

        -- 2. Lotes Separacao (via lotes)
        DELETE FROM lotes_separacao WHERE lote_id IN (
            SELECT id FROM lotes WHERE fornecedor_id = ${SUPPLIER_ID}
        );

        -- 3. Entradas, Movimentacoes, Inventario (via lotes)
        DELETE FROM entradas_estoque WHERE lote_id IN (
            SELECT id FROM lotes WHERE fornecedor_id = ${SUPPLIER_ID}
        );
        DELETE FROM movimentacoes_estoque WHERE lote_id IN (
            SELECT id FROM lotes WHERE fornecedor_id = ${SUPPLIER_ID}
        );
        DELETE FROM inventario_contagens WHERE lote_id IN (
            SELECT id FROM lotes WHERE fornecedor_id = ${SUPPLIER_ID}
        );

        -- 4. GPS Logs, Rotas, Conferencias (via ordens_servico -> ordens_compra)
        DELETE FROM gps_logs WHERE os_id IN (
            SELECT id FROM ordens_servico WHERE oc_id IN (
                SELECT id FROM ordens_compra WHERE fornecedor_id = ${SUPPLIER_ID}
            )
        );
        DELETE FROM rotas_operacionais WHERE os_id IN (
            SELECT id FROM ordens_servico WHERE oc_id IN (
                SELECT id FROM ordens_compra WHERE fornecedor_id = ${SUPPLIER_ID}
            )
        );
        DELETE FROM conferencias_recebimento WHERE os_id IN (
            SELECT id FROM ordens_servico WHERE oc_id IN (
                SELECT id FROM ordens_compra WHERE fornecedor_id = ${SUPPLIER_ID}
            )
        );

        -- 5. Ordens Servico (via ordens_compra)
        DELETE FROM ordens_servico WHERE oc_id IN (
            SELECT id FROM ordens_compra WHERE fornecedor_id = ${SUPPLIER_ID}
        );

        -- 6. Auditoria OC
        DELETE FROM auditoria_oc WHERE oc_id IN (
            SELECT id FROM ordens_compra WHERE fornecedor_id = ${SUPPLIER_ID}
        );

        -- 7. Ordens Compra
        DELETE FROM ordens_compra WHERE fornecedor_id = ${SUPPLIER_ID};

        -- 8. Itens Solicitacao (via solicitacoes)
        DELETE FROM itens_solicitacao WHERE solicitacao_id IN (
            SELECT id FROM solicitacoes WHERE fornecedor_id = ${SUPPLIER_ID}
        );

        -- 9. Lotes
        DELETE FROM lotes WHERE fornecedor_id = ${SUPPLIER_ID};

        -- 10. Solicitacoes
        DELETE FROM solicitacoes WHERE fornecedor_id = ${SUPPLIER_ID};

        -- 11. Atribuicoes
        DELETE FROM fornecedor_funcionario_atribuicao WHERE fornecedor_id = ${SUPPLIER_ID};

        COMMIT;
        `;

        console.log("Executando limpeza completa...");
        await client.query(sql);
        console.log("Limpeza concluída com sucesso.");

    } catch (err) {
        console.error("ERRO durante a limpeza:", err.message);
        try {
            await client.query('ROLLBACK');
        } catch (rollbackErr) {
            console.error("Erro ao executar ROLLBACK:", rollbackErr.message);
        }
    } finally {
        await client.end();
    }
}

runCleanup();
