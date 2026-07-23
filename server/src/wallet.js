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

  const pendingCommissions = db
    .prepare(`SELECT COALESCE(SUM(amount), 0) AS t FROM commissions WHERE user_id = ? AND status = 'locked'`)
    .get(userId).t;

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
    nextSettlement: nextPayoutDate(db, now).toISOString().slice(0, 10),
    verifyingCount,
    transactions,
  };
}

// Request a payout of the current locked balance. Marks those commissions
// 'paid' and creates a 'processing' payout row atomically.
function requestPayout(db, userId, { method = 'Bank Transfer' } = {}) {
  const tx = db.transaction(() => {
    const locked = db
      .prepare(`SELECT COALESCE(SUM(amount), 0) AS t FROM commissions WHERE user_id = ? AND status = 'locked'`)
      .get(userId).t;
    if (locked <= 0) throw new Error('No locked commissions available to pay out');

    const reference = `PO-${Date.now().toString().slice(-6)}`;
    const info = db
      .prepare(`INSERT INTO payouts (user_id, reference_no, amount, method, status) VALUES (?, ?, ?, ?, 'processing')`)
      .run(userId, reference, locked, method);
    db.prepare(`UPDATE commissions SET status = 'paid' WHERE user_id = ? AND status = 'locked'`).run(userId);
    return { payoutId: info.lastInsertRowid, reference, amount: locked };
  });
  return tx();
}

module.exports = { getWallet, requestPayout };
