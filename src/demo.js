import pg from 'pg';
import { getConfig } from './config.js';

const { Client } = pg;

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function ensureSchema(client) {
  await client.query(`
    CREATE TABLE IF NOT EXISTS events (
      id BIGSERIAL PRIMARY KEY,
      message TEXT NOT NULL,
      created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
  `);
}

async function runDemo() {
  const config = getConfig();
  const writer = new Client(config.primary);
  const reader = new Client(config.replica);

  await writer.connect();
  await reader.connect();

  try {
    await ensureSchema(writer);

    const message = `hello-replica-${Date.now()}`;
    const insertResult = await writer.query(
      'INSERT INTO events(message) VALUES($1) RETURNING id, message, created_at',
      [message]
    );

    const { id } = insertResult.rows[0];
    console.log('WROTE_ON_PRIMARY:', insertResult.rows[0]);

    let replicatedRow = null;
    for (let attempt = 1; attempt <= 20; attempt += 1) {
      const readResult = await reader.query(
        'SELECT id, message, created_at FROM events WHERE id = $1',
        [id]
      );
      if (readResult.rowCount > 0) {
        replicatedRow = readResult.rows[0];
        break;
      }
      await sleep(500);
    }

    if (!replicatedRow) {
      throw new Error('Row was not visible on replica within timeout.');
    }

    console.log('READ_ON_REPLICA:', replicatedRow);
    console.log('SUCCESS: write to primary + read from replica demonstrated.');
  } finally {
    await writer.end();
    await reader.end();
  }
}

runDemo().catch((error) => {
  console.error('DEMO_FAILED:', error.message);
  process.exitCode = 1;
});
