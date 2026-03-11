
const { Client } = require('pg');

// Using IP address directly to bypass DNS/proxy issues if possible
const connectionString = "postgresql://postgres:dWldGAyqtVAsQvMYvTIqBKXTkHedCLAS@66.33.22.244:26559/railway";
const SUPPLIER_ID = 92;

async function runCleanup() {
    console.log(`Iniciando limpeza direta via IP para ID: ${SUPPLIER_ID}`);
    const client = new Client({ 
        connectionString,
        ssl: { rejectUnauthorized: false },
        connectionTimeoutMillis: 60000,
        statement_timeout: 60000,
    });

    try {
        await client.connect();
        console.log("Conectado ao banco de dados (IP).");

        // Executando tudo em um bloco SQL para minimizar viagens de rede
        const sql = `
        DO $$
        BEGIN
            -- 1. Residuos
            DELETE FROM residuos WHERE separacao_id IN (SELECT id FROM lotes_separacao WHERE lote_id IN (SELECT id FROM lotes WHERE fornecedor_id = ${SUPPLIER_ID}));
            -- 2. Lotes Separacao
            DELETE FROM lotes_separacao WHERE lote_id IN (SELECT id FROM lotes WHERE fornecedor_id = ${SUPPLIER_ID});
            -- 3. Estoque
            DELETE FROM entradas_estoque WHERE lote_id IN (SELECT id FROM lotes WHERE fornecedor_id = ${SUPPLIER_ID});
            DELETE FROM movimentacoes_estoque WHERE lote_id IN (SELECT id FROM lotes WHERE fornecedor_id = ${SUPPLIER_ID});
            DELETE FROM inventario_contagens WHERE lote_id IN (SELECT id FROM lotes WHERE fornecedor_id = ${SUPPLIER_ID});
            -- 4. Logística
            DELETE FROM gps_logs WHERE os_id IN (SELECT id FROM ordens_servico WHERE oc_id IN (SELECT id FROM ordens_compra WHERE fornecedor_id = ${SUPPLIER_ID}));
            DELETE FROM rotas_operacionais WHERE os_id IN (SELECT id FROM ordens_servico WHERE oc_id IN (SELECT id FROM ordens_compra WHERE fornecedor_id = ${SUPPLIER_ID}));
            DELETE FROM conferencias_recebimento WHERE os_id IN (SELECT id FROM ordens_servico WHERE oc_id IN (SELECT id FROM ordens_compra WHERE fornecedor_id = ${SUPPLIER_ID}));
            -- 5. OS
            DELETE FROM ordens_servico WHERE oc_id IN (SELECT id FROM ordens_compra WHERE fornecedor_id = ${SUPPLIER_ID});
            -- 6. OC
            DELETE FROM auditoria_oc WHERE oc_id IN (SELECT id FROM ordens_compra WHERE fornecedor_id = ${SUPPLIER_ID});
            DELETE FROM ordens_compra WHERE fornecedor_id = ${SUPPLIER_ID};
            -- 7. Solicitação
            DELETE FROM itens_solicitacao WHERE solicitacao_id IN (SELECT id FROM solicitacoes WHERE fornecedor_id = ${SUPPLIER_ID});
            -- 8. Lotes
            DELETE FROM lotes WHERE fornecedor_id = ${SUPPLIER_ID};
            -- 9. Solicitacoes
            DELETE FROM solicitacoes WHERE fornecedor_id = ${SUPPLIER_ID};
            -- 10. Atribuicoes
            DELETE FROM fornecedor_funcionario_atribuicao WHERE fornecedor_id = ${SUPPLIER_ID};
        END $$;
        `;

        await client.query(sql);
        console.log("Limpeza realizada com sucesso.");

    } catch (err) {
        console.error("Erro durante a limpeza:", err.message);
    } finally {
        await client.end();
    }
}

runCleanup();
