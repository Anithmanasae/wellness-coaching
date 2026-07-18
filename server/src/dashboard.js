const { nextRank, nextPayoutDate } = require('./engine');

// Human labels for the "Recent Conversions" list on the home screen.
function conversionLabel(row) {
  if (row.sale_note) return row.sale_note;
  switch (row.type) {
    case 'personal_sale':
      return row.product_name;
    case 'downline_l1':
    case 'downline_l2':
      return `${row.product_name} Referral`;
    case 'geo_sale_area':
    case 'geo_sale_taluk':
    case 'geo_sale_district':
      return `${row.product_name} (territory)`;
    case 'join_bonus_area':
    case 'join_bonus_taluk':
    case 'join_bonus_district':
      return 'New Affiliate Bonus';
    default:
      return row.type;
  }
}

// Everything the home screen needs, in one payload.
function getDashboard(db, userId, now = new Date()) {
  const user = db.prepare('SELECT * FROM users WHERE id = ?').get(userId);
  if (!user) return null;

  const monthStart = new Date(now.getFullYear(), now.getMonth(), 1).toISOString().slice(0, 10);

  const totalEarnedThisMonth = db
    .prepare(
      `SELECT COALESCE(SUM(amount), 0) AS total FROM commissions
       WHERE user_id = ? AND created_at >= ?`
    )
    .get(userId, monthStart).total;

  const lockedAmount = db
    .prepare(`SELECT COALESCE(SUM(amount), 0) AS total FROM commissions WHERE user_id = ? AND status = 'locked'`)
    .get(userId).total;

  const linkClicks = db
    .prepare('SELECT COUNT(*) AS n FROM link_clicks WHERE user_id = ?')
    .get(userId).n;

  const personalSales = db
    .prepare('SELECT COUNT(*) AS n FROM sales WHERE seller_id = ?')
    .get(userId).n;

  const next = nextRank(db, user.rank);
  const currentRank = db.prepare('SELECT * FROM ranks WHERE name = ?').get(user.rank);
  let rankProgress = null;
  if (next && currentRank) {
    const span = next.min_personal_sales - currentRank.min_personal_sales;
    const done = personalSales - currentRank.min_personal_sales;
    rankProgress = {
      currentRank: user.rank,
      nextRank: next.name,
      salesToNext: Math.max(0, next.min_personal_sales - personalSales),
      percent: Math.max(0, Math.min(100, Math.round((done / span) * 100))),
    };
  }

  const recentConversions = db
    .prepare(
      `SELECT c.id, c.type, c.amount, c.created_at,
              s.customer_name, s.note AS sale_note, p.name AS product_name
       FROM commissions c
       LEFT JOIN sales s ON s.id = c.source_sale_id
       LEFT JOIN products p ON p.id = s.product_id
       LEFT JOIN users nu ON nu.id = c.source_user_id
       WHERE c.user_id = ?
         AND c.type IN ('personal_sale','downline_l1','downline_l2')
       ORDER BY c.created_at DESC, c.id DESC
       LIMIT 5`
    )
    .all(userId)
    .map((row) => ({
      id: row.id,
      name: row.customer_name || 'Customer',
      label: conversionLabel(row),
      amount: row.amount,
    }));

  const payoutDate = nextPayoutDate(db, now);

  return {
    user: { id: user.id, name: user.name, rank: user.rank },
    totalEarnedThisMonth,
    linkClicks,
    conversions: personalSales,
    nextPayout: {
      amount: lockedAmount,
      estimatedDate: payoutDate.toISOString().slice(0, 10),
    },
    rankProgress,
    recentConversions,
  };
}

module.exports = { getDashboard };
