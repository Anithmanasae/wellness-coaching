const test = require('node:test');
const assert = require('node:assert');
const { createDb } = require('../src/db');
const { registerAffiliate, recordSale, managersForPincode, nextPayoutDate } = require('../src/engine');
const { getDashboard } = require('../src/dashboard');

function setup() {
  const db = createDb(':memory:');
  db.prepare('INSERT INTO pincodes (pincode, area_name, taluk, district) VALUES (?, ?, ?, ?)')
    .run('560001', 'Shivajinagar', 'Bangalore North', 'Bengaluru Urban');
  db.prepare('INSERT INTO pincodes (pincode, area_name, taluk, district) VALUES (?, ?, ?, ?)')
    .run('560004', 'Basavanagudi', 'Bangalore South', 'Bengaluru Urban');
  const product = db.prepare('INSERT INTO products (name, price) VALUES (?, ?)').run('Cleanse', 1000).lastInsertRowid;
  return { db, product };
}

function commissionsFor(db, userId) {
  return db.prepare('SELECT * FROM commissions WHERE user_id = ? ORDER BY id').all(userId);
}

test('personal sale pays the seller their rank rate', () => {
  const { db, product } = setup();
  const a = registerAffiliate(db, { name: 'A', pincode: '560001' });
  recordSale(db, { sellerId: a, productId: product });
  const rows = commissionsFor(db, a);
  assert.equal(rows.length, 1);
  assert.equal(rows[0].type, 'personal_sale');
  assert.equal(rows[0].amount, 200); // Bronze 20% of 1000
});

test('downline overrides flow up exactly two levels', () => {
  const { db, product } = setup();
  const top = registerAffiliate(db, { name: 'Top', pincode: '560001' });
  const mid = registerAffiliate(db, { name: 'Mid', pincode: '560001', sponsorId: top });
  const leaf = registerAffiliate(db, { name: 'Leaf', pincode: '560001', sponsorId: mid });
  const above = registerAffiliate(db, { name: 'Above', pincode: '560001' });
  db.prepare('UPDATE users SET sponsor_id = ? WHERE id = ?').run(above, top); // 3 levels above leaf
  recordSale(db, { sellerId: leaf, productId: product });

  assert.equal(commissionsFor(db, mid).find(c => c.type === 'downline_l1').amount, 100); // 10%
  assert.equal(commissionsFor(db, top).find(c => c.type === 'downline_l2').amount, 50); // 5%
  assert.equal(commissionsFor(db, above).length, 0); // level 3 earns nothing
});

test('geo managers earn overrides on sales from their territory', () => {
  const { db, product } = setup();
  const area = registerAffiliate(db, { name: 'Area', pincode: '560004' });
  const taluk = registerAffiliate(db, { name: 'Taluk', pincode: '560004' });
  const district = registerAffiliate(db, { name: 'District', pincode: '560004' });
  const insMgr = db.prepare('INSERT INTO territory_managers (level, territory, user_id) VALUES (?, ?, ?)');
  insMgr.run('area', '560001', area);
  insMgr.run('taluk', 'Bangalore North', taluk);
  insMgr.run('district', 'Bengaluru Urban', district);

  const seller = registerAffiliate(db, { name: 'S', pincode: '560001' });
  recordSale(db, { sellerId: seller, productId: product });

  assert.equal(commissionsFor(db, area).find(c => c.type === 'geo_sale_area').amount, 30); // 3%
  assert.equal(commissionsFor(db, taluk).find(c => c.type === 'geo_sale_taluk').amount, 20); // 2%
  assert.equal(commissionsFor(db, district).find(c => c.type === 'geo_sale_district').amount, 10); // 1%
});

test('geo managers earn a flat bonus when an affiliate joins from their territory', () => {
  const { db } = setup();
  const area = registerAffiliate(db, { name: 'Area', pincode: '560004' });
  const taluk = registerAffiliate(db, { name: 'Taluk', pincode: '560004' });
  const district = registerAffiliate(db, { name: 'District', pincode: '560004' });
  const insMgr = db.prepare('INSERT INTO territory_managers (level, territory, user_id) VALUES (?, ?, ?)');
  insMgr.run('area', '560001', area);
  insMgr.run('taluk', 'Bangalore North', taluk);
  insMgr.run('district', 'Bengaluru Urban', district);

  registerAffiliate(db, { name: 'New', pincode: '560001' });

  assert.equal(commissionsFor(db, area).find(c => c.type === 'join_bonus_area').amount, 100);
  assert.equal(commissionsFor(db, taluk).find(c => c.type === 'join_bonus_taluk').amount, 50);
  assert.equal(commissionsFor(db, district).find(c => c.type === 'join_bonus_district').amount, 25);
});

