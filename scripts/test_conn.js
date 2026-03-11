
const { Client } = require('pg');

const connectionString = "postgresql://postgres:dWldGAyqtVAsQvMYvTIqBKXTkHedCLAS@shortline.proxy.rlwy.net:26559/railway";

async function run() {
    const client = new Client({ 
        connectionString,
        ssl: { rejectUnauthorized: false }
    });
    try {
        await client.connect();
        console.log("Conectado com sucesso (SSL).");
        
        const res = await client.query("SELECT id, nome FROM fornecedores WHERE nome ILIKE '%RODRIGO GASPAR%'");
        console.log("Fornecedores encontrados:", res.rows);
        
        if (res.rows.length > 0) {
            const s_id = res.rows[0].id;
            const tables = ['solicitacoes', 'ordens_compra', 'lotes'];
            for (const table of tables) {
                const countRes = await client.query(`SELECT COUNT(*) FROM ${table} WHERE fornecedor_id = $1`, [s_id]);
                console.log(`${table}: ${countRes.rows[0].count}`);
            }
        }
    } catch (err) {
        console.error("Erro de conexão/consulta:", err.message);
    } finally {
        await client.end();
    }
}

run();
