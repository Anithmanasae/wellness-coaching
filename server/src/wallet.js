// Wallet / Payouts read-model and the payout lifecycle actions.

const { nextRank, nextPayoutDate, conversionCount } = require('./engine');

function prestigeLabel(rankName) {
  return `${rankName} Ambassador`;
}

async function getWallet(db, userId, now = new Date()) {
  const user = await db.get('SELECT * FROM users WHERE id = ?', [userId]);
  if (!user) return null;

  const totalPayoutsToDate = (await db.get(
    `SELECT COALESCE(SUM(amount), 0) AS t FROM payouts WHERE user_id = ? AND status = 'paid'`,
    [userId]
  )).t;

  // Owed but not yet settled — available (locked) or reserved (requested).
  const pendingCommissions = (await db.get(
    `SELECT COALESCE(SUM(amount), 0) AS t FROM commissions WHERE user_id = ? AND status != 'paid'`,
    [userId]
  )).t;

  const hasPendingRequest = !!(await db.get(
    `SELECT 1 FROM payouts WHERE user_id = ? AND status = 'requested' LIMIT 1`,
    [userId]
  ));

  const sevenDaysAgo = new Date(now.getTime() - 7 * 864e5).toISOString().slice(0, 19).replace('T', ' ');
  const verifyingCount = Number((await db.get(
    `SELECT COUNT(DISTINCT source_purchase_id) AS n FROM commissions
     WHERE user_id = ? AND status = 'locked' AND created_at >= ?`,
    [userId, sevenDaysAgo]
  )).n);

  const conversions = await conversionCount(db, userId);
  const next = await nextRank(db, user.rank);
  const currentRank = await db.get('SELECT * FROM ranks WHERE name = ?', [user.rank]);
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

  const txRows = await db.all(
    'SELECT * FROM payouts WHERE user_id = ? ORDER BY created_at DESC, id DESC LIMIT 20',
    [userId]
  );
  const transactions = txRows.map((p) => ({
    id: p.id,
    reference: p.reference_no,
    date: String(p.created_at).slice(0, 10),
    method: p.method,
    amount: p.amount,
    status: p.status,
  }));

  return {
    totalPayoutsToDate,
    prestige,
    pendingCommissions,
    hasPendingRequest,
    nextSettlement: (await nextPayoutDate(db, now)).toISOString().slice(0, 10),
    verifyingCount,
    transactions,
  };
}

// Affiliate action: request a payout of the current available (locked) balance.
// Reserves those commissions ('requested'); nothing is paid until the coach
// approves. Only one open request per affiliate at a time.
async function requestPayout(db, userId, { method = 'Bank Transfer' } = {}) {
  return db.tx(async (t) => {
    const open = await t.get(`SELECT id FROM payouts WHERE user_id = ? AND status = 'requested' LIMIT 1`, [userId]);
    if (open) throw new Error('You already have a payout request awaiting approval');

    const locked = (await t.get(`SELECT COALESCE(SUM(amount), 0) AS t FROM commissions WHERE user_id = ? AND status = 'locked'`, [userId])).t;
    if (locked <= 0) throw new Error('No commissions available to request');

    const reference = `PO-${Date.now().toString().slice(-6)}`;
    const row = await t.get(`INSERT INTO payouts (user_id, reference_no, amount, method, status) VALUES (?, ?, ?, ?, 'requested') RETURNING id`, [userId, reference, locked, method]);
    await t.run(`UPDATE commissions SET status = 'requested', payout_id = ? WHERE user_id = ? AND status = 'locked'`, [row.id, userId]);
    return { payoutId: row.id, reference, amount: locked, status: 'requested' };
  });
}

async function getPayout(db, payoutId) {
  return db.get('SELECT * FROM payouts WHERE id = ?', [payoutId]);
}

// Coach: approve a requested payout — moves it into disbursement.
async function approvePayout(db, payoutId) {
  return db.tx(async (t) => {
    const p = await getPayout(t, payoutId);
    if (!p) throw new Error('Unknown payout');
    if (p.status !== 'requested') throw new Error(`Cannot approve a payout that is '${p.status}'`);
    await t.run(`UPDATE payouts SET status = 'processing' WHERE id = ?`, [payoutId]);
    return { payoutId, status: 'processing' };
  });
}

// Coach: mark an approved (processing) payout as paid — settles the reserved commissions.
async function settlePayout(db, payoutId) {
  return db.tx(async (t) => {
    const p = await getPayout(t, payoutId);
    if (!p) throw new Error('Unknown payout');
    if (p.status !== 'processing') throw new Error(`Cannot settle a payout that is '${p.status}'`);
    await t.run(`UPDATE payouts SET status = 'paid' WHERE id = ?`, [payoutId]);
    await t.run(`UPDATE commissions SET status = 'paid' WHERE payout_id = ?`, [payoutId]);
    return { payoutId, status: 'paid' };
  });
}

// Coach: reject a requested payout — releases the reserved commissions.
async function rejectPayout(db, payoutId) {
  return db.tx(async (t) => {
    const p = await getPayout(t, payoutId);
    if (!p) throw new Error('Unknown payout');
    if (p.status !== 'requested') throw new Error(`Cannot reject a payout that is '${p.status}'`);
    await t.run(`UPDATE payouts SET status = 'rejected' WHERE id = ?`, [payoutId]);
    await t.run(`UPDATE commissions SET status = 'locked', payout_id = NULL WHERE payout_id = ?`, [payoutId]);
    return { payoutId, status: 'rejected' };
  });
}

module.exports = { getWallet, requestPayout, approvePayout, settlePayout, rejectPayout };
