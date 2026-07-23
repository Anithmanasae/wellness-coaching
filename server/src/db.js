const path = require('path');
const { createAdapter } = require('./adapter');

const DB_PATH = process.env.DB_PATH || path.join(__dirname, '..', 'data.sqlite');

// ---------------------------------------------------------------------------
// Reference data — the coach's real commission plan. Seeded into tables so
// every number is editable at runtime without code changes.
// ---------------------------------------------------------------------------

// [code, name, price, tier_rank, grants_territory]
const PRODUCTS = [
  ['REG', 'Registration – Life & Career Building Program', 250, 0, null],
  ['P7', 'Water Awareness + Potability Test + AMC + Career Intro', 4990, 1, null],
  ['P1', 'Mind Mastery – Basic Course', 5000, 2, null],
  ['P2', 'Mind Mastery – Advanced Course', 10000, 3, null],
  ['P6', 'Water & Physical Health Awareness + Career Intro', 11000, 4, null],
  ['P3', 'Advanced Course + Territory Protection (PIN Code)', 25000, 5, 'area'],
  ['P4', 'Advanced Course + Personal Counselling', 100000, 6, null],
  ['P5', 'Advanced Course + Territory Protection (Taluk)', 150000, 7, 'taluk'],
];

const LEVEL_PAYOUTS = {
  REG: [100, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5],
  P1: [2000, 350, 150, 50, 50, 30, 30, 30, 30, 30, 25, 25],
  P2: [3000, 1000, 500, 300, 300, 100, 100, 100, 100, 100, 100, 100],
  P3: [10000, 1000, 800, 500, 200, 100, 100, 100, 100, 100, 100, 100],
  P4: [35000, 4000, 2000, 1000, 500, 500, 200, 200, 150, 150, 150, 150],
  P5: [51000, 8000, 3500, 2000, 1000, 600, 300, 200, 200, 100, 100, 100],
  P6: [1500, 300, 100, 100, 100, 50, 50, 50, 50, 50, 50, 50],
  P7: [1010, 300, 100, 100, 100, 50, 50, 20, 20, 20, 20, 20],
};

// [area, taluk, district] override per product. Only Registration is quantified
// by the coach so far (₹100 each); packages default to 0.
const GEO_PAYOUTS = {
  REG: [100, 100, 100],
  P1: [0, 0, 0], P2: [0, 0, 0], P3: [0, 0, 0], P4: [0, 0, 0],
  P5: [0, 0, 0], P6: [0, 0, 0], P7: [0, 0, 0],
};

// Cosmetic advocate rank by conversions. Does not affect payouts.
const RANKS = [
  ['Bronze', 0, 1], ['Silver', 5, 2], ['Gold', 10, 3], ['Platinum', 17, 4], ['Diamond', 30, 5],
];

const SETTINGS = [
  ['qualification_gate', 1, 'When 1, an upline earns a level payout only if they own a package of equal-or-higher tier than the purchased product.'],
  ['payout_day', 15, 'Day of the month locked commissions are released.'],
];

// Dialect-specific column fragments.
function tokens(dialect) {
  const pg = dialect === 'pg';
  return {
    PK: pg ? 'INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY' : 'INTEGER PRIMARY KEY AUTOINCREMENT',
    REAL: pg ? 'DOUBLE PRECISION' : 'REAL',
    TS: pg ? 'TIMESTAMPTZ NOT NULL DEFAULT now()' : 'TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP',
  };
}

