import pg from 'pg';

const { Client } = pg;

// Two independent Postgres instances = two shards
const shardConfigs = [
  {
    host:     process.env.SHARD0_HOST || 'localhost',
    port:     process.env.SHARD0_PORT || 5434,
    user:     process.env.POSTGRES_USER     || 'app',
    password: process.env.POSTGRES_PASSWORD || 'app_password',
    database: process.env.POSTGRES_DB       || 'appdb',
  },
  {
    host:     process.env.SHARD1_HOST || 'localhost',
    port:     process.env.SHARD1_PORT || 5435,
    user:     process.env.POSTGRES_USER     || 'app',
    password: process.env.POSTGRES_PASSWORD || 'app_password',
    database: process.env.POSTGRES_DB       || 'appdb',
  },
];

// Hash-based routing: which shard owns this user?
function shardFor(userId) {
  return userId % shardConfigs.length;
}

async function setup(clients) {
  for (const c of clients) {
    await c.query('DROP TABLE IF EXISTS users');
    await c.query(`
      CREATE TABLE users (
        id    INT  PRIMARY KEY,
        name  TEXT NOT NULL,
        email TEXT NOT NULL
      )
    `);
  }
}

async function runDemo() {
  const clients = shardConfigs.map((cfg) => new Client(cfg));
  for (const c of clients) await c.connect();

  try {
    await setup(clients);

    console.log(`SHARDS: ${clients.length} independent Postgres instances`);
    console.log('ROUTING: shard_index = user_id % num_shards\n');

    // --- INSERT: each user routed by id % 2 ---
    const users = [
      { id: 1, name: 'Alice', email: 'alice@example.com' },
      { id: 2, name: 'Bob',   email: 'bob@example.com'   },
      { id: 3, name: 'Carol', email: 'carol@example.com' },
      { id: 4, name: 'Dave',  email: 'dave@example.com'  },
      { id: 5, name: 'Eve',   email: 'eve@example.com'   },
    ];

    console.log('INSERTS (routed to shard by user_id % 2):');
    for (const u of users) {
      const idx = shardFor(u.id);
      await clients[idx].query(
        'INSERT INTO users(id, name, email) VALUES($1, $2, $3)',
        [u.id, u.name, u.email]
      );
      console.log(`  user ${u.id} (${u.name.padEnd(5)}) → shard-${idx}`);
    }

    // --- POINT LOOKUP: route directly to one shard ---
    const lookupId = 3;
    const idx = shardFor(lookupId);
    const point = await clients[idx].query('SELECT * FROM users WHERE id = $1', [lookupId]);
    console.log(`\nPOINT LOOKUP (id=${lookupId}) → only shard-${idx} queried:`);
    console.log(' ', point.rows[0]);

    // --- SCATTER-GATHER: query all shards, merge in app ---
    console.log('\nSCATTER-GATHER (fan out to all shards, merge in app):');
    const allRows = [];
    for (let i = 0; i < clients.length; i++) {
      const res = await clients[i].query('SELECT * FROM users ORDER BY id');
      console.log(`  shard-${i} returned ${res.rowCount} row(s): ${res.rows.map((r) => r.name).join(', ')}`);
      allRows.push(...res.rows);
    }
    allRows.sort((a, b) => a.id - b.id);
    console.log(`  merged  → ${allRows.map((r) => r.name).join(', ')}`);

    console.log('\nSUCCESS: sharding demo complete.');
  } finally {
    for (const c of clients) await c.end();
  }
}

runDemo().catch((err) => {
  console.error('DEMO_FAILED:', err.message);
  process.exitCode = 1;
});
