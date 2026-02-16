import pg from 'pg';
import { getConfig } from './config.js';

const { Client } = pg;

async function runDemo() {
  const { primary } = getConfig();
  const client = new Client(primary);
  await client.connect();

  try {
    // Clean up from previous runs
    await client.query('DROP TABLE IF EXISTS logs CASCADE');

    // 1. Create a range-partitioned table (partitioned by month via created_at date)
    await client.query(`
      CREATE TABLE logs (
        id        BIGSERIAL,
        message   TEXT NOT NULL,
        created_at DATE NOT NULL
      ) PARTITION BY RANGE (created_at)
    `);

    // 2. Create one partition per month for Q1 2024
    await client.query(`CREATE TABLE logs_jan PARTITION OF logs FOR VALUES FROM ('2024-01-01') TO ('2024-02-01')`);
    await client.query(`CREATE TABLE logs_feb PARTITION OF logs FOR VALUES FROM ('2024-02-01') TO ('2024-03-01')`);
    await client.query(`CREATE TABLE logs_mar PARTITION OF logs FOR VALUES FROM ('2024-03-01') TO ('2024-04-01')`);

    console.log('SCHEMA: "logs" partitioned by RANGE(created_at) — partitions: logs_jan, logs_feb, logs_mar\n');

    // 3. Insert rows spanning all three months
    const rows = [
      ['Jan event A', '2024-01-10'],
      ['Jan event B', '2024-01-25'],
      ['Feb event',   '2024-02-14'],
      ['Mar event',   '2024-03-05'],
    ];
    for (const [msg, date] of rows) {
      await client.query('INSERT INTO logs(message, created_at) VALUES($1, $2)', [msg, date]);
    }
    console.log(`INSERTS: ${rows.length} rows written across Jan / Feb / Mar`);

    // 4. Show which physical partition each row lives in
    const placement = await client.query(`
      SELECT tableoid::regclass AS partition, id, created_at, message
      FROM   logs
      ORDER  BY created_at
    `);
    console.log('\nROW PLACEMENT (each row stored in its month partition):');
    for (const r of placement.rows) {
      console.log(`  ${String(r.partition).padEnd(10)} | ${r.created_at.toISOString().slice(0, 10)} | ${r.message}`);
    }

    // 5. Partition pruning — query is restricted to Jan, so only logs_jan is scanned
    const explain = await client.query(`
      EXPLAIN SELECT * FROM logs WHERE created_at < '2024-02-01'
    `);
    console.log('\nEXPLAIN for WHERE created_at < 2024-02-01 (only logs_jan should appear):');
    for (const r of explain.rows) {
      console.log('  ' + r['QUERY PLAN']);
    }

    // 6. Row count per partition
    const counts = await client.query(`
      SELECT tableoid::regclass AS partition, COUNT(*) AS rows
      FROM   logs
      GROUP  BY tableoid
      ORDER  BY partition
    `);
    console.log('\nROWS PER PARTITION:');
    for (const r of counts.rows) {
      console.log(`  ${r.partition}: ${r.rows} row(s)`);
    }

    console.log('\nSUCCESS: partitioning demo complete.');
  } finally {
    await client.end();
  }
}

runDemo().catch((err) => {
  console.error('DEMO_FAILED:', err.message);
  process.exitCode = 1;
});
