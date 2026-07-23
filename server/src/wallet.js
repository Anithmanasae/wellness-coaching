// Wallet / Payouts read-model and the payout-request action.

const { nextRank, nextPayoutDate, conversionCount } = require('./engine');

// Prestige label shown on the wallet screen, derived from the advocate's rank.
function prestigeLabel(rankName) {
  return `${rankName} Ambassador`;
}

function getWallet(db, userId, now = new Date()) {
  const user = db.prepare('SELECT * FROM users WHERE id = ?').get(userId);
  if (!user) return null;

  const totalPayoutsToDate = db
    .prepare(`SELECT COALESCE(SUM(amount), 0) AS t FROM payouts WHERE user_id = ? AND status = 'paid'`)
    .get(userId).t;

  // Everything the affiliate is owed but hasn't been settled yet — whether it
  // is still available (locked) or reserved in a payout awaiting coach approval
  // (requested).
  const pendingCommissions = db
    .prepare(`SELECT COALESCE(SUM(amount), 0) AS t FROM commissions WHERE user_id = ? AND status != 'paid'`)
    .get(userId).t;

  // Is there already a payout request waiting on the coach?
  const hasPendingRequest = !!db
    .prepare(`SELECT 1 FROM payouts WHERE user_id = ? AND status = 'requested' LIMIT 1`)
    .get(userId);

  // Sales still inside the verification window (recent locked commissions).
  const verifyingCount = db
    .prepare(
      `SELECT COUNT(DISTINCT source_purchase_id) AS n FROM commissions
       WHERE user_id = ? AND status = 'locked' AND created_at >= ?`
    )
    .get(userId, new Date(now.getTime() - 7 * 864e5).toISOString().slice(0, 19).replace('T', ' ')).n;

  // Prestige progress mirrors the home-screen rank ladder (by conversions).
  const conversions = conversionCount(db, userId);
  const next = nextRank(db, user.rank);
  const currentRank = db.prepare('SELECT * FROM ranks WHERE name = ?').get(user.rank);
  let prestige = { level: prestigeLabel(user.rank), nextLevel: null, percent: 100 };
  if (next && currentRank) {
    const span = next.min_conversions - currentRank.min_conversions;
    const done = conversions - currentRank.min_conversions;
    prestige = {
      level: prestigeLabel(user.rank),
      nextLevel: next.name,
      percent: Math.max(0, Math.min(100, Math.round((done / span) * 100))),
    };
  }

  const transactions = db
    .prepare('SELECT * FROM payouts WHERE user_id = ? ORDER BY created_at DESC, id DESC LIMIT 20')
    .all(userId)
    .map((p) => ({
      id: p.id,
      reference: p.reference_no,
      date: p.created_at.slice(0, 10),
      method: p.method,
      amount: p.amount,
      status: p.status,
    }));

  return {
    totalPayoutsToDate,
    prestige,
    pendingCommissions,
    hasPendingRequest,
    nextSettlement: nextPayoutDate(db, now).toISOString().slice(0, 10),
    verifyingCount,
    transactions,
  };
}

// Affiliate action: request a payout of the current available (locked) balance.
// Creates a 'requested' payout and reserves those commissions ('requested').
// Nothing is paid until the coach approves. Idempotent-guarded: only one open
// request at a time.
function requestPayout(db, userId, { method = 'Bank Transfer' } = {}) {
  const tx = db.transaction(() => {
    const open = db
      .prepare(`SELECT id FROM payouts WHERE user_id = ? AND status = 'requested' LIMIT 1`)
      .get(userId);
    if (open) throw new Error('You already have a payout request awaiting approval');

    const locked = db
      .prepare(`SELECT COALESCE(SUM(amount), 0) AS t FROM commissions WHERE user_id = ? AND status = 'locked'`)
      .get(userId).t;
    if (locked <= 0) throw new Error('No commissions available to request');

    const reference = `PO-${Date.now().toString().slice(-6)}`;
    const info = db
      .prepare(`INSERT INTO payouts (user_id, reference_no, amount, method, status) VALUES (?, ?, ?, ?, 'requested')`)
      .run(userId, reference, locked, method);
    const payoutId = info.lastInsertRowid;
    db.prepare(`UPDATE commissions SET status = 'requested', payout_id = ? WHERE user_id = ? AND status = 'locked'`)
      .run(payoutId, userId);
    return { payoutId, reference, amount: locked, status: 'requested' };
  });
  return tx();
}

function getPayout(db, payoutId) {
  return db.prepare('SELECT * FROM payouts WHERE id = ?').get(payoutId);
}

// Coach action: approve a requested payout — moves it into disbursement.
// Commissions stay reserved ('requested') until the payout is marked paid.
function approvePayout(db, payoutId) {
  const tx = db.transaction(() => {
    const p = getPayout(db, payoutId);
    if (!p) throw new Error('Unknown payout');
    if (p.status !== 'requested') throw new Error(`Cannot approve a payout that is '${p.status}'`);
    db.prepare(`UPDATE payouts SET status = 'processing' WHERE id = ?`).run(payoutId);
    return { payoutId, status: 'processing' };
  });
  return tx();
}

// Coach action: mark an approved (processing) payout as paid — settles the
// reserved commissions.
function settlePayout(db, payoutId) {
  const tx = db.transaction(() => {
    const p = getPayout(db, payoutId);
    if (!p) throw new Error('Unknown payout');
    if (p.status !== 'processing') throw new Error(`Cannot settle a payout that is '${p.status}'`);
    db.prepare(`UPDATE payouts SET status = 'paid' WHERE id = ?`).run(payoutId);
    db.prepare(`UPDATE commissions SET status = 'paid' WHERE payout_id = ?`).run(payoutId);
    return { payoutId, status: 'paid' };
  });
  return tx();
}

// Coach action: reject a requested payout — releases the reserved commissions
// back to 'locked' so the affiliate can request again.
function rejectPayout(db, payoutId) {
  const tx = db.transaction(() => {
    const p = getPayout(db, payoutId);
    if (!p) throw new Error('Unknown payout');
    if (p.status !== 'requested') throw new Error(`Cannot reject a payout that is '${p.status}'`);
    db.prepare(`UPDATE payouts SET status = 'rejected' WHERE id = ?`).run(payoutId);
    db.prepare(`UPDATE commissions SET status = 'locked', payout_id = NULL WHERE payout_id = ?`).run(payoutId);
    return { payoutId, status: 'rejected' };
  });
  return tx();
}

module.exports = { getWallet, requestPayout, approvePayout, settlePayout, rejectPayout };
