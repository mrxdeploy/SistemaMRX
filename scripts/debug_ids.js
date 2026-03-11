const { Client } = require('pg');

const client = new Client({
  connectionString: 'postgresql://postgres:dWldGAyqtVAsQvMYvTIqBKXTkHedCLAS@shortline.proxy.rlwy.net:26559/railway',
  ssl: { rejectUnauthorized: false }
});

async function run() {
  await client.connect();
  
  console.log("--- Fornecedores RODRIGO GASPAR ---");
  const resForn = await client.query("SELECT id, nome FROM fornecedores WHERE nome ILIKE '%RODRIGO%'");
  console.table(resForn.rows);

  console.log("\n--- Lotes 2026-0000X ---");
  const lotes = ['2026-00009', '2026-00008', '2026-00007', '2026-00006'];
  const resLotes = await client.query("SELECT id, numero_lote, fornecedor_id, status FROM lotes WHERE numero_lote = ANY($1)", [lotes]);
  console.table(resLotes.rows);

  console.log("\n--- Todos os Lotes do Rodrigo (se for ID diferente de 92) ---");
  if (resForn.rows.length > 0) {
      for (const f of resForn.rows) {
          const rL = await client.query("SELECT id, numero_lote, fornecedor_id, status FROM lotes WHERE fornecedor_id = $1", [f.id]);
          console.table(rL.rows);
      }
  }

  await client.end();
}

run().catch(console.error);
