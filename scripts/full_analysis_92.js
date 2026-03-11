const { Client } = require('pg');

const SUPPLIER_ID = 92;

const config = {
    user: 'postgres',
    password: 'dWldGAyqtVAsQvMYvTIqBKXTkHedCLAS',
    host: 'shortline.proxy.rlwy.net',
    port: 26559,
    database: 'railway',
    ssl: { rejectUnauthorized: false },
    connectionTimeoutMillis: 60000,
    query_timeout: 30000,
};

async function main() {
    const client = new Client(config);
    try {
        await client.connect();
        console.log('Conectado ao banco!\n');

        // 1. Fornecedor
        const sup = await client.query('SELECT id, nome FROM fornecedores WHERE id = $1', [SUPPLIER_ID]);
        console.log('=== FORNECEDOR ===');
        console.log(sup.rows[0] || 'NAO ENCONTRADO');

        // 2. All tables
        const tables = await client.query(`
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name
        `);
        console.log('\n=== TODAS AS TABELAS ===');
        const allTables = tables.rows.map(r => r.table_name);
        allTables.forEach(t => console.log(' -', t));

        // 3. All columns with 'fornecedor' reference
        const fornCols = await client.query(`
            SELECT table_name, column_name
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND (column_name ILIKE '%fornecedor%')
            ORDER BY table_name, column_name
        `);
        console.log('\n=== COLUNAS COM "fornecedor" ===');
        fornCols.rows.forEach(r => console.log(` - ${r.table_name}.${r.column_name}`));

        // 4. Count records per table that reference supplier 92
        console.log('\n=== CONTAGEM POR TABELA (fornecedor_id=92) ===');
        for (const row of fornCols.rows) {
            try {
                const cnt = await client.query(
                    `SELECT COUNT(*) FROM "${row.table_name}" WHERE "${row.column_name}" = $1`,
                    [SUPPLIER_ID]
                );
                if (parseInt(cnt.rows[0].count) > 0) {
                    console.log(` *** ${row.table_name}.${row.column_name}: ${cnt.rows[0].count} registros`);
                } else {
                    console.log(` - ${row.table_name}.${row.column_name}: 0 registros`);
                }
            } catch(e) {
                console.log(` ! ${row.table_name}.${row.column_name}: ERRO - ${e.message}`);
            }
        }

        // 5. Foreign keys (to check cascade deletions possible)
        const fks = await client.query(`
            SELECT 
                tc.table_name as child_table,
                kcu.column_name as child_col,
                ccu.table_name as parent_table,
                ccu.column_name as parent_col,
                rc.delete_rule
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu 
                ON tc.constraint_name = kcu.constraint_name AND tc.table_schema = kcu.table_schema
            JOIN information_schema.constraint_column_usage ccu 
                ON ccu.constraint_name = tc.constraint_name AND ccu.table_schema = tc.table_schema
            JOIN information_schema.referential_constraints rc
                ON rc.constraint_name = tc.constraint_name
            WHERE tc.constraint_type = 'FOREIGN KEY'
              AND tc.table_schema = 'public'
            ORDER BY parent_table, child_table
        `);
        console.log('\n=== FOREIGN KEYS (regras de cascade) ===');
        fks.rows.forEach(r => 
            console.log(` - ${r.child_table}.${r.child_col} -> ${r.parent_table}.${r.parent_col} [DELETE: ${r.delete_rule}]`)
        );

    } catch(e) {
        console.error('Erro:', e.message);
    } finally {
        await client.end();
    }
}

main();
