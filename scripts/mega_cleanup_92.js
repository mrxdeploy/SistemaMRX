
const { Pool } = require('pg');

const connectionString = "postgresql://postgres:dWldGAyqtVAsQvMYvTIqBKXTkHedCLAS@shortline.proxy.rlwy.net:26559/railway";
const SUPPLIER_ID = 92;

const pool = new Pool({
    connectionString,
    ssl: { rejectUnauthorized: false },
    max: 1,
    connectionTimeoutMillis: 30000,
    idleTimeoutMillis: 30000,
});

async function runCleanup() {
    console.log(`Iniciando limpeza granular para Fornecedor ID: ${SUPPLIER_ID}`);

    const queries = [
        ["Residuos", `DELETE FROM residuos WHERE separacao_id IN (SELECT id FROM lotes_separacao WHERE lote_id IN (SELECT id FROM lotes WHERE fornecedor_id = ${SUPPLIER_ID}))`],
        ["Lotes Separacao", `DELETE FROM lotes_separacao WHERE lote_id IN (SELECT id FROM lotes WHERE fornecedor_id = ${SUPPLIER_ID})`],
        ["Entradas Estoque", `DELETE FROM entradas_estoque WHERE lote_id IN (SELECT id FROM lotes WHERE fornecedor_id = ${SUPPLIER_ID})`],
        ["Movimentacoes Estoque", `DELETE FROM movimentacoes_estoque WHERE lote_id IN (SELECT id FROM lotes WHERE fornecedor_id = ${SUPPLIER_ID})`],
        ["Inventario Contagens", `DELETE FROM inventario_contagens WHERE lote_id IN (SELECT id FROM lotes WHERE fornecedor_id = ${SUPPLIER_ID})`],
        ["GPS Logs", `DELETE FROM gps_logs WHERE os_id IN (SELECT id FROM ordens_servico WHERE oc_id IN (SELECT id FROM ordens_compra WHERE fornecedor_id = ${SUPPLIER_ID}))`],
        ["Rotas Operacionais", `DELETE FROM rotas_operacionais WHERE os_id IN (SELECT id FROM ordens_servico WHERE oc_id IN (SELECT id FROM ordens_compra WHERE fornecedor_id = ${SUPPLIER_ID}))`],
        ["Conferencias Recebimento", `DELETE FROM conferencias_recebimento WHERE os_id IN (SELECT id FROM ordens_servico WHERE oc_id IN (SELECT id FROM ordens_compra WHERE fornecedor_id = ${SUPPLIER_ID}))`],
        ["Ordens Servico", `DELETE FROM ordens_servico WHERE oc_id IN (SELECT id FROM ordens_compra WHERE fornecedor_id = ${SUPPLIER_ID})`],
        ["Auditoria OC", `DELETE FROM auditoria_oc WHERE oc_id IN (SELECT id FROM ordens_compra WHERE fornecedor_id = ${SUPPLIER_ID})`],
        ["Ordens Compra", `DELETE FROM ordens_compra WHERE fornecedor_id = ${SUPPLIER_ID}`],
        ["Itens Solicitacao", `DELETE FROM itens_solicitacao WHERE solicitacao_id IN (SELECT id FROM solicitacoes WHERE fornecedor_id = ${SUPPLIER_ID})`],
        ["Lotes", `DELETE FROM lotes WHERE fornecedor_id = ${SUPPLIER_ID}`],
        ["Solicitacoes", `DELETE FROM solicitacoes WHERE fornecedor_id = ${SUPPLIER_ID}`],
        ["Atribuicoes", `DELETE FROM fornecedor_funcionario_atribuicao WHERE fornecedor_id = ${SUPPLIER_ID}`]
    ];

    for (const [name, sql] of queries) {
        let done = false;
        let attempts = 0;
        console.log(`Executando: ${name}...`);
        while (!done && attempts < 5) {
            attempts++;
            try {
                const res = await pool.query(sql);
                console.log(`  Sucesso: ${res.rowCount} linhas removidas.`);
                done = true;
            } catch (err) {
                console.error(`  Tentativa ${attempts} falhou: ${err.message}`);
                if (attempts >= 5) {
                    console.error(`  Desistindo de ${name}.`);
                } else {
                    await new Promise(resolve => setTimeout(resolve, 3000));
                }
            }
        }
    }

    await pool.end();
    console.log("Processo finalizado.");
}

runCleanup().catch(err => {
    console.error("Erro fatal:", err.message);
    process.exit(1);
});
