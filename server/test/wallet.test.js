const test = require('node:test');
const assert = require('node:assert');
const { createDb } = require('../src/db');
const { registerAffiliate, recordPurchase } = require('../src/engine');
const { getWallet, requestPayout, approvePayout, settlePayout, rejectPayout } = require('../src/wallet');

function setup() {
  const db = createDb(':memory:');
  db.prepare('INSERT INTO pincodes (pincode, area_name, taluk, district) VALUES (?, ?, ?, ?)')
    .run('560001', 'Shivajinagar', 'Bangalore North', 'Bengaluru Urban');
  // A sponsor who has earned a locked balance from a recruit's purchase.
  const sponsor = registerAffiliate(db, { name: 'Sponsor', pincode: '560001' }).userId;
  db.prepare('UPDATE users SET highest_tier_rank = 99').run();
  const recruit = registerAffiliate(db, { name: 'Recruit', pincode: '560001', sponsorId: sponsor }).userId;
  recordPurchase(db, { buyerId: recruit, productCode: 'P2' }); // sponsor earns L-1 ₹3000 + ₹100 reg
  return { db, sponsor };
}

const locked = (db, u) => db.prepare(`SELECT COALESCE(SUM(amount),0) t FROM commissions WHERE user_id=? AND status='locked'`).get(u).t;

test('requesting a payout reserves commissions but pays nothing', () => {
  const { db, sponsor } = setup();
  const before = locked(db, sponsor);
  assert.ok(before > 0);

  const r = requestPayout(db, sponsor, {});
  assert.equal(r.status, 'requested');
  assert.equal(r.amount, before);
  assert.equal(locked(db, sponsor), 0); // reserved, no longer 'locked'

  const w = getWallet(db, sponsor);
  assert.equal(w.hasPendingRequest, true);
  assert.equal(w.totalPayoutsToDate, 0); // nothing paid yet
  assert.equal(w.pendingCommissions, before); // still owed
});

test('a second request while one is pending is rejected', () => {
  const { db, sponsor } = setup();
  requestPayout(db, sponsor, {});
  assert.throws(() => requestPayout(db, sponsor, {}), /awaiting approval/);
});

test('coach approve then settle pays the affiliate', () => {
  const { db, sponsor } = setup();
  const amount = locked(db, sponsor);
  const { payoutId } = requestPayout(db, sponsor, {});

  assert.equal(approvePayout(db, payoutId).status, 'processing');
  assert.equal(getWallet(db, sponsor).totalPayoutsToDate, 0); // not paid until settled

  assert.equal(settlePayout(db, payoutId).status, 'paid');
  const w = getWallet(db, sponsor);
  assert.equal(w.totalPayoutsToDate, amount);
  assert.equal(w.pendingCommissions, 0);
  assert.equal(w.hasPendingRequest, false);
});

test('coach reject releases the reserved commissions', () => {
  const { db, sponsor } = setup();
  const amount = locked(db, sponsor);
  const { payoutId } = requestPayout(db, sponsor, {});
  assert.equal(locked(db, sponsor), 0);

  assert.equal(rejectPayout(db, payoutId).status, 'rejected');
  assert.equal(locked(db, sponsor), amount); // back to available
  assert.equal(getWallet(db, sponsor).hasPendingRequest, false);
  // Can request again after a rejection.
  assert.doesNotThrow(() => requestPayout(db, sponsor, {}));
});

test('cannot settle a payout that was never approved', () => {
  const { db, sponsor } = setup();
  const { payoutId } = requestPayout(db, sponsor, {});
  assert.throws(() => settlePayout(db, payoutId), /Cannot settle/);
});
