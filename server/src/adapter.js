// Dual-driver async database adapter.
//
// The whole app talks to this uniform async interface, so the same code runs
// on SQLite (zero-setup dev/test) or PostgreSQL (production). Queries use `?`
// placeholders everywhere; the Postgres side rewrites them to $1,$2,….
//
//   db.get(sql, params)  -> first row | undefined
//   db.all(sql, params)  -> row[]
//   db.run(sql, params)  -> { changes }
//   db.exec(sql)         -> run raw DDL/script
//   db.tx(async t => …)  -> transaction; nests via SAVEPOINTs
//
// For inserts that need the new id, write `INSERT … RETURNING id` and use
// db.get(...).id — both drivers support RETURNING.

// Rewrite `?` placeholders to Postgres `$n`. Our SQL never contains a literal
// `?`, so a positional replace is safe.
function toPg(sql) {
  let i = 0;
  return sql.replace(/\?/g, () => `$${++i}`);
}

// A Handle wraps one connection and a transaction depth. tx() opens BEGIN at
// the top level and a SAVEPOINT when already inside a transaction.
class Handle {
  constructor(conn, depth = 0) {
    this.conn = conn;
    this.depth = depth;
    this.dialect = conn.dialect;
  }
  get(sql, params = []) { return this.conn.get(sql, params); }
  all(sql, params = []) { return this.conn.all(sql, params); }
  run(sql, params = []) { return this.conn.run(sql, params); }
  exec(sql) { return this.conn.exec(sql); }

  async tx(fn) {
    const nested = this.depth > 0;
    const name = `sp_${this.depth}`;
    await this.conn.exec(nested ? `SAVEPOINT ${name}` : 'BEGIN');
    const child = new Handle(this.conn, this.depth + 1);
    try {
      const result = await fn(child);
      await this.conn.exec(nested ? `RELEASE SAVEPOINT ${name}` : 'COMMIT');
      return result;
    } catch (err) {
      await this.conn.exec(nested ? `ROLLBACK TO SAVEPOINT ${name}` : 'ROLLBACK');
      throw err;
    }
  }
}

// ---- SQLite (better-sqlite3) -------------------------------------------------

function sqliteConn(raw) {
  return {
    dialect: 'sqlite',
    async get(sql, p) { return raw.prepare(sql).get(...p); },
    async all(sql, p) { return raw.prepare(sql).all(...p); },
    async run(sql, p) { const r = raw.prepare(sql).run(...p); return { changes: r.changes }; },
    async exec(sql) { raw.exec(sql); },
  };
}

function createSqlite({ file = ':memory:' } = {}) {
  const Database = require('better-sqlite3');
  const raw = new Database(file);
  raw.pragma('journal_mode = WAL');
  raw.pragma('foreign_keys = ON');
  const conn = sqliteConn(raw);
  const handle = new Handle(conn, 0);
  handle.dialect = 'sqlite';
  handle.close = async () => raw.close();
  return handle;
}

// ---- PostgreSQL (pg) ---------------------------------------------------------

function pgConn(client) {
  return {
    dialect: 'pg',
    async get(sql, p) { return (await client.query(toPg(sql), p)).rows[0]; },
    async all(sql, p) { return (await client.query(toPg(sql), p)).rows; },
    async run(sql, p) { const r = await client.query(toPg(sql), p); return { changes: r.rowCount }; },
    async exec(sql) { await client.query(sql); },
  };
}

function createPg({ connectionString } = {}) {
  const pg = require('pg');
  // Return timestamps as raw strings (like SQLite) so downstream string ops
  // (slice, comparisons) behave identically across drivers.
  pg.types.setTypeParser(1114, (v) => v); // timestamp
  pg.types.setTypeParser(1184, (v) => v); // timestamptz
  // allowExitOnIdle lets one-shot processes (tests, seed) exit once idle,
  // instead of hanging on open pool connections. The server stays alive via
  // its listening socket regardless.
  const pool = new pg.Pool({ connectionString: connectionString || process.env.DATABASE_URL, allowExitOnIdle: true });

  const poolConn = {
    dialect: 'pg',
    async get(sql, p) { return (await pool.query(toPg(sql), p)).rows[0]; },
    async all(sql, p) { return (await pool.query(toPg(sql), p)).rows; },
    async run(sql, p) { const r = await pool.query(toPg(sql), p); return { changes: r.rowCount }; },
    async exec(sql) { await pool.query(sql); },
  };

  const handle = new Handle(poolConn, 0);
  handle.dialect = 'pg';
  // A transaction needs a dedicated client so BEGIN/COMMIT are isolated.
  handle.tx = async (fn) => {
    const client = await pool.connect();
    try {
      const bound = new Handle(pgConn(client), 0);
      return await bound.tx(fn);
    } finally {
      client.release();
    }
  };
  handle.close = async () => pool.end();
  return handle;
}

// driver: 'sqlite' | 'pg' (defaults from DB_DRIVER, else sqlite).
function createAdapter(opts = {}) {
  const driver = opts.driver || process.env.DB_DRIVER || 'sqlite';
  return driver === 'pg' ? createPg(opts) : createSqlite(opts);
}

module.exports = { createAdapter, toPg };