function schema(dialect) {
  const { PK, REAL, TS } = tokens(dialect);
  // Tables are ordered so every foreign-key target exists first (Postgres
  // resolves references eagerly, unlike SQLite).
  return `
    CREATE TABLE IF NOT EXISTS users (
      id ${PK},
      name TEXT NOT NULL,
      email TEXT UNIQUE,
      phone TEXT,
      pincode TEXT,
      sponsor_id INTEGER REFERENCES users(id),
      referral_code TEXT UNIQUE,
      highest_tier_rank INTEGER NOT NULL DEFAULT 0,
      rank TEXT NOT NULL DEFAULT 'Bronze',
      joined_at ${TS}
    );

    CREATE TABLE IF NOT EXISTS pincodes (
      pincode TEXT PRIMARY KEY,
      area_name TEXT NOT NULL,
      taluk TEXT NOT NULL,
      district TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS products (
      id ${PK},
      code TEXT UNIQUE NOT NULL,
      name TEXT NOT NULL,
      price ${REAL} NOT NULL,
      tier_rank INTEGER NOT NULL,
      grants_territory TEXT
    );

    CREATE TABLE IF NOT EXISTS commission_levels (
      product_id INTEGER NOT NULL REFERENCES products(id),
      level INTEGER NOT NULL CHECK (level BETWEEN 1 AND 12),
      amount ${REAL} NOT NULL,
      PRIMARY KEY (product_id, level)
    );

    CREATE TABLE IF NOT EXISTS geo_levels (
      product_id INTEGER NOT NULL REFERENCES products(id),
      level TEXT NOT NULL CHECK (level IN ('area','taluk','district')),
      amount ${REAL} NOT NULL,
      PRIMARY KEY (product_id, level)
    );

    CREATE TABLE IF NOT EXISTS territory_holders (
      id ${PK},
      level TEXT NOT NULL CHECK (level IN ('area','taluk','district')),
      territory TEXT NOT NULL,
      user_id INTEGER NOT NULL REFERENCES users(id),
      granted_by_purchase_id INTEGER,
      UNIQUE (level, territory)
    );

    CREATE TABLE IF NOT EXISTS campaign_links (
      id ${PK},
      user_id INTEGER NOT NULL REFERENCES users(id),
      slug TEXT UNIQUE NOT NULL,
      title TEXT NOT NULL,
      tag TEXT,
      product_id INTEGER REFERENCES products(id),
      created_at ${TS}
    );

    CREATE TABLE IF NOT EXISTS purchases (
      id ${PK},
      buyer_id INTEGER NOT NULL REFERENCES users(id),
      product_id INTEGER NOT NULL REFERENCES products(id),
      amount ${REAL} NOT NULL,
      campaign_link_id INTEGER REFERENCES campaign_links(id),
      external_order_id TEXT UNIQUE,
      created_at ${TS}
    );

    CREATE TABLE IF NOT EXISTS payouts (
      id ${PK},
      user_id INTEGER NOT NULL REFERENCES users(id),
      reference_no TEXT NOT NULL,
      amount ${REAL} NOT NULL,
      method TEXT NOT NULL DEFAULT 'Bank Transfer',
      status TEXT NOT NULL DEFAULT 'processing' CHECK (status IN ('requested','processing','paid','rejected')),
      created_at ${TS}
    );

    CREATE TABLE IF NOT EXISTS commissions (
      id ${PK},
      user_id INTEGER NOT NULL REFERENCES users(id),
      kind TEXT NOT NULL CHECK (kind IN ('level','geo_area','geo_taluk','geo_district')),
      level INTEGER,
      source_purchase_id INTEGER REFERENCES purchases(id),
      source_user_id INTEGER REFERENCES users(id),
      product_id INTEGER REFERENCES products(id),
      amount ${REAL} NOT NULL,
      status TEXT NOT NULL DEFAULT 'locked' CHECK (status IN ('locked','requested','paid')),
      payout_id INTEGER REFERENCES payouts(id),
      created_at ${TS}
    );

    CREATE TABLE IF NOT EXISTS settings (
      key TEXT PRIMARY KEY,
      value ${REAL} NOT NULL,
      description TEXT
    );

    CREATE TABLE IF NOT EXISTS ranks (
      name TEXT PRIMARY KEY,
      min_conversions INTEGER NOT NULL,
      sort_order INTEGER NOT NULL
    );

    CREATE TABLE IF NOT EXISTS link_clicks (
      id ${PK},
      user_id INTEGER NOT NULL REFERENCES users(id),
      campaign_link_id INTEGER REFERENCES campaign_links(id),
      clicked_at ${TS}
    );

    CREATE INDEX IF NOT EXISTS idx_commissions_user ON commissions(user_id, created_at);
    CREATE INDEX IF NOT EXISTS idx_payouts_user ON payouts(user_id, created_at);
  `;
}

async function seedReferenceData(db) {
  await db.tx(async (t) => {
    const geoNames = ['area', 'taluk', 'district'];
    for (const [code, name, price, tier, territory] of PRODUCTS) {
      await t.run('INSERT INTO products (code, name, price, tier_rank, grants_territory) VALUES (?, ?, ?, ?, ?) ON CONFLICT DO NOTHING', [code, name, price, tier, territory]);
      const product = await t.get('SELECT id FROM products WHERE code = ?', [code]);
      const payouts = LEVEL_PAYOUTS[code];
      for (let i = 0; i < payouts.length; i++) {
        await t.run('INSERT INTO commission_levels (product_id, level, amount) VALUES (?, ?, ?) ON CONFLICT DO NOTHING', [product.id, i + 1, payouts[i]]);
      }
      const geo = GEO_PAYOUTS[code];
      for (let i = 0; i < geo.length; i++) {
        await t.run('INSERT INTO geo_levels (product_id, level, amount) VALUES (?, ?, ?) ON CONFLICT DO NOTHING', [product.id, geoNames[i], geo[i]]);
      }
    }
    for (const [key, value, description] of SETTINGS) {
      await t.run('INSERT INTO settings (key, value, description) VALUES (?, ?, ?) ON CONFLICT DO NOTHING', [key, value, description]);
    }
    for (const [name, min, order] of RANKS) {
      await t.run('INSERT INTO ranks (name, min_conversions, sort_order) VALUES (?, ?, ?) ON CONFLICT DO NOTHING', [name, min, order]);
    }
  });
}

// Open (and migrate + seed) a database. Driver from opts.driver or DB_DRIVER
// ('sqlite' default). For sqlite, opts.file (default DB_PATH, or ':memory:').
async function openDb(opts = {}) {
  const driver = opts.driver || process.env.DB_DRIVER || 'sqlite';
  const db = createAdapter(driver === 'sqlite' ? { driver, file: opts.file || DB_PATH } : { driver, connectionString: opts.connectionString });
  await db.exec(schema(db.dialect));
  // Postgres shares one database across callers; opts.reset (or DB_RESET) wipes
  // everything for a clean slate — used by the test suite for per-test isolation.
  if ((opts.reset || process.env.DB_RESET) && db.dialect === 'pg') {
    await db.exec('TRUNCATE users, pincodes, products, commission_levels, geo_levels, territory_holders, campaign_links, purchases, payouts, commissions, settings, ranks, link_clicks RESTART IDENTITY CASCADE');
  }
  await seedReferenceData(db);
  return db;
}

module.exports = { openDb, DB_PATH, PRODUCTS, LEVEL_PAYOUTS, GEO_PAYOUTS };
