// Coach-side read-models: network dashboard overview and the affiliate directory.

const { nextPayoutDate } = require('./engine');

// Dashboard overview for the coach home screen.
async function getOverview(db, coachId, now = new Date()) {
  const coach = await db.get('SELECT * FROM users WHERE id = ?', [coachId]);

  // Total gross sales flowing through the network (sum of all purchase values).
  const totalNetworkSales = Number((await db.get('SELECT COALESCE(SUM(amount), 0) AS t FROM purchases')).t);

  const activeAffiliates = Number((await db.get(`SELECT COUNT(*) AS n FROM users WHERE role = 'affiliate'`)).n);

  const pending = await db.get(`SELECT COALESCE(SUM(amount),0) AS total, COUNT(*) AS n FROM payouts WHERE status = 'requested'`);
  const pendingPayoutsTotal = Number(pending.total);
  const pendingPayoutsCount = Number(pending.n);

  // Days until the next scheduled settlement.
  const settlement = await nextPayoutDate(db, now);
  const payoutDueInDays = Math.max(0, Math.ceil((settlement - now) / 864e5));

  const topRows = await db.all(
    `SELECT u.id, u.name, u.rank AS tier, COALESCE(SUM(c.amount), 0) AS earnings
     FROM users u
     JOIN commissions c ON c.user_id = u.id
     WHERE u.role = 'affiliate'
     GROUP BY u.id, u.name, u.rank
     ORDER BY earnings DESC
     LIMIT 5`
  );
  const topAffiliates = topRows.map((r) => ({ id: r.id, name: r.name, tier: r.tier, earnings: Number(r.earnings) }));

  return {
    coachName: coach ? coach.name : 'Coach',
    totalNetworkSales,
    activeAffiliates,
    pendingPayoutsTotal,
    pendingPayoutsCount,
    payoutDueInDays,
    topAffiliates,
  };
}

// Affiliate directory with optional text search and tier filter.
async function listAffiliates(db, { search = '', tier = '' } = {}) {
  const rows = await db.all(
    `SELECT u.id, u.name, u.rank AS tier, u.title, u.location,
            COALESCE(SUM(c.amount), 0) AS total_sales
     FROM users u
     LEFT JOIN commissions c ON c.user_id = u.id
     WHERE u.role = 'affiliate'
     GROUP BY u.id, u.name, u.rank, u.title, u.location
     ORDER BY total_sales DESC`
  );

  const q = search.trim().toLowerCase();
  const t = tier.trim().toLowerCase();
  return rows
    .map((r) => ({
      id: r.id,
      name: r.name,
      tier: r.tier,
      title: r.title,
      location: r.location,
      totalSales: Number(r.total_sales),
    }))
    .filter((a) => (!q || a.name.toLowerCase().includes(q) || (a.title || '').toLowerCase().includes(q) || (a.location || '').toLowerCase().includes(q)))
    .filter((a) => (!t || t === 'all' || a.tier.toLowerCase() === t));
}

// Pending payout requests with the affiliate's name, for the approvals screen.
async function pendingPayouts(db) {
  const rows = await db.all(
    `SELECT p.id, p.reference_no, p.amount, p.method, p.status, p.created_at,
            u.id AS affiliate_id, u.name AS affiliate_name, u.rank AS tier
     FROM payouts p JOIN users u ON u.id = p.user_id
     WHERE p.status IN ('requested','processing')
     ORDER BY (p.status = 'requested') DESC, p.created_at ASC`
  );
  return rows.map((p) => ({
    id: p.id,
    reference: p.reference_no,
    amount: Number(p.amount),
    method: p.method,
    status: p.status,
    date: String(p.created_at).slice(0, 10),
    affiliate: { id: p.affiliate_id, name: p.affiliate_name, tier: p.tier },
  }));
}

module.exports = { getOverview, listAffiliates, pendingPayouts };
