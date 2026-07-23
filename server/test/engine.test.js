const test = require('node:test');
const assert = require('node:assert');
const { openDb } = require('../src/db');
const { registerAffiliate, recordPurchase, holdersForPincode, nextPayoutDate } = require('../src/engine');
const { getDashboard } = require('../src/dashboard');

async function setup() {
  const db = await openDb({ file: ':memory:' });
  await db.run('INSERT INTO pincodes (pincode, area_name, taluk, district) VALUES (?, ?, ?, ?)', ['560001', 'Shivajinagar', 'Bangalore North', 'Bengaluru Urban']);
  await db.run('INSERT INTO pincodes (pincode, area_name, taluk, district) VALUES (?, ?, ?, ?)', ['560004', 'Basavanagudi', 'Bangalore South', 'Bengaluru Urban']);
  return db;
}

const c = (db, userId) => db.all('SELECT * FROM commissions WHERE user_id = ? ORDER BY id', [userId]);
const sum = async (db, userId) => (await db.get('SELECT COALESCE(SUM(amount),0) AS t FROM commissions WHERE user_id = ?', [userId])).t;

async function chain(db, depth, pincode = '560001') {
  const ids = [];
  let sponsor = null;
  for (let i = 0; i < depth; i++) {
    const { userId } = await registerAffiliate(db, { name: `U${i}`, pincode, sponsorId: sponsor });
    ids.push(userId);
    sponsor = userId;
  }
  return ids;
}

const maxOutTiers = (db) => db.run('UPDATE users SET highest_tier_rank = 99', []);

test('registration pays ₹100 to the direct sponsor (L-1) and ₹5 up the chain', async () => {
  const db = await setup();
  const ids = await chain(db, 13);
  await maxOutTiers(db);
  const { userId: buyer } = await registerAffiliate(db, { name: 'Buyer', pincode: '560001', sponsorId: ids[12] });
  await maxOutTiers(db);

  assert.equal((await c(db, ids[12])).filter(x => x.source_user_id === buyer && x.level === 1)[0].amount, 100);
  assert.equal((await c(db, ids[11])).filter(x => x.source_user_id === buyer && x.level === 2)[0].amount, 5);
  assert.equal((await c(db, ids[1])).filter(x => x.source_user_id === buyer && x.level === 12)[0].amount, 5);
  assert.equal((await c(db, ids[0])).filter(x => x.source_user_id === buyer).length, 0);
});

test('package 5 pays the full 12-level table to a qualified upline', async () => {
  const db = await setup();
  const ids = await chain(db, 12);
  await maxOutTiers(db);
  const buyer = ids[11];
  const { purchaseId } = await recordPurchase(db, { buyerId: buyer, productCode: 'P5' });
  const expected = [51000, 8000, 3500, 2000, 1000, 600, 300, 200, 200, 100, 100, 100];
  for (let level = 1; level <= 11; level++) {
    const ancestor = ids[11 - level];
    const row = (await c(db, ancestor)).find(x => x.source_purchase_id === purchaseId && x.level === level);
    assert.equal(row.amount, expected[level - 1], `L-${level}`);
  }
});

test('qualification gate forfeits the L-1 payout when the sponsor under-invested', async () => {
  const db = await setup();
  const { userId: sponsor } = await registerAffiliate(db, { name: 'Sponsor', pincode: '560001' });
  const { userId: buyer } = await registerAffiliate(db, { name: 'Buyer', pincode: '560001', sponsorId: sponsor });
  const result = await recordPurchase(db, { buyerId: buyer, productCode: 'P5' });
  assert.equal((await c(db, sponsor)).filter(x => x.source_purchase_id === result.purchaseId).length, 0);
  assert.equal(result.forfeited.find(f => f.level === 1).amount, 51000);
});

test('a qualified sponsor earns; the gate can be turned off', async () => {
  const db = await setup();
  const { userId: sponsor } = await registerAffiliate(db, { name: 'Sponsor', pincode: '560001' });
  const { userId: buyer } = await registerAffiliate(db, { name: 'Buyer', pincode: '560001', sponsorId: sponsor });
  await recordPurchase(db, { buyerId: sponsor, productCode: 'P5' });
  const p5 = await recordPurchase(db, { buyerId: buyer, productCode: 'P5' });
  assert.equal((await c(db, sponsor)).find(x => x.source_purchase_id === p5.purchaseId && x.level === 1).amount, 51000);

  await db.run("UPDATE settings SET value = 0 WHERE key = 'qualification_gate'", []);
  const { userId: s2 } = await registerAffiliate(db, { name: 'S2', pincode: '560001' });
  const { userId: b2 } = await registerAffiliate(db, { name: 'B2', pincode: '560001', sponsorId: s2 });
  const p4 = await recordPurchase(db, { buyerId: b2, productCode: 'P4' });
  assert.equal((await c(db, s2)).find(x => x.source_purchase_id === p4.purchaseId && x.level === 1).amount, 35000);
});

