const test = require('node:test');
const assert = require('node:assert');
const { createDb } = require('../src/db');
const { registerAffiliate } = require('../src/engine');
const { resolveRef, recordClick, recordConversion } = require('../src/referral');

function setup() {
  const db = createDb(':memory:');
  db.prepare('INSERT INTO pincodes (pincode, area_name, taluk, district) VALUES (?, ?, ?, ?)')
    .run('560001', 'Shivajinagar', 'Bangalore North', 'Bengaluru Urban');
  const top = registerAffiliate(db, { name: 'Top', pincode: '560001' }).userId;
  const affiliate = registerAffiliate(db, { name: 'Aff Iliate', pincode: '560001', sponsorId: top }).userId;
  db.prepare('UPDATE users SET highest_tier_rank = 99').run();
  const code = db.prepare('SELECT referral_code FROM users WHERE id = ?').get(affiliate).referral_code;
  return { db, top, affiliate, code };
}

const commissionsOnPurchase = (db, purchaseId) =>
  db.prepare('SELECT * FROM commissions WHERE source_purchase_id = ?').all(purchaseId);

test('resolveRef finds an affiliate by personal code and by campaign slug', () => {
  const { db, affiliate, code } = setup();
  assert.equal(resolveRef(db, code).referrerId, affiliate);

  const link = db.prepare("INSERT INTO campaign_links (user_id, slug, title) VALUES (?, 'my-slug', 'Camp')").run(affiliate);
  const r = resolveRef(db, 'my-slug');
  assert.equal(r.referrerId, affiliate);
  assert.equal(r.campaignLinkId, link.lastInsertRowid);

  assert.equal(resolveRef(db, 'nope'), null);
});

test('recordClick logs a click for a valid code and still redirects unknown ones', () => {
  const { db, affiliate, code } = setup();
  const r = recordClick(db, code);
  assert.equal(r.matched, true);
  assert.match(r.destination, /epiclife\.academy\/course\.asp\?ref=/);
  assert.equal(db.prepare('SELECT COUNT(*) n FROM link_clicks WHERE user_id = ?').get(affiliate).n, 1);

  const u = recordClick(db, 'bogus');
  assert.equal(u.matched, false);
  assert.match(u.destination, /ref=bogus/);
});

test('a conversion attributes the sale to the referrer and fires the upline cascade', () => {
  const { db, top, affiliate, code } = setup();
  const res = recordConversion(db, {
    ref: code, productCode: 'P1', externalOrderId: 'ORDER-1',
    customerName: 'New Customer', customerEmail: 'cust@example.com', pincode: '560001',
  });
  assert.equal(res.duplicate, false);
  assert.equal(res.referrerId, affiliate);

  // Buyer is a new node sponsored by the affiliate.
  const buyer = db.prepare('SELECT * FROM users WHERE id = ?').get(res.buyerId);
  assert.equal(buyer.sponsor_id, affiliate);
  assert.equal(buyer.email, 'cust@example.com');

  const rows = commissionsOnPurchase(db, res.purchaseId);
  // Affiliate is L-1 (₹2000), Top is L-2 (₹350) on a P1 sale.
  assert.equal(rows.find(r => r.user_id === affiliate && r.level === 1).amount, 2000);
  assert.equal(rows.find(r => r.user_id === top && r.level === 2).amount, 350);
});

test('conversions are idempotent on externalOrderId', () => {
  const { db, code } = setup();
  const a = recordConversion(db, { ref: code, productCode: 'P1', externalOrderId: 'DUP-1', customerEmail: 'x@e.com', pincode: '560001' });
  const b = recordConversion(db, { ref: code, productCode: 'P1', externalOrderId: 'DUP-1', customerEmail: 'x@e.com', pincode: '560001' });
  assert.equal(b.duplicate, true);
  assert.equal(a.purchaseId, b.purchaseId);
  // Exactly one purchase and one L-1 commission for that order.
  assert.equal(db.prepare("SELECT COUNT(*) n FROM purchases WHERE external_order_id = 'DUP-1'").get().n, 1);
});

test('a conversion through a campaign slug is attributed to that campaign', () => {
  const { db, affiliate, code } = setup();
  db.prepare("INSERT INTO campaign_links (user_id, slug, title) VALUES (?, 'spring', 'Spring')").run(affiliate);
  const res = recordConversion(db, { ref: 'spring', productCode: 'P2', externalOrderId: 'ORD-9', customerEmail: 'c9@e.com', pincode: '560001' });
  const purchase = db.prepare('SELECT * FROM purchases WHERE id = ?').get(res.purchaseId);
  const link = db.prepare("SELECT id FROM campaign_links WHERE slug = 'spring'").get();
  assert.equal(purchase.campaign_link_id, link.id);
});

test('geo overrides fire for a registration conversion from a held territory', () => {
  const { db, affiliate, code } = setup();
  // A district holder for Bengaluru Urban.
  const holder = registerAffiliate(db, { name: 'District Holder', pincode: '560001' }).userId;
  db.prepare("INSERT INTO territory_holders (level, territory, user_id) VALUES ('district', 'Bengaluru Urban', ?)").run(holder);

  const res = recordConversion(db, { ref: code, productCode: 'REG', externalOrderId: 'REG-1', customerEmail: 'j@e.com', pincode: '560001' });
  const geo = db.prepare("SELECT * FROM commissions WHERE source_purchase_id = ? AND kind = 'geo_district'").get(res.purchaseId);
  assert.equal(geo.user_id, holder);
  assert.equal(geo.amount, 100);
});
