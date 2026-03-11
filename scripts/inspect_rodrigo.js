
const { Client } = require('pg');

const connectionString = "postgresql://postgres:dWldGAyqtVAsQvMYvTIqBKXTkHedCLAS@shortline.proxy.rlwy.net:26559/railway";

async function inspect() {
    const client = new Client({ connectionString });
    await client.connect();

    try {
        // 1. Find supplier
        const resFornecedor = await client.query("SELECT id, nome FROM fornecedores WHERE nome ILIKE '%RODRIGO GASPAR%'");
        if (resFornecedor.rows.length === 0) {
            console.log("Fornecedor 'RODRIGO GASPAR' não encontrado.");
            return;
        }

        for (const fornecedor of resFornecedor.rows) {
            const s_id = fornecedor.id;
            console.log(`\nAnalisando Fornecedor: ${fornecedor.nome} (ID: ${s_id})`);

            // Tables with direct supplier_id
            const directTables = [
                ['solicitacoes', 'fornecedor_id'],
                ['ordens_compra', 'fornecedor_id'],
                ['lotes', 'fornecedor_id'],
                ['fornecedor_tipo_lote_precos', 'fornecedor_id'],
                ['fornecedor_tabela_precos', 'fornecedor_id'],
                ['fornecedor_tipo_lote', 'fornecedor_id'],
                ['fornecedor_classificacao_estrela', 'fornecedor_id'],
                ['fornecedor_funcionario_atribuicao', 'fornecedor_id']
            ];

            for (const [table, col] of directTables) {
                const countRes = await client.query(`SELECT COUNT(*) FROM ${table} WHERE ${col} = $1`, [s_id]);
                console.log(`  Tabela ${table}: ${countRes.rows[0].count} registros`);
            }

            // Indirect: via solicitacoes -> itens_solicitacao
            const solRes = await client.query("SELECT id FROM solicitacoes WHERE fornecedor_id = $1", [s_id]);
            const solIds = solRes.rows.map(r => r.id);
            if (solIds.length > 0) {
                const itemSolRes = await client.query(`SELECT COUNT(*) FROM itens_solicitacao WHERE solicitacao_id = ANY($1)`, [solIds]);
                console.log(`  Tabela itens_solicitacao: ${itemSolRes.rows[0].count} registros`);
            }

            // Indirect: via ordens_compra -> ordens_servico -> logs/conferencias
            const ocRes = await client.query("SELECT id FROM ordens_compra WHERE fornecedor_id = $1", [s_id]);
            const ocIds = ocRes.rows.map(r => r.id);
            if (ocIds.length > 0) {
                const osRes = await client.query("SELECT id FROM ordens_servico WHERE oc_id = ANY($1)", [ocIds]);
                const osIds = osRes.rows.map(r => r.id);
                console.log(`  Tabela ordens_servico: ${osRes.rows.length} registros`);
                
                if (osIds.length > 0) {
                    const osSubTables = ['gps_logs', 'rotas_operacionais', 'conferencias_recebimento'];
                    for (const table of osSubTables) {
                        const subCount = await client.query(`SELECT COUNT(*) FROM ${table} WHERE os_id = ANY($1)`, [osIds]);
                        console.log(`    Tabela ${table}: ${subCount.rows[0].count} registros`);
                    }
                }
            }

            // Indirect: via lotes -> estoque/movimentacao/separacao
            const loteRes = await client.query("SELECT id FROM lotes WHERE fornecedor_id = $1", [s_id]);
            const loteIds = loteRes.rows.map(r => r.id);
            if (loteIds.length > 0) {
                const loteSubTables = ['entradas_estoque', 'movimentacoes_estoque', 'lotes_separacao', 'inventario_contagens'];
                for (const table of loteSubTables) {
                    const subCount = await client.query(`SELECT COUNT(*) FROM ${table} WHERE lote_id = ANY($1)`, [loteIds]);
                    console.log(`  Tabela ${table}: ${subCount.rows[0].count} registros`);
                }

                // via lotes_separacao -> residuos
                const sepRes = await client.query("SELECT id FROM lotes_separacao WHERE lote_id = ANY($1)", [loteIds]);
                const sepIds = sepRes.rows.map(r => r.id);
                if (sepIds.length > 0) {
                    const resCount = await client.query(`SELECT COUNT(*) FROM residuos WHERE separacao_id = ANY($1)`, [sepIds]);
                    console.log(`    Tabela residuos: ${resCount.rows[0].count} registros`);
                }
            }
        }

    } catch (err) {
        console.error(err);
    } finally {
        await client.end();
    }
}

inspect();