test('a join from a different taluk pays only the district manager', () => {
  const { db } = setup();
  const taluk = registerAffiliate(db, { name: 'Taluk', pincode: '560004' });
  const district = registerAffiliate(db, { name: 'District', pincode: '560004' });
  const insMgr = db.prepare('INSERT INTO territory_managers (level, territory, user_id) VALUES (?, ?, ?)');
  insMgr.run('taluk', 'Bangalore North', taluk);
  insMgr.run('district', 'Bengaluru Urban', district);

  registerAffiliate(db, { name: 'New', pincode: '560004' }); // Bangalore South

  assert.equal(commissionsFor(db, taluk).some(c => c.type === 'join_bonus_taluk'), false);
  assert.equal(commissionsFor(db, district).find(c => c.type === 'join_bonus_district').amount, 25);
});

test('a manager earns no geo override on their own sale', () => {
  const { db, product } = setup();
  const mgr = registerAffiliate(db, { name: 'Mgr', pincode: '560001' });
  db.prepare('INSERT INTO territory_managers (level, territory, user_id) VALUES (?, ?, ?)')
    .run('area', '560001', mgr);
  recordSale(db, { sellerId: mgr, productId: product });
  const rows = commissionsFor(db, mgr);
  assert.equal(rows.filter(c => c.type === 'geo_sale_area').length, 0);
  assert.equal(rows.filter(c => c.type === 'personal_sale').length, 1);
});

test('rank promotes with sales count and raises the personal rate', () => {
  const { db, product } = setup();
  const a = registerAffiliate(db, { name: 'A', pincode: '560001' });
  for (let i = 0; i < 5; i++) recordSale(db, { sellerId: a, productId: product });
  assert.equal(db.prepare('SELECT rank FROM users WHERE id = ?').get(a).rank, 'Silver');
  recordSale(db, { sellerId: a, productId: product });
  const rows = commissionsFor(db, a);
  assert.equal(rows[rows.length - 1].amount, 220); // Silver 22% of 1000
});

test('managersForPincode resolves all three levels', () => {
  const { db } = setup();
  const u = registerAffiliate(db, { name: 'U', pincode: '560004' });
  db.prepare('INSERT INTO territory_managers (level, territory, user_id) VALUES (?, ?, ?)')
    .run('district', 'Bengaluru Urban', u);
  const m = managersForPincode(db, '560001');
  assert.equal(m.area, null);
  assert.equal(m.taluk, null);
  assert.equal(m.district, u);
});

test('nextPayoutDate rolls to next month after the payout day', () => {
  const { db } = setup();
  assert.equal(nextPayoutDate(db, new Date(2026, 6, 18)).getMonth(), 7); // Jul 18 -> Aug 15
  assert.equal(nextPayoutDate(db, new Date(2026, 6, 10)).getDate(), 15); // Jul 10 -> Jul 15
  assert.equal(nextPayoutDate(db, new Date(2026, 6, 10)).getMonth(), 6);
});

test('dashboard aggregates earnings, locked payout and rank progress', () => {
  const { db, product } = setup();
  const sponsor = registerAffiliate(db, { name: 'Sponsor', pincode: '560001' });
  const a = registerAffiliate(db, { name: 'A', pincode: '560001', sponsorId: sponsor });
  recordSale(db, { sellerId: a, productId: product, customerName: 'C1' });
  const dash = getDashboard(db, a);
  assert.equal(dash.totalEarnedThisMonth, 200);
  assert.equal(dash.conversions, 1);
  assert.equal(dash.nextPayout.amount, 200);
  assert.equal(dash.rankProgress.currentRank, 'Bronze');
  assert.equal(dash.rankProgress.nextRank, 'Silver');
  assert.equal(dash.rankProgress.salesToNext, 4);
  assert.equal(dash.recentConversions[0].name, 'C1');
});
