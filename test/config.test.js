import test from 'node:test';
import assert from 'node:assert/strict';
import { getConfig } from '../src/config.js';

test('getConfig returns defaults', () => {
  const previousEnv = { ...process.env };
  delete process.env.PRIMARY_HOST;
  delete process.env.PRIMARY_PORT;
  delete process.env.REPLICA_HOST;
  delete process.env.REPLICA_PORT;
  delete process.env.POSTGRES_USER;
  delete process.env.POSTGRES_PASSWORD;
  delete process.env.POSTGRES_DB;

  const config = getConfig();

  assert.equal(config.primary.host, 'localhost');
  assert.equal(config.primary.port, 5432);
  assert.equal(config.replica.port, 5433);
  assert.equal(config.primary.user, 'app');

  process.env = previousEnv;
});
