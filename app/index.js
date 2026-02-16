/**
 * Kubernetes Sharding Demo - Node.js API
 *
 * This app demonstrates database sharding:
 *   - 2 PostgreSQL instances (shard-0, shard-1) run as separate Kubernetes pods
 *   - Users are routed to a shard based on: shard = user_id % num_shards
 *   - Even IDs  → shard-0 (id=0, 2, 4, 6 ...)
 *   - Odd  IDs  → shard-1 (id=1, 3, 5, 7 ...)
 */

const express = require('express');
const { Pool } = require('pg');

const app = express();
app.use(express.json());

// ── Configuration ────────────────────────────────────────────────────────────

const NUM_SHARDS = 2;
const PORT = parseInt(process.env.PORT || '3000');

// Each shard is a separate PostgreSQL pod, reachable via its Kubernetes Service name
const shardConfigs = [
  {
    host: process.env.SHARD_0_HOST || 'postgres-shard-0',  // K8s Service name
    port: 5432,
    database: process.env.DB_NAME     || 'sharddb',
    user:     process.env.DB_USER     || 'postgres',
    password: process.env.DB_PASSWORD || 'postgres',
    connectionTimeoutMillis: 5000,
  },
  {
    host: process.env.SHARD_1_HOST || 'postgres-shard-1',  // K8s Service name
    port: 5432,
    database: process.env.DB_NAME     || 'sharddb',
    user:     process.env.DB_USER     || 'postgres',
    password: process.env.DB_PASSWORD || 'postgres',
    connectionTimeoutMillis: 5000,
  },
];

// Create a connection pool per shard
const shards = shardConfigs.map(cfg => new Pool(cfg));

// ── Helpers ──────────────────────────────────────────────────────────────────

/** Retry an async operation with exponential back-off */
async function withRetry(label, fn, maxRetries = 8, baseDelayMs = 3000) {
  let lastErr;
  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      return await fn();
    } catch (err) {
      lastErr = err;
      const delay = baseDelayMs * Math.pow(1.5, attempt - 1);
      console.log(`[retry] ${label} – attempt ${attempt}/${maxRetries} failed: ${err.message}. Waiting ${Math.round(delay)}ms…`);
      await new Promise(r => setTimeout(r, delay));
    }
  }
  throw lastErr;
}

/** Determine which shard stores a given userId */
function shardIndex(userId) {
  return userId % NUM_SHARDS;
}

// ── Schema initialisation ─────────────────────────────────────────────────────

async function initShards() {
  for (let i = 0; i < shards.length; i++) {
    await withRetry(`init shard-${i}`, async () => {
      await shards[i].query(`
        CREATE TABLE IF NOT EXISTS users (
          id         INTEGER PRIMARY KEY,
          name       VARCHAR(100) NOT NULL,
          email      VARCHAR(100) NOT NULL,
          shard_id   INTEGER      NOT NULL,
          created_at TIMESTAMP    DEFAULT NOW()
        )
      `);
      console.log(`[init] shard-${i} (${shardConfigs[i].host}) ✓`);
    });
  }
}

// ── Routes ────────────────────────────────────────────────────────────────────

// GET /health  – liveness / readiness probe target
app.get('/health', (_req, res) => {
  res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

// GET /shards  – explain the sharding topology
app.get('/shards', (_req, res) => {
  res.json({
    numShards: NUM_SHARDS,
    shardingKey: 'user_id',
    shardingFormula: 'shard = user_id % numShards',
    shards: shardConfigs.map((cfg, i) => ({
      shardId:     i,
      host:        cfg.host,
      storesUsers: i === 0
        ? 'Even IDs  (0, 2, 4 …)'
        : 'Odd  IDs  (1, 3, 5 …)',
    })),
  });
});

// POST /users  – create a user, routed to the correct shard
app.post('/users', async (req, res) => {
  const { id, name, email } = req.body;

  if (!id || !name || !email) {
    return res.status(400).json({ error: 'id, name, and email are required' });
  }

  const userId  = parseInt(id);
  const idx     = shardIndex(userId);
  const shard   = shards[idx];

  try {
    const result = await shard.query(
      'INSERT INTO users (id, name, email, shard_id) VALUES ($1, $2, $3, $4) RETURNING *',
      [userId, name, email, idx],
    );
    res.status(201).json({
      user: result.rows[0],
      routing: {
        shardId:   idx,
        shardHost: shardConfigs[idx].host,
        why:       `${userId} % ${NUM_SHARDS} = ${idx}`,
      },
    });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// GET /users/:id  – fetch a single user from the correct shard
app.get('/users/:id', async (req, res) => {
  const userId = parseInt(req.params.id);
  if (isNaN(userId)) return res.status(400).json({ error: 'id must be a number' });

  const idx   = shardIndex(userId);
  const shard = shards[idx];

  try {
    const result = await shard.query('SELECT * FROM users WHERE id = $1', [userId]);
    if (result.rows.length === 0) {
      return res.status(404).json({
        error:         'User not found',
        searchedShard: idx,
        searchedHost:  shardConfigs[idx].host,
      });
    }
    res.json({
      user: result.rows[0],
      routing: {
        shardId:   idx,
        shardHost: shardConfigs[idx].host,
        why:       `${userId} % ${NUM_SHARDS} = ${idx}`,
      },
    });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// GET /users  – fan-out: query ALL shards and merge results
app.get('/users', async (_req, res) => {
  try {
    const perShard = await Promise.all(
      shards.map((shard, i) =>
        shard.query('SELECT * FROM users ORDER BY id')
             .then(r => r.rows.map(u => ({ ...u, _shard: i }))),
      ),
    );
    const all = perShard.flat().sort((a, b) => a.id - b.id);
    res.json({
      users:      all,
      totalUsers: all.length,
      perShard:   perShard.map((rows, i) => ({ shardId: i, count: rows.length })),
    });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// DELETE /users/:id  – delete from the correct shard
app.delete('/users/:id', async (req, res) => {
  const userId = parseInt(req.params.id);
  if (isNaN(userId)) return res.status(400).json({ error: 'id must be a number' });

  const idx   = shardIndex(userId);
  const shard = shards[idx];

  try {
    const result = await shard.query(
      'DELETE FROM users WHERE id = $1 RETURNING *', [userId],
    );
    if (result.rows.length === 0) {
      return res.status(404).json({ error: 'User not found', shard: idx });
    }
    res.json({ deleted: result.rows[0], fromShard: idx });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// ── Start ─────────────────────────────────────────────────────────────────────

app.listen(PORT, async () => {
  console.log('');
  console.log('╔══════════════════════════════════════════╗');
  console.log('║   Kubernetes Sharding Demo – Node.js     ║');
  console.log('╚══════════════════════════════════════════╝');
  console.log(`Listening on port ${PORT}`);
  console.log(`Shards: ${NUM_SHARDS}  |  Formula: user_id % ${NUM_SHARDS}`);
  console.log('');
  console.log('Initialising shards (waiting for Postgres pods to be ready)…');

  try {
    await initShards();
    console.log('All shards ready!');
  } catch (err) {
    console.error('Could not initialise shards:', err.message);
    process.exit(1);
  }
});
