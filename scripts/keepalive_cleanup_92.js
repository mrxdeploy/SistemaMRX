
const { Client } = require('pg');
const net = require('net');

const SUPPLIER_ID = 92;

// Parse the connection string manually 
const config = {
    user: 'postgres',
    password: 'dWldGAyqtVAsQvMYvTIqBKXTkHedCLAS',
    host: 'shortline.proxy.rlwy.net',
    port: 26559,
    database: 'railway',
    ssl: { rejectUnauthorized: false },
    connectionTimeoutMillis: 60000,
};

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

async function execOne(name, sql) {
    return new Promise((resolve, reject) => {
        const client = new Client(config);
        
        // Enable TCP keepalive at socket level
        client.on('connect', () => {
            if (client.connection && client.connection.stream) {
                const sock = client.connection.stream;
                sock.setKeepAlive(true, 10000);
                sock.setTimeout(120000);
            }
        });
        
        client.connect()
            .then(() => client.query(sql))
            .then(res => {
                console.log(`  ✓ ${name}: ${res.rowCount} rows`);
                return client.end();
            })
            .then(resolve)
            .catch(err => {
                console.error(`  ✗ ${name}: ${err.message}`);
                client.end().catch(() => {});
                reject(err);
            });
    });
}

async function sleep(ms) {
    return new Promise(r => setTimeout(r, ms));
}

async function main() {
    console.log(`=== Limpeza Fornecedor ID ${SUPPLIER_ID} ===`);

    for (const [name, sql] of queries) {
        console.log(`• ${name}...`);
        let success = false;
        for (let attempt = 1; attempt <= 5 && !success; attempt++) {
            try {
                await execOne(name, sql);
                success = true;
            } catch (err) {
                if (attempt < 5) {
                    console.log(`  Aguardando 5s antes de nova tentativa...`);
                    await sleep(5000);
                } else {
                    console.error(`  FALHOU definitivamente: ${name}`);
                }
            }
        }
    }

    console.log('=== Concluído ===');
}

main().catch(err => console.error('Fatal:', err.message));
