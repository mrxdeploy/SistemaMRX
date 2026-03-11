
const { Pool } = require('pg');

const pool = new Pool({
  connectionString: 'postgresql://postgres:dWldGAyqtVAsQvMYvTIqBKXTkHedCLAS@shortline.proxy.rlwy.net:26559/railway',
  ssl: { rejectUnauthorized: false }
});

async function analyze() {
  try {
    // 1. List all tables
    const tables = await pool.query(`
      SELECT table_name 
      FROM information_schema.tables 
      WHERE table_schema = 'public' 
      ORDER BY table_name
    `);
    console.log('=== TODAS AS TABELAS ===');
    tables.rows.forEach(r => console.log(' -', r.table_name));

    // 2. Check supplier id=92
    const supplier = await pool.query(`SELECT * FROM fornecedores WHERE id = 92`);
    console.log('\n=== FORNECEDOR ID=92 ===');
    console.log(supplier.rows[0]);

    // 3. Check all columns that reference fornecedor_id across tables
    const fkCols = await pool.query(`
      SELECT 
        tc.table_name, 
        kcu.column_name,
        ccu.table_name AS foreign_table_name,
        ccu.column_name AS foreign_column_name 
      FROM information_schema.table_constraints AS tc 
      JOIN information_schema.key_column_usage AS kcu
        ON tc.constraint_name = kcu.constraint_name
        AND tc.table_schema = kcu.table_schema
      JOIN information_schema.constraint_column_usage AS ccu
        ON ccu.constraint_name = tc.constraint_name
        AND ccu.table_schema = tc.table_schema
      WHERE tc.constraint_type = 'FOREIGN KEY' 
        AND (ccu.table_name = 'fornecedores' OR ccu.column_name LIKE '%fornecedor%')
      ORDER BY tc.table_name
    `);
    console.log('\n=== FOREIGN KEYS PARA FORNECEDORES ===');
    fkCols.rows.forEach(r => console.log(` - ${r.table_name}.${r.column_name} -> ${r.foreign_table_name}.${r.foreign_column_name}`));

    // 4. Check count in each relevant table
    const relevantTables = [
      { table: 'ordens_compra', col: 'fornecedor_id' },
      { table: 'ordens_servico', col: 'fornecedor_id' },
      { table: 'estoque', col: 'fornecedor_id' },
      { table: 'itens_estoque', col: 'fornecedor_id' },
      { table: 'fila_separacao', col: 'fornecedor_id' },
      { table: 'materiais', col: 'fornecedor_id' },
      { table: 'itens_ordens_compra', col: 'fornecedor_id' },
      { table: 'fornecedor_tabela', col: 'fornecedor_id' },
      { table: 'fornecedor_tabela_precos', col: 'fornecedor_id' },
      { table: 'tabela_precos', col: 'fornecedor_id' },
      { table: 'produtos', col: 'fornecedor_id' },
      { table: 'compras', col: 'fornecedor_id' },
      { table: 'pedidos', col: 'fornecedor_id' },
      { table: 'solicitacoes', col: 'fornecedor_id' },
    ];

    console.log('\n=== CONTAGEM POR TABELA (fornecedor_id=92) ===');
    for (const { table, col } of relevantTables) {
      try {
        const r = await pool.query(`SELECT COUNT(*) FROM ${table} WHERE ${col} = 92`);
        console.log(` - ${table}: ${r.rows[0].count} registros`);
      } catch (e) {
        // Table might not exist or column might be different
        try {
          // Check if table exists
          const exists = await pool.query(`SELECT COUNT(*) FROM information_schema.tables WHERE table_name = '${table}' AND table_schema='public'`);
          if (exists.rows[0].count === '0') {
            // Table doesn't exist
          } else {
            console.log(` - ${table}: coluna '${col}' não encontrada ou erro: ${e.message}`);
          }
        } catch(e2) {}
      }
    }

    // 5. Let's also search all tables for any column with 'fornecedor' in name
    const fornecedorCols = await pool.query(`
      SELECT table_name, column_name
      FROM information_schema.columns
      WHERE table_schema = 'public'
        AND (column_name LIKE '%fornecedor%' OR column_name = 'supplier_id')
      ORDER BY table_name, column_name
    `);
    console.log('\n=== COLUNAS COM "fornecedor" EM TODAS AS TABELAS ===');
    fornecedorCols.rows.forEach(r => console.log(` - ${r.table_name}.${r.column_name}`));

    // 6. Check OC (ordens_compra) structure
    const ocCols = await pool.query(`
      SELECT column_name, data_type 
      FROM information_schema.columns 
      WHERE table_name = 'ordens_compra' AND table_schema = 'public'
      ORDER BY ordinal_position
    `);
    if (ocCols.rows.length > 0) {
      console.log('\n=== ESTRUTURA ordens_compra ===');
      ocCols.rows.forEach(r => console.log(` - ${r.column_name} (${r.data_type})`));
    }

    // 7. Check OS (ordens_servico) structure  
    const osCols = await pool.query(`
      SELECT column_name, data_type 
      FROM information_schema.columns 
      WHERE table_name = 'ordens_servico' AND table_schema = 'public'
      ORDER BY ordinal_position
    `);
    if (osCols.rows.length > 0) {
      console.log('\n=== ESTRUTURA ordens_servico ===');
      osCols.rows.forEach(r => console.log(` - ${r.column_name} (${r.data_type})`));
    }

  } catch (e) {
    console.error('Erro:', e.message);
  } finally {
    await pool.end();
  }
}

analyze();
