const test = require('node:test');
const assert = require('node:assert');
const { openDb } = require('../src/db');
const { registerAffiliate, recordPurchase } = require('../src/engine');
const { getWallet, requestPayout, approvePayout, settlePayout, rejectPayout } = require('../src/wallet');

async function setup() {
  const db = await openDb({ file: ':memory:' });
  await db.run('INSERT INTO pincodes (pincode, area_name, taluk, district) VALUES (?, ?, ?, ?)', ['560001', 'Shivajinagar', 'Bangalore North', 'Bengaluru Urban']);
  const sponsor = (await registerAffiliate(db, { name: 'Sponsor', pincode: '560001' })).userId;
  await db.run('UPDATE users SET highest_tier_rank = 99', []);
  const recruit = (await registerAffiliate(db, { name: 'Recruit', pincode: '560001', sponsorId: sponsor })).userId;
  await recordPurchase(db, { buyerId: recruit, productCode: 'P2' });
  return { db, sponsor };
}

const locked = async (db, u) => (await db.get(`SELECT COALESCE(SUM(amount),0) t FROM commissions WHERE user_id=? AND status='locked'`, [u])).t;

test('requesting a payout reserves commissions but pays nothing', async () => {
  const { db, sponsor } = await setup();
  const before = await locked(db, sponsor);
  assert.ok(before > 0);

  const r = await requestPayout(db, sponsor, {});
  assert.equal(r.status, 'requested');
  assert.equal(r.amount, before);
  assert.equal(await locked(db, sponsor), 0);

  const w = await getWallet(db, sponsor);
  assert.equal(w.hasPendingRequest, true);
  assert.equal(w.totalPayoutsToDate, 0);
  assert.equal(w.pendingCommissions, before);
});

test('a second request while one is pending is rejected', async () => {
  const { db, sponsor } = await setup();
  await requestPayout(db, sponsor, {});
  await assert.rejects(() => requestPayout(db, sponsor, {}), /awaiting approval/);
});

test('coach approve then settle pays the affiliate', async () => {
  const { db, sponsor } = await setup();
  const amount = await locked(db, sponsor);
  const { payoutId } = await requestPayout(db, sponsor, {});

  assert.equal((await approvePayout(db, payoutId)).status, 'processing');
  assert.equal((await getWallet(db, sponsor)).totalPayoutsToDate, 0);

  assert.equal((await settlePayout(db, payoutId)).status, 'paid');
  const w = await getWallet(db, sponsor);
  assert.equal(w.totalPayoutsToDate, amount);
  assert.equal(w.pendingCommissions, 0);
  assert.equal(w.hasPendingRequest, false);
});

test('coach reject releases the reserved commissions', async () => {
  const { db, sponsor } = await setup();
  const amount = await locked(db, sponsor);
  const { payoutId } = await requestPayout(db, sponsor, {});
  assert.equal(await locked(db, sponsor), 0);

  assert.equal((await rejectPayout(db, payoutId)).status, 'rejected');
  assert.equal(await locked(db, sponsor), amount);
  assert.equal((await getWallet(db, sponsor)).hasPendingRequest, false);
  await assert.doesNotReject(() => requestPayout(db, sponsor, {}));
});

test('cannot settle a payout that was never approved', async () => {
  const { db, sponsor } = await setup();
  const { payoutId } = await requestPayout(db, sponsor, {});
  await assert.rejects(() => settlePayout(db, payoutId), /Cannot settle/);
});
