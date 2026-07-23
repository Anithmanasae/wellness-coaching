const test = require('node:test');
const assert = require('node:assert');
const { createDb } = require('../src/db');
const { registerAffiliate, recordPurchase, holdersForPincode, nextPayoutDate } = require('../src/engine');
const { getDashboard } = require('../src/dashboard');

function setup() {
  const db = createDb(':memory:');
  db.prepare('INSERT INTO pincodes (pincode, area_name, taluk, district) VALUES (?, ?, ?, ?)')
    .run('560001', 'Shivajinagar', 'Bangalore North', 'Bengaluru Urban');
  db.prepare('INSERT INTO pincodes (pincode, area_name, taluk, district) VALUES (?, ?, ?, ?)')
    .run('560004', 'Basavanagudi', 'Bangalore South', 'Bengaluru Urban');
  return db;
}

const c = (db, userId) => db.prepare('SELECT * FROM commissions WHERE user_id = ? ORDER BY id').all(userId);
const sum = (db, userId) => db.prepare('SELECT COALESCE(SUM(amount),0) AS t FROM commissions WHERE user_id = ?').get(userId).t;

// Build a straight chain of `depth` affiliates. Returns ids top-first.
function chain(db, depth, pincode = '560001') {
  const ids = [];
  let sponsor = null;
  for (let i = 0; i < depth; i++) {
    const { userId } = registerAffiliate(db, { name: `U${i}`, pincode, sponsorId: sponsor });
    ids.push(userId);
    sponsor = userId;
  }
  return ids;
}

// Give everyone the top tier so the qualification gate never interferes.
function maxOutTiers(db) {
  db.prepare('UPDATE users SET highest_tier_rank = 99').run();
}

test('registration pays ₹100 to the direct sponsor (L-1) and ₹5 up the chain', () => {
  const db = setup();
  const ids = chain(db, 13); // 1 root + 12 ancestors above the last joiner
  maxOutTiers(db);
  // The 13th registration already happened during chain(); inspect it via a fresh join.
  const { userId: buyer } = registerAffiliate(db, { name: 'Buyer', pincode: '560001', sponsorId: ids[12] });
  db.prepare('UPDATE users SET highest_tier_rank = 99').run();

  // L-1 is ids[12], L-2 ids[11], ... L-12 ids[1]. ids[0] is L-13 -> nothing.
  assert.equal(c(db, ids[12]).filter(x => x.source_user_id === buyer && x.level === 1)[0].amount, 100);
  assert.equal(c(db, ids[11]).filter(x => x.source_user_id === buyer && x.level === 2)[0].amount, 5);
  assert.equal(c(db, ids[1]).filter(x => x.source_user_id === buyer && x.level === 12)[0].amount, 5);
  assert.equal(c(db, ids[0]).filter(x => x.source_user_id === buyer).length, 0); // 13th level: no compression
});

test('package 5 pays the full 12-level table to a qualified upline', () => {
  const db = setup();
  const ids = chain(db, 12);
  maxOutTiers(db);
  const buyer = ids[11];
  const { purchaseId } = recordPurchase(db, { buyerId: buyer, productCode: 'P5' });
  const expected = [51000, 8000, 3500, 2000, 1000, 600, 300, 200, 200, 100, 100, 100];
  // ancestor at level L is ids[11-L]
  for (let level = 1; level <= 11; level++) {
    const ancestor = ids[11 - level];
    const row = c(db, ancestor).find(x => x.source_purchase_id === purchaseId && x.level === level);
    assert.equal(row.amount, expected[level - 1], `L-${level}`);
  }
});

test('qualification gate forfeits the L-1 payout when the sponsor under-invested', () => {
  const db = setup();
  const { userId: sponsor } = registerAffiliate(db, { name: 'Sponsor', pincode: '560001' });
  const { userId: buyer } = registerAffiliate(db, { name: 'Buyer', pincode: '560001', sponsorId: sponsor });
  // Sponsor owns only REG (tier 0). Buyer purchases P5 (tier 7).
  const result = recordPurchase(db, { buyerId: buyer, productCode: 'P5' });
  // Sponsor earns nothing from this purchase; the ₹51,000 L-1 is forfeited.
  assert.equal(c(db, sponsor).filter(x => x.source_purchase_id === result.purchaseId).length, 0);
  assert.equal(result.forfeited.find(f => f.level === 1).amount, 51000);
});

test('a qualified sponsor (owns equal tier) earns; gate can be turned off', () => {
  const db = setup();
  const { userId: sponsor } = registerAffiliate(db, { name: 'Sponsor', pincode: '560001' });
  const { userId: buyer } = registerAffiliate(db, { name: 'Buyer', pincode: '560001', sponsorId: sponsor });
  recordPurchase(db, { buyerId: sponsor, productCode: 'P5' }); // sponsor now tier 7
  const p5 = recordPurchase(db, { buyerId: buyer, productCode: 'P5' });
  assert.equal(c(db, sponsor).find(x => x.source_purchase_id === p5.purchaseId && x.level === 1).amount, 51000);

  // Turn the gate off: even a REG-only sponsor earns.
  db.prepare("UPDATE settings SET value = 0 WHERE key = 'qualification_gate'").run();
  const { userId: s2 } = registerAffiliate(db, { name: 'S2', pincode: '560001' });
  const { userId: b2 } = registerAffiliate(db, { name: 'B2', pincode: '560001', sponsorId: s2 });
  const p4 = recordPurchase(db, { buyerId: b2, productCode: 'P4' });
  assert.equal(c(db, s2).find(x => x.source_purchase_id === p4.purchaseId && x.level === 1).amount, 35000);
});

