const { Client } = require('pg');

const config = {
    user: 'postgres',
    password: 'dWldGAyqtVAsQvMYvTIqBKXTkHedCLAS',
    host: 'shortline.proxy.rlwy.net',
    port: 26559,
    database: 'railway',
    ssl: { rejectUnauthorized: false },
    connectionTimeoutMillis: 30000,
};

async function main() {
    const client = new Client(config);
    await client.connect();
    console.log('OK Connected');

    // Just get tables and fornecedor columns in one shot
    const r = await client.query(`
        SELECT c.table_name, c.column_name
        FROM information_schema.columns c
        JOIN information_schema.tables t ON t.table_name = c.table_name AND t.table_schema = 'public'
        WHERE c.table_schema = 'public'
          AND c.column_name ILIKE '%fornecedor%'
        ORDER BY c.table_name, c.column_name;
    `);
    console.log('Colunas fornecedor:');
    r.rows.forEach(x => console.log(x.table_name, '.', x.column_name));

    const t = await client.query(`
        SELECT table_name FROM information_schema.tables 
        WHERE table_schema='public' ORDER BY table_name
    `);
    console.log('\nTabelas:', t.rows.map(x=>x.table_name).join(', '));

    await client.end();
}

main().catch(e => { console.error('ERRO:', e.message); process.exit(1); });
