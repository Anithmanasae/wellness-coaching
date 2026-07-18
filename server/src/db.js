const Database = require('better-sqlite3');
const path = require('path');

const DB_PATH = process.env.DB_PATH || path.join(__dirname, '..', 'data.sqlite');

function createDb(dbPath = DB_PATH) {
  const db = new Database(dbPath);
  db.pragma('journal_mode = WAL');
  db.pragma('foreign_keys = ON');
  migrate(db);
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
      rank TEXT NOT NULL DEFAULT 'Bronze',
      joined_at TEXT NOT NULL DEFAULT (datetime('now'))
    );

    -- Geography: every pincode belongs to an area (locality), a taluk and a district.
    CREATE TABLE IF NOT EXISTS pincodes (
      pincode TEXT PRIMARY KEY,
      area_name TEXT NOT NULL,
      taluk TEXT NOT NULL,
      district TEXT NOT NULL
    );

    -- One manager per territory per level. territory = pincode | taluk name | district name.
    CREATE TABLE IF NOT EXISTS territory_managers (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      level TEXT NOT NULL CHECK (level IN ('area','taluk','district')),
      territory TEXT NOT NULL,
      user_id INTEGER NOT NULL REFERENCES users(id),
      UNIQUE (level, territory)
    );

    CREATE TABLE IF NOT EXISTS products (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL,
      price REAL NOT NULL
    );

    CREATE TABLE IF NOT EXISTS sales (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      seller_id INTEGER NOT NULL REFERENCES users(id),
      product_id INTEGER NOT NULL REFERENCES products(id),
      customer_name TEXT,
      amount REAL NOT NULL,
      note TEXT,
      created_at TEXT NOT NULL DEFAULT (datetime('now'))
    );

    -- Every rupee of commission is a ledger row. Nothing is ever computed twice.
    CREATE TABLE IF NOT EXISTS commissions (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      user_id INTEGER NOT NULL REFERENCES users(id),
      type TEXT NOT NULL CHECK (type IN (
        'personal_sale','downline_l1','downline_l2',
        'geo_sale_area','geo_sale_taluk','geo_sale_district',
        'join_bonus_area','join_bonus_taluk','join_bonus_district'
      )),
      source_sale_id INTEGER REFERENCES sales(id),
      source_user_id INTEGER REFERENCES users(id),
      rate REAL,
      amount REAL NOT NULL,
      status TEXT NOT NULL DEFAULT 'locked' CHECK (status IN ('locked','paid')),
      created_at TEXT NOT NULL DEFAULT (datetime('now'))
    );
    CREATE INDEX IF NOT EXISTS idx_commissions_user ON commissions(user_id, created_at);

    -- All tunable numbers live here so the coach can change any rate without code changes.
    CREATE TABLE IF NOT EXISTS commission_rules (
      key TEXT PRIMARY KEY,
      value REAL NOT NULL,
      description TEXT
    );

    CREATE TABLE IF NOT EXISTS ranks (
      name TEXT PRIMARY KEY,
      min_personal_sales INTEGER NOT NULL,
      personal_rate REAL NOT NULL,
      sort_order INTEGER NOT NULL
    );

    CREATE TABLE IF NOT EXISTS link_clicks (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      user_id INTEGER NOT NULL REFERENCES users(id),
      clicked_at TEXT NOT NULL DEFAULT (datetime('now'))
    );
  `);

  const seedRule = db.prepare(
    'INSERT OR IGNORE INTO commission_rules (key, value, description) VALUES (?, ?, ?)'
  );
  const defaults = [
    ['downline_l1_rate', 10, '% of a sale paid to the seller\'s direct recruiter'],
    ['downline_l2_rate', 5, '% of a sale paid to the recruiter\'s recruiter'],
    ['geo_sale_area_rate', 3, '% of a sale paid to the area (pincode) manager of the seller'],
    ['geo_sale_taluk_rate', 2, '% of a sale paid to the taluk manager of the seller'],
    ['geo_sale_district_rate', 1, '% of a sale paid to the district manager of the seller'],
    ['join_bonus_area', 100, 'Flat bonus (in rupees) to the area manager when an affiliate joins from their pincode'],
    ['join_bonus_taluk', 50, 'Flat bonus to the taluk manager when an affiliate joins from their taluk'],
    ['join_bonus_district', 25, 'Flat bonus to the district manager when an affiliate joins from their district'],
    ['payout_day', 15, 'Day of the month locked commissions are paid out'],
  ];
  for (const [key, value, description] of defaults) seedRule.run(key, value, description);

  const seedRank = db.prepare(
    'INSERT OR IGNORE INTO ranks (name, min_personal_sales, personal_rate, sort_order) VALUES (?, ?, ?, ?)'
  );
  // Rank is earned by lifetime personal sales; personal_rate is the % the
  // affiliate earns on their own sales at that rank.
  seedRank.run('Bronze', 0, 20, 1);
  seedRank.run('Silver', 5, 22, 2);
  seedRank.run('Gold', 10, 25, 3);
  seedRank.run('Platinum', 17, 30, 4);
}

module.exports = { createDb, DB_PATH };
