const Database = require('better-sqlite3');
const path = require('path');

const DB_PATH = process.env.DB_PATH || path.join(__dirname, '..', 'data.sqlite');

// ---------------------------------------------------------------------------
// Reference data — the coach's real commission plan.
// All of this is seeded into tables so every number is editable at runtime
// without touching code.
// ---------------------------------------------------------------------------

// Products: [code, name, price, tier_rank, grants_territory]
// tier_rank orders packages for the qualification gate (higher = bigger).
// grants_territory: buying this package makes the buyer the protected holder
// of that geographic level for their own pincode/taluk.
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

// Fixed payout at each of the 12 upline levels, per product (L-1 .. L-12).
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

// Geographic override per product: [area, taluk, district].
// Only Registration is quantified by the coach so far (₹100 each). Packages
// default to 0 — set them here (or via the API) when the coach provides them.
const GEO_PAYOUTS = {
  REG: [100, 100, 100],
  P1: [0, 0, 0],
  P2: [0, 0, 0],
  P3: [0, 0, 0],
  P4: [0, 0, 0],
  P5: [0, 0, 0],
  P6: [0, 0, 0],
  P7: [0, 0, 0],
};

// Cosmetic advocate rank shown on the home screen. Earned by conversions
// (downline purchases the advocate directly drove). Does NOT affect payouts —
// this plan pays fixed amounts by level, independent of rank.
const RANKS = [
  ['Bronze', 0, 1],
  ['Silver', 5, 2],
  ['Gold', 10, 3],
  ['Platinum', 17, 4],
  ['Diamond', 30, 5],
];

const SETTINGS = [
  ['qualification_gate', 1, 'When 1, an upline earns a level payout only if they own a package of equal-or-higher tier than the purchased product.'],
  ['payout_day', 15, 'Day of the month locked commissions are released.'],
];

function createDb(dbPath = DB_PATH) {
  const db = new Database(dbPath);
  db.pragma('journal_mode = WAL');
  db.pragma('foreign_keys = ON');
  migrate(db);
  seedReferenceData(db);
  return db;
}

