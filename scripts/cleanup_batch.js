
const { Client } = require('pg');

const connectionString = "postgresql://postgres:dWldGAyqtVAsQvMYvTIqBKXTkHedCLAS@shortline.proxy.rlwy.net:26559/railway";
const SUPPLIER_ID = 92;

async function executeWithRetry(query, params = []) {
    let retries = 3;
    while (retries > 0) {
        const client = new Client({ 
            connectionString,
            ssl: { rejectUnauthorized: false },
            connectionTimeoutMillis: 10000,
        });
        
        try {
            await client.connect();
            const res = await client.query(query, params);
            await client.end();
            return res;
        } catch (err) {
            retries--;
            console.error(`Falha na query (restam ${retries} tentativas): ${err.message}`);
            try { await client.end(); } catch(e) {}
            if (retries === 0) throw err;
            await new Promise(resolve => setTimeout(resolve, 2000));
        }
    }
}

async function runBatchCleanup() {
    console.log(`Iniciando limpeza em lotes para o Fornecedor ID: ${SUPPLIER_ID}`);

    try {
        // IDs
        console.log("Coletando IDs...");
        const loteRes = await executeWithRetry("SELECT id FROM lotes WHERE fornecedor_id = $1", [SUPPLIER_ID]);
        const loteIds = loteRes.rows.map(r => r.id);
        
        const solRes = await executeWithRetry("SELECT id FROM solicitacoes WHERE fornecedor_id = $1", [SUPPLIER_ID]);
        const solIds = solRes.rows.map(r => r.id);

        const ocRes = await executeWithRetry("SELECT id FROM ordens_compra WHERE fornecedor_id = $1", [SUPPLIER_ID]);
        const ocIds = ocRes.rows.map(r => r.id);

        let osIds = [];
        if (ocIds.length > 0) {
            const osRes = await executeWithRetry("SELECT id FROM ordens_servico WHERE oc_id = ANY($1)", [ocIds]);
            osIds = osRes.rows.map(r => r.id);
        }

        let sepIds = [];
        if (loteIds.length > 0) {
            const sepRes = await executeWithRetry("SELECT id FROM lotes_separacao WHERE lote_id = ANY($1)", [loteIds]);
            sepIds = sepRes.rows.map(r => r.id);
        }

        console.log(`Resumo: ${loteIds.length} lotes, ${solIds.length} solicitações, ${ocIds.length} OCs, ${osIds.length} OSs, ${sepIds.length} separações.`);

        // Deleções individuais (para evitar transações longas que caem)
        
        if (sepIds.length > 0) {
            console.log("Limpando separação...");
            await executeWithRetry("DELETE FROM residuos WHERE separacao_id = ANY($1)", [sepIds]);
            await executeWithRetry("DELETE FROM lotes_separacao WHERE id = ANY($1)", [sepIds]);
        }

        if (loteIds.length > 0) {
            console.log("Limpando estoque...");
            await executeWithRetry("DELETE FROM entradas_estoque WHERE lote_id = ANY($1)", [loteIds]);
            await executeWithRetry("DELETE FROM movimentacoes_estoque WHERE lote_id = ANY($1)", [loteIds]);
            await executeWithRetry("DELETE FROM inventario_contagens WHERE lote_id = ANY($1)", [loteIds]);
            console.log("Removendo lotes...");
            await executeWithRetry("DELETE FROM lotes WHERE id = ANY($1)", [loteIds]);
        }

        if (osIds.length > 0) {
            console.log("Limpando logística...");
            await executeWithRetry("DELETE FROM gps_logs WHERE os_id = ANY($1)", [osIds]);
            await executeWithRetry("DELETE FROM rotas_operacionais WHERE os_id = ANY($1)", [osIds]);
            await executeWithRetry("DELETE FROM conferencias_recebimento WHERE os_id = ANY($1)", [osIds]);
            await executeWithRetry("DELETE FROM ordens_servico WHERE id = ANY($1)", [osIds]);
        }

        if (ocIds.length > 0) {
            console.log("Limpando auditoria OC...");
            await executeWithRetry("DELETE FROM auditoria_oc WHERE oc_id = ANY($1)", [ocIds]);
            console.log("Removendo OCs...");
            await executeWithRetry("DELETE FROM ordens_compra WHERE id = ANY($1)", [ocIds]);
        }

        if (solIds.length > 0) {
            console.log("Limpando itens de solicitação...");
            await executeWithRetry("DELETE FROM itens_solicitacao WHERE solicitacao_id = ANY($1)", [solIds]);
            console.log("Removendo solicitações...");
            await executeWithRetry("DELETE FROM solicitacoes WHERE id = ANY($1)", [solIds]);
        }

        console.log("Limpando atribuições...");
        await executeWithRetry("DELETE FROM fornecedor_funcionario_atribuicao WHERE fornecedor_id = $1", [SUPPLIER_ID]);

        console.log("LIMPEZA CONCLUÍDA!");

    } catch (err) {
        console.error("ERRO CRÍTICO na limpeza:", err.message);
    }
}

runBatchCleanup();