test('registration pays ₹100 each to the area, taluk and district holders', async () => {
  const db = await setup();
  const area = (await registerAffiliate(db, { name: 'Area', pincode: '560004' })).userId;
  const taluk = (await registerAffiliate(db, { name: 'Taluk', pincode: '560004' })).userId;
  const district = (await registerAffiliate(db, { name: 'Dist', pincode: '560004' })).userId;
  await db.run('INSERT INTO territory_holders (level, territory, user_id) VALUES (?, ?, ?)', ['area', '560001', area]);
  await db.run('INSERT INTO territory_holders (level, territory, user_id) VALUES (?, ?, ?)', ['taluk', 'Bangalore North', taluk]);
  await db.run('INSERT INTO territory_holders (level, territory, user_id) VALUES (?, ?, ?)', ['district', 'Bengaluru Urban', district]);

  const before = { area: await sum(db, area), taluk: await sum(db, taluk), district: await sum(db, district) };
  await registerAffiliate(db, { name: 'New', pincode: '560001' });

  assert.equal(await sum(db, area) - before.area, 100);
  assert.equal(await sum(db, taluk) - before.taluk, 100);
  assert.equal(await sum(db, district) - before.district, 100);
});

test('buying Package 3 grants PIN-code territory; Package 5 grants taluk', async () => {
  const db = await setup();
  const a = (await registerAffiliate(db, { name: 'A', pincode: '560001' })).userId;
  await recordPurchase(db, { buyerId: a, productCode: 'P3' });
  assert.equal((await holdersForPincode(db, '560001')).area, a);

  const b = (await registerAffiliate(db, { name: 'B', pincode: '560004' })).userId;
  await recordPurchase(db, { buyerId: b, productCode: 'P5' });
  assert.equal((await holdersForPincode(db, '560004')).taluk, b);
});

test('territory is protected: a second buyer does not displace the holder', async () => {
  const db = await setup();
  const first = (await registerAffiliate(db, { name: 'First', pincode: '560001' })).userId;
  const second = (await registerAffiliate(db, { name: 'Second', pincode: '560001' })).userId;
  await recordPurchase(db, { buyerId: first, productCode: 'P3' });
  await recordPurchase(db, { buyerId: second, productCode: 'P3' });
  assert.equal((await holdersForPincode(db, '560001')).area, first);
});

test('a holder earns no geo override on their own purchase', async () => {
  const db = await setup();
  const holder = (await registerAffiliate(db, { name: 'H', pincode: '560001' })).userId;
  await recordPurchase(db, { buyerId: holder, productCode: 'P3' });
  await recordPurchase(db, { buyerId: holder, productCode: 'P1' });
  const geoRows = (await c(db, holder)).filter(x => x.kind.startsWith('geo'));
  assert.equal(geoRows.length, 0);
});

test('short chains forfeit the deep levels (no compression)', async () => {
  const db = await setup();
  const top = (await registerAffiliate(db, { name: 'Top', pincode: '560001' })).userId;
  const mid = (await registerAffiliate(db, { name: 'Mid', pincode: '560001', sponsorId: top })).userId;
  const leaf = (await registerAffiliate(db, { name: 'Leaf', pincode: '560001', sponsorId: mid })).userId;
  await maxOutTiers(db);
  const res = await recordPurchase(db, { buyerId: leaf, productCode: 'P2' });
  assert.equal((await c(db, mid)).find(x => x.source_purchase_id === res.purchaseId && x.level === 1).amount, 3000);
  assert.equal((await c(db, top)).find(x => x.source_purchase_id === res.purchaseId && x.level === 2).amount, 1000);
  assert.equal(res.paid.filter(p => p.level >= 3).length, 0);
});

test('nextPayoutDate rolls to next month after the payout day', async () => {
  const db = await setup();
  assert.equal((await nextPayoutDate(db, new Date(2026, 6, 18))).getMonth(), 7);
  assert.equal((await nextPayoutDate(db, new Date(2026, 6, 10))).getDate(), 15);
});

test('dashboard aggregates earnings, conversions and rank progress', async () => {
  const db = await setup();
  const jess = (await registerAffiliate(db, { name: 'Jessica', pincode: '560001' })).userId;
  await maxOutTiers(db);
  const r1 = (await registerAffiliate(db, { name: 'R1', pincode: '560001', sponsorId: jess })).userId;
  await registerAffiliate(db, { name: 'R2', pincode: '560001', sponsorId: jess });
  await registerAffiliate(db, { name: 'R3', pincode: '560001', sponsorId: jess });
  await maxOutTiers(db);
  await recordPurchase(db, { buyerId: r1, productCode: 'P1' });

  const dash = await getDashboard(db, jess);
  assert.equal(dash.conversions, 4);
  assert.equal(dash.totalEarnedThisMonth, 300 + 2000);
  assert.equal(dash.nextPayout.amount, 2300);
  assert.equal(dash.rankProgress.currentRank, 'Bronze');
  assert.equal(dash.rankProgress.nextRank, 'Silver');
});