function migrate(db) {
  db.exec(`
    CREATE TABLE IF NOT EXISTS users (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL,
      email TEXT UNIQUE,
      phone TEXT,
      pincode TEXT NOT NULL,
      sponsor_id INTEGER REFERENCES users(id),
      highest_tier_rank INTEGER NOT NULL DEFAULT 0,
      rank TEXT NOT NULL DEFAULT 'Bronze',
      joined_at TEXT NOT NULL DEFAULT (datetime('now'))
    );

    -- Every pincode maps to an area (locality), a taluk and a district.
    CREATE TABLE IF NOT EXISTS pincodes (
      pincode TEXT PRIMARY KEY,
      area_name TEXT NOT NULL,
      taluk TEXT NOT NULL,
      district TEXT NOT NULL
    );

    -- One protected holder per territory per level.
    -- territory = pincode (area) | taluk name | district name.
    CREATE TABLE IF NOT EXISTS territory_holders (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      level TEXT NOT NULL CHECK (level IN ('area','taluk','district')),
      territory TEXT NOT NULL,
      user_id INTEGER NOT NULL REFERENCES users(id),
      granted_by_purchase_id INTEGER,
      UNIQUE (level, territory)
    );

    CREATE TABLE IF NOT EXISTS products (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      code TEXT UNIQUE NOT NULL,
      name TEXT NOT NULL,
      price REAL NOT NULL,
      tier_rank INTEGER NOT NULL,
      grants_territory TEXT
    );

    -- Fixed payout for each upline level, per product.
    CREATE TABLE IF NOT EXISTS commission_levels (
      product_id INTEGER NOT NULL REFERENCES products(id),
      level INTEGER NOT NULL CHECK (level BETWEEN 1 AND 12),
      amount REAL NOT NULL,
      PRIMARY KEY (product_id, level)
    );

    -- Geographic override per product, per territory level.
    CREATE TABLE IF NOT EXISTS geo_levels (
      product_id INTEGER NOT NULL REFERENCES products(id),
      level TEXT NOT NULL CHECK (level IN ('area','taluk','district')),
      amount REAL NOT NULL,
      PRIMARY KEY (product_id, level)
    );

    -- A shareable referral campaign link owned by an affiliate.
    CREATE TABLE IF NOT EXISTS campaign_links (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      user_id INTEGER NOT NULL REFERENCES users(id),
      slug TEXT UNIQUE NOT NULL,
      title TEXT NOT NULL,
      tag TEXT,
      product_id INTEGER REFERENCES products(id),
      created_at TEXT NOT NULL DEFAULT (datetime('now'))
    );

    -- A purchase is any product bought by a user (registration is a purchase
    -- of the REG product). It is the event that generates commissions.
    -- campaign_link_id attributes the purchase to the link that drove it.
    CREATE TABLE IF NOT EXISTS purchases (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      buyer_id INTEGER NOT NULL REFERENCES users(id),
      product_id INTEGER NOT NULL REFERENCES products(id),
      amount REAL NOT NULL,
      campaign_link_id INTEGER REFERENCES campaign_links(id),
      created_at TEXT NOT NULL DEFAULT (datetime('now'))
    );

    -- Every rupee of commission is one ledger row. Never recomputed.
    CREATE TABLE IF NOT EXISTS commissions (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      user_id INTEGER NOT NULL REFERENCES users(id),
      kind TEXT NOT NULL CHECK (kind IN ('level','geo_area','geo_taluk','geo_district')),
      level INTEGER,
      source_purchase_id INTEGER REFERENCES purchases(id),
      source_user_id INTEGER REFERENCES users(id),
      product_id INTEGER REFERENCES products(id),
      amount REAL NOT NULL,
      status TEXT NOT NULL DEFAULT 'locked' CHECK (status IN ('locked','paid')),
      created_at TEXT NOT NULL DEFAULT (datetime('now'))
    );
    CREATE INDEX IF NOT EXISTS idx_commissions_user ON commissions(user_id, created_at);

    CREATE TABLE IF NOT EXISTS settings (
      key TEXT PRIMARY KEY,
      value REAL NOT NULL,
      description TEXT
    );

    CREATE TABLE IF NOT EXISTS ranks (
      name TEXT PRIMARY KEY,
      min_conversions INTEGER NOT NULL,
      sort_order INTEGER NOT NULL
    );

    CREATE TABLE IF NOT EXISTS link_clicks (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      user_id INTEGER NOT NULL REFERENCES users(id),
      campaign_link_id INTEGER REFERENCES campaign_links(id),
      clicked_at TEXT NOT NULL DEFAULT (datetime('now'))
    );

    -- Payout requests / settlements. status: requested -> processing -> paid.
    CREATE TABLE IF NOT EXISTS payouts (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      user_id INTEGER NOT NULL REFERENCES users(id),
      reference_no TEXT NOT NULL,
      amount REAL NOT NULL,
      method TEXT NOT NULL DEFAULT 'Bank Transfer',
      status TEXT NOT NULL DEFAULT 'processing' CHECK (status IN ('requested','processing','paid','failed')),
      created_at TEXT NOT NULL DEFAULT (datetime('now'))
    );
    CREATE INDEX IF NOT EXISTS idx_payouts_user ON payouts(user_id, created_at);
  `);
}

function seedReferenceData(db) {
  const insProduct = db.prepare(
    'INSERT OR IGNORE INTO products (code, name, price, tier_rank, grants_territory) VALUES (?, ?, ?, ?, ?)'
  );
  const insLevel = db.prepare(
    'INSERT OR IGNORE INTO commission_levels (product_id, level, amount) VALUES (?, ?, ?)'
  );
  const insGeo = db.prepare(
    'INSERT OR IGNORE INTO geo_levels (product_id, level, amount) VALUES (?, ?, ?)'
  );
  const geoLevelNames = ['area', 'taluk', 'district'];

  const seed = db.transaction(() => {
    for (const [code, name, price, tier, territory] of PRODUCTS) {
      insProduct.run(code, name, price, tier, territory);
      const productId = db.prepare('SELECT id FROM products WHERE code = ?').get(code).id;

      const payouts = LEVEL_PAYOUTS[code];
      for (let i = 0; i < payouts.length; i++) insLevel.run(productId, i + 1, payouts[i]);

      const geo = GEO_PAYOUTS[code];
      for (let i = 0; i < geo.length; i++) insGeo.run(productId, geoLevelNames[i], geo[i]);
    }

    const insSetting = db.prepare(
      'INSERT OR IGNORE INTO settings (key, value, description) VALUES (?, ?, ?)'
    );
    for (const [key, value, description] of SETTINGS) insSetting.run(key, value, description);

    const insRank = db.prepare(
      'INSERT OR IGNORE INTO ranks (name, min_conversions, sort_order) VALUES (?, ?, ?)'
    );
    for (const [name, min, order] of RANKS) insRank.run(name, min, order);
  });
  seed();
}

module.exports = { createDb, DB_PATH, PRODUCTS, LEVEL_PAYOUTS, GEO_PAYOUTS };
