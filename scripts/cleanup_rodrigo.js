
const { Client } = require('pg');

const connectionString = "postgresql://postgres:dWldGAyqtVAsQvMYvTIqBKXTkHedCLAS@shortline.proxy.rlwy.net:26559/railway";
const SUPPLIER_ID = 92;

async function runCleanup() {
    const client = new Client({ 
        connectionString,
        ssl: { rejectUnauthorized: false },
        connectionTimeoutMillis: 10000,
    });

    try {
        await client.connect();
        console.log("Conectado ao banco de dados Railway.");

        // Iniciar Transação
        await client.query('BEGIN');

        console.log(`Iniciando limpeza para o Fornecedor ID: ${SUPPLIER_ID}`);

        // 1. Coleta de IDs para deleções em cascata manual (onde não há ON DELETE CASCADE)

        // Lotes do fornecedor
        const loteRes = await client.query("SELECT id FROM lotes WHERE fornecedor_id = $1", [SUPPLIER_ID]);
        const loteIds = loteRes.rows.map(r => r.id);
        console.log(`- Encontrados ${loteIds.length} lotes.`);

        // Solicitações do fornecedor
        const solRes = await client.query("SELECT id FROM solicitacoes WHERE fornecedor_id = $1", [SUPPLIER_ID]);
        const solIds = solRes.rows.map(r => r.id);
        console.log(`- Encontradas ${solIds.length} solicitações.`);

        // Ordens de Compra do fornecedor
        const ocRes = await client.query("SELECT id FROM ordens_compra WHERE fornecedor_id = $1", [SUPPLIER_ID]);
        const ocIds = ocRes.rows.map(r => r.id);
        console.log(`- Encontradas ${ocIds.length} ordens de compra.`);

        // Ordens de Serviço (via OCs)
        let osIds = [];
        if (ocIds.length > 0) {
            const osRes = await client.query("SELECT id FROM ordens_servico WHERE oc_id = ANY($1)", [ocIds]);
            osIds = osRes.rows.map(r => r.id);
        }
        console.log(`- Encontradas ${osIds.length} ordens de serviço.`);

        // Separações (via Lotes)
        let sepIds = [];
        if (loteIds.length > 0) {
            const sepRes = await client.query("SELECT id FROM lotes_separacao WHERE lote_id = ANY($1)", [loteIds]);
            sepIds = sepRes.rows.map(r => r.id);
        }
        console.log(`- Encontradas ${sepIds.length} separações.`);

        // --- EXECUÇÃO DAS DELEÇÕES (Ordem reversa de dependência) ---

        console.log("Executando deleções...");

        // Separação e Resíduos
        if (sepIds.length > 0) {
            await client.query("DELETE FROM residuos WHERE separacao_id = ANY($1)", [sepIds]);
            await client.query("DELETE FROM lotes_separacao WHERE id = ANY($1)", [sepIds]);
        }

        // Estoque e Movimentação (via Lotes)
        if (loteIds.length > 0) {
            await client.query("DELETE FROM entradas_estoque WHERE lote_id = ANY($1)", [loteIds]);
            await client.query("DELETE FROM movimentacoes_estoque WHERE lote_id = ANY($1)", [loteIds]);
            await client.query("DELETE FROM inventario_contagens WHERE lote_id = ANY($1)", [loteIds]);
        }

        // Lotes
        if (loteIds.length > 0) {
            await client.query("DELETE FROM lotes WHERE id = ANY($1)", [loteIds]);
        }

        // Logística (via OS)
        if (osIds.length > 0) {
            await client.query("DELETE FROM gps_logs WHERE os_id = ANY($1)", [osIds]);
            await client.query("DELETE FROM rotas_operacionais WHERE os_id = ANY($1)", [osIds]);
            await client.query("DELETE FROM conferencias_recebimento WHERE os_id = ANY($1)", [osIds]);
            await client.query("DELETE FROM ordens_servico WHERE id = ANY($1)", [osIds]);
        }

        // Compras (via OC e Solicitações)
        if (ocIds.length > 0) {
            await client.query("DELETE FROM auditoria_oc WHERE oc_id = ANY($1)", [ocIds]);
            await client.query("DELETE FROM ordens_compra WHERE id = ANY($1)", [ocIds]);
        }
        
        if (solIds.length > 0) {
            await client.query("DELETE FROM itens_solicitacao WHERE solicitacao_id = ANY($1)", [solIds]);
            await client.query("DELETE FROM solicitacoes WHERE id = ANY($1)", [solIds]);
        }

        // Tabelas de vínculo direto (não processuais que o plano cita)
        await client.query("DELETE FROM fornecedor_funcionario_atribuicao WHERE fornecedor_id = $1", [SUPPLIER_ID]);
        
        // Tabelas de classificação (opcional, mas o usuário pediu "apagar por completo todos os processos")
        // O plano cita manter a "tabela associada a ele" (tabela de preços), então manteremos fornecedor_tabela_precos.
        // E o perfil do fornecedor (fornecedores).

        await client.query('COMMIT');
        console.log("Limpeza concluída com sucesso e transação efetivada.");

    } catch (err) {
        await client.query('ROLLBACK');
        console.error("ERRO durante a limpeza (Rollback executado):", err.stack);
    } finally {
        await client.end();
    }
}

runCleanup();
