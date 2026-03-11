
const { Client } = require('pg');

const connectionString = "postgresql://postgres:dWldGAyqtVAsQvMYvTIqBKXTkHedCLAS@shortline.proxy.rlwy.net:26559/railway";
const SUPPLIER_ID = 92;

async function testConn() {
    console.log("Teste sem SSL...");
    const client = new Client({ 
        connectionString,
        ssl: false,
        connectionTimeoutMillis: 20000,
    });
    try {
        await client.connect();
        console.log("Conectado sem SSL!");
        const res = await client.query("SELECT 1 as test");
        console.log("Query OK:", res.rows[0]);
    } catch (err) {
        console.error("Erro sem SSL:", err.message);
    } finally {
        await client.end();
    }
}

testConn();