test('registration pays ₹100 each to the area, taluk and district holders', () => {
  const db = setup();
  const area = registerAffiliate(db, { name: 'Area', pincode: '560004' }).userId;
  const taluk = registerAffiliate(db, { name: 'Taluk', pincode: '560004' }).userId;
  const district = registerAffiliate(db, { name: 'Dist', pincode: '560004' }).userId;
  const ins = db.prepare('INSERT INTO territory_holders (level, territory, user_id) VALUES (?, ?, ?)');
  ins.run('area', '560001', area);
  ins.run('taluk', 'Bangalore North', taluk);
  ins.run('district', 'Bengaluru Urban', district);

  const before = { area: sum(db, area), taluk: sum(db, taluk), district: sum(db, district) };
  registerAffiliate(db, { name: 'New', pincode: '560001' });

  assert.equal(sum(db, area) - before.area, 100);
  assert.equal(sum(db, taluk) - before.taluk, 100);
  assert.equal(sum(db, district) - before.district, 100);
});

test('buying Package 3 grants PIN-code territory; Package 5 grants taluk', () => {
  const db = setup();
  const a = registerAffiliate(db, { name: 'A', pincode: '560001' }).userId;
  recordPurchase(db, { buyerId: a, productCode: 'P3' });
  assert.equal(holdersForPincode(db, '560001').area, a);

  const b = registerAffiliate(db, { name: 'B', pincode: '560004' }).userId;
  recordPurchase(db, { buyerId: b, productCode: 'P5' });
  // 560004 is in Bangalore South taluk; any 560004 pincode now resolves to b as taluk holder.
  assert.equal(holdersForPincode(db, '560004').taluk, b);
});

test('territory is protected: a second buyer does not displace the holder', () => {
  const db = setup();
  const first = registerAffiliate(db, { name: 'First', pincode: '560001' }).userId;
  const second = registerAffiliate(db, { name: 'Second', pincode: '560001' }).userId;
  recordPurchase(db, { buyerId: first, productCode: 'P3' });
  recordPurchase(db, { buyerId: second, productCode: 'P3' });
  assert.equal(holdersForPincode(db, '560001').area, first);
});

test('a holder earns no geo override on their own purchase', () => {
  const db = setup();
  const holder = registerAffiliate(db, { name: 'H', pincode: '560001' }).userId;
  recordPurchase(db, { buyerId: holder, productCode: 'P3' }); // becomes area holder
  const before = sum(db, holder);
  recordPurchase(db, { buyerId: holder, productCode: 'P1' }); // P1 geo is 0 anyway
  const geoRows = c(db, holder).filter(x => x.kind.startsWith('geo'));
  assert.equal(geoRows.length, 0);
  assert.ok(sum(db, holder) >= before);
});

test('short chains forfeit the deep levels (no compression)', () => {
  const db = setup();
  const top = registerAffiliate(db, { name: 'Top', pincode: '560001' }).userId;
  const mid = registerAffiliate(db, { name: 'Mid', pincode: '560001', sponsorId: top }).userId;
  const leaf = registerAffiliate(db, { name: 'Leaf', pincode: '560001', sponsorId: mid }).userId;
  db.prepare('UPDATE users SET highest_tier_rank = 99').run();
  const res = recordPurchase(db, { buyerId: leaf, productCode: 'P2' });
  // Only mid (L-1) and top (L-2) exist. L-3..L-12 paid to nobody.
  assert.equal(c(db, mid).find(x => x.source_purchase_id === res.purchaseId && x.level === 1).amount, 3000);
  assert.equal(c(db, top).find(x => x.source_purchase_id === res.purchaseId && x.level === 2).amount, 1000);
  assert.equal(res.paid.filter(p => p.level >= 3).length, 0);
});

test('nextPayoutDate rolls to next month after the payout day', () => {
  const db = setup();
  assert.equal(nextPayoutDate(db, new Date(2026, 6, 18)).getMonth(), 7);
  assert.equal(nextPayoutDate(db, new Date(2026, 6, 10)).getDate(), 15);
});

test('dashboard aggregates earnings, conversions and rank progress', () => {
  const db = setup();
  const jess = registerAffiliate(db, { name: 'Jessica', pincode: '560001' }).userId;
  db.prepare('UPDATE users SET highest_tier_rank = 99').run();
  // 3 direct recruits register under Jessica -> 3 conversions, 3 x ₹100 L-1.
  const r1 = registerAffiliate(db, { name: 'R1', pincode: '560001', sponsorId: jess }).userId;
  registerAffiliate(db, { name: 'R2', pincode: '560001', sponsorId: jess });
  registerAffiliate(db, { name: 'R3', pincode: '560001', sponsorId: jess });
  db.prepare('UPDATE users SET highest_tier_rank = 99').run();
  recordPurchase(db, { buyerId: r1, productCode: 'P1' }); // +₹2000 L-1 for Jessica

  const dash = getDashboard(db, jess);
  assert.equal(dash.conversions, 4); // 3 registrations + 1 package purchase by recruits
  assert.equal(dash.totalEarnedThisMonth, 300 + 2000);
  assert.equal(dash.nextPayout.amount, 2300);
  assert.equal(dash.rankProgress.currentRank, 'Bronze');
  assert.equal(dash.rankProgress.nextRank, 'Silver');
});
