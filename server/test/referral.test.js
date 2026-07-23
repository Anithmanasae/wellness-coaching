const test = require('node:test');
const assert = require('node:assert');
const { openDb } = require('../src/db');
const { registerAffiliate } = require('../src/engine');
const { resolveRef, recordClick, recordConversion } = require('../src/referral');

async function setup() {
  const db = await openDb({ file: ':memory:' });
  await db.run('INSERT INTO pincodes (pincode, area_name, taluk, district) VALUES (?, ?, ?, ?)', ['560001', 'Shivajinagar', 'Bangalore North', 'Bengaluru Urban']);
  const top = (await registerAffiliate(db, { name: 'Top', pincode: '560001' })).userId;
  const affiliate = (await registerAffiliate(db, { name: 'Aff Iliate', pincode: '560001', sponsorId: top })).userId;
  await db.run('UPDATE users SET highest_tier_rank = 99', []);
  const code = (await db.get('SELECT referral_code FROM users WHERE id = ?', [affiliate])).referral_code;
  return { db, top, affiliate, code };
}

const onPurchase = (db, purchaseId) => db.all('SELECT * FROM commissions WHERE source_purchase_id = ?', [purchaseId]);

test('resolveRef finds an affiliate by personal code and by campaign slug', async () => {
  const { db, affiliate, code } = await setup();
  assert.equal((await resolveRef(db, code)).referrerId, affiliate);

  const link = await db.get("INSERT INTO campaign_links (user_id, slug, title) VALUES (?, 'my-slug', 'Camp') RETURNING id", [affiliate]);
  const r = await resolveRef(db, 'my-slug');
  assert.equal(r.referrerId, affiliate);
  assert.equal(r.campaignLinkId, link.id);

  assert.equal(await resolveRef(db, 'nope'), null);
});

test('recordClick logs a click for a valid code and still redirects unknown ones', async () => {
  const { db, affiliate, code } = await setup();
  const r = await recordClick(db, code);
  assert.equal(r.matched, true);
  assert.match(r.destination, /epiclife\.academy\/course\.asp\?ref=/);
  assert.equal((await db.get('SELECT COUNT(*) n FROM link_clicks WHERE user_id = ?', [affiliate])).n, 1);

  const u = await recordClick(db, 'bogus');
  assert.equal(u.matched, false);
  assert.match(u.destination, /ref=bogus/);
});

test('a conversion attributes the sale to the referrer and fires the upline cascade', async () => {
  const { db, top, affiliate, code } = await setup();
  const res = await recordConversion(db, {
    ref: code, productCode: 'P1', externalOrderId: 'ORDER-1',
    customerName: 'New Customer', customerEmail: 'cust@example.com', pincode: '560001',
  });
  assert.equal(res.duplicate, false);
  assert.equal(res.referrerId, affiliate);

  const buyer = await db.get('SELECT * FROM users WHERE id = ?', [res.buyerId]);
  assert.equal(buyer.sponsor_id, affiliate);
  assert.equal(buyer.email, 'cust@example.com');

  const rows = await onPurchase(db, res.purchaseId);
  assert.equal(rows.find(r => r.user_id === affiliate && r.level === 1).amount, 2000);
  assert.equal(rows.find(r => r.user_id === top && r.level === 2).amount, 350);
});

test('conversions are idempotent on externalOrderId', async () => {
  const { db, code } = await setup();
  const a = await recordConversion(db, { ref: code, productCode: 'P1', externalOrderId: 'DUP-1', customerEmail: 'x@e.com', pincode: '560001' });
  const b = await recordConversion(db, { ref: code, productCode: 'P1', externalOrderId: 'DUP-1', customerEmail: 'x@e.com', pincode: '560001' });
  assert.equal(b.duplicate, true);
  assert.equal(a.purchaseId, b.purchaseId);
  assert.equal((await db.get("SELECT COUNT(*) n FROM purchases WHERE external_order_id = 'DUP-1'")).n, 1);
});

test('a conversion through a campaign slug is attributed to that campaign', async () => {
  const { db, affiliate, code } = await setup();
  await db.run("INSERT INTO campaign_links (user_id, slug, title) VALUES (?, 'spring', 'Spring')", [affiliate]);
  const res = await recordConversion(db, { ref: 'spring', productCode: 'P2', externalOrderId: 'ORD-9', customerEmail: 'c9@e.com', pincode: '560001' });
  const purchase = await db.get('SELECT * FROM purchases WHERE id = ?', [res.purchaseId]);
  const link = await db.get("SELECT id FROM campaign_links WHERE slug = 'spring'");
  assert.equal(purchase.campaign_link_id, link.id);
});

test('geo overrides fire for a registration conversion from a held territory', async () => {
  const { db, code } = await setup();
  const holder = (await registerAffiliate(db, { name: 'District Holder', pincode: '560001' })).userId;
  await db.run("INSERT INTO territory_holders (level, territory, user_id) VALUES ('district', 'Bengaluru Urban', ?)", [holder]);

  const res = await recordConversion(db, { ref: code, productCode: 'REG', externalOrderId: 'REG-1', customerEmail: 'j@e.com', pincode: '560001' });
  const geo = await db.get("SELECT * FROM commissions WHERE source_purchase_id = ? AND kind = 'geo_district'", [res.purchaseId]);
  assert.equal(geo.user_id, holder);
  assert.equal(geo.amount, 100);
});
