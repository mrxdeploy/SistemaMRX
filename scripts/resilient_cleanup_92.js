
const { Client } = require('pg');

const connectionString = "postgresql://postgres:dWldGAyqtVAsQvMYvTIqBKXTkHedCLAS@shortline.proxy.rlwy.net:26559/railway";
const SUPPLIER_ID = 92;

async function runQuery(sql) {
    const client = new Client({ 
        connectionString,
        ssl: { rejectUnauthorized: false },
        connectionTimeoutMillis: 30000,
    });
    try {
        await client.connect();
        const res = await client.query(sql);
        await client.end();
        return res;
    } catch (err) {
        console.error(`Erro na query: ${err.message}`);
        try { await client.end(); } catch(e) {}
        throw err;
    }
}

async function runResilientCleanup() {
    console.log(`Iniciando limpeza resiliente para ID: ${SUPPLIER_ID}`);

    const steps = [
        {
            name: "Residuos",
            sql: `DELETE FROM residuos WHERE separacao_id IN (SELECT id FROM lotes_separacao WHERE lote_id IN (SELECT id FROM lotes WHERE fornecedor_id = ${SUPPLIER_ID}))`
        },
        {
            name: "Lotes Separacao",
            sql: `DELETE FROM lotes_separacao WHERE lote_id IN (SELECT id FROM lotes WHERE fornecedor_id = ${SUPPLIER_ID})`
        },
        {
            name: "Entradas Estoque",
            sql: `DELETE FROM entradas_estoque WHERE lote_id IN (SELECT id FROM lotes WHERE fornecedor_id = ${SUPPLIER_ID})`
        },
        {
            name: "Movimentacoes Estoque",
            sql: `DELETE FROM movimentacoes_estoque WHERE lote_id IN (SELECT id FROM lotes WHERE fornecedor_id = ${SUPPLIER_ID})`
        },
        {
            name: "Inventario Contagens",
            sql: `DELETE FROM inventario_contagens WHERE lote_id IN (SELECT id FROM lotes WHERE fornecedor_id = ${SUPPLIER_ID})`
        },
        {
            name: "GPS Logs",
            sql: `DELETE FROM gps_logs WHERE os_id IN (SELECT id FROM ordens_servico WHERE oc_id IN (SELECT id FROM ordens_compra WHERE fornecedor_id = ${SUPPLIER_ID}))`
        },
        {
            name: "Rotas Operacionais",
            sql: `DELETE FROM rotas_operacionais WHERE os_id IN (SELECT id FROM ordens_servico WHERE oc_id IN (SELECT id FROM ordens_compra WHERE fornecedor_id = ${SUPPLIER_ID}))`
        },
        {
            name: "Conferencias Recebimento",
            sql: `DELETE FROM conferencias_recebimento WHERE os_id IN (SELECT id FROM ordens_servico WHERE oc_id IN (SELECT id FROM ordens_compra WHERE fornecedor_id = ${SUPPLIER_ID}))`
        },
        {
            name: "Ordens Servico",
            sql: `DELETE FROM ordens_servico WHERE oc_id IN (SELECT id FROM ordens_compra WHERE fornecedor_id = ${SUPPLIER_ID})`
        },
        {
            name: "Auditoria OC",
            sql: `DELETE FROM auditoria_oc WHERE oc_id IN (SELECT id FROM ordens_compra WHERE fornecedor_id = ${SUPPLIER_ID})`
        },
        {
            name: "Ordens Compra",
            sql: `DELETE FROM ordens_compra WHERE fornecedor_id = ${SUPPLIER_ID}`
        },
        {
            name: "Itens Solicitacao",
            sql: `DELETE FROM itens_solicitacao WHERE solicitacao_id IN (SELECT id FROM solicitacoes WHERE fornecedor_id = ${SUPPLIER_ID})`
        },
        {
            name: "Lotes",
            sql: `DELETE FROM lotes WHERE fornecedor_id = ${SUPPLIER_ID}`
        },
        {
            name: "Solicitacoes",
            sql: `DELETE FROM solicitacoes WHERE fornecedor_id = ${SUPPLIER_ID}`
        },
        {
            name: "Atribuicoes",
            sql: `DELETE FROM fornecedor_funcionario_atribuicao WHERE fornecedor_id = ${SUPPLIER_ID}`
        }
    ];

    for (const step of steps) {
        console.log(`- Step: ${step.name}...`);
        let success = false;
        let retries = 3;
        while (!success && retries > 0) {
            try {
                const res = await runQuery(step.sql);
                console.log(`  OK: ${res.rowCount} rows deleted.`);
                success = true;
            } catch (err) {
                retries--;
                console.log(`  Falhou. Retrying (${retries} left)...`);
                if (retries === 0) {
                    console.error(`  ERRO FINAL no step ${step.name}: ${err.message}`);
                } else {
                    await new Promise(r => setTimeout(r, 2000));
                }
            }
        }
    }

    console.log("Limpeza finalizada.");
}

runResilientCleanup();
