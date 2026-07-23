const { nextRank, nextPayoutDate, conversionCount } = require('./engine');

// Human label for a commission row on the "Recent Conversions" list.
function conversionLabel(row) {
  if (row.kind === 'level') {
    return row.level === 1 ? row.product_name : `${row.product_name} (L-${row.level})`;
  }
  const territory = { geo_area: 'PIN Code', geo_taluk: 'Taluk', geo_district: 'District' }[row.kind];
  return `${row.product_name} — ${territory} Override`;
}

// Everything the home screen needs, in one payload.
function getDashboard(db, userId, now = new Date()) {
  const user = db.prepare('SELECT * FROM users WHERE id = ?').get(userId);
  if (!user) return null;

  const monthStart = new Date(now.getFullYear(), now.getMonth(), 1).toISOString().slice(0, 10);

  const totalEarnedThisMonth = db
    .prepare('SELECT COALESCE(SUM(amount), 0) AS total FROM commissions WHERE user_id = ? AND created_at >= ?')
    .get(userId, monthStart).total;

  const lockedAmount = db
    .prepare(`SELECT COALESCE(SUM(amount), 0) AS total FROM commissions WHERE user_id = ? AND status = 'locked'`)
    .get(userId).total;

  const linkClicks = db.prepare('SELECT COUNT(*) AS n FROM link_clicks WHERE user_id = ?').get(userId).n;

  const conversions = conversionCount(db, userId);

  const next = nextRank(db, user.rank);
  const currentRank = db.prepare('SELECT * FROM ranks WHERE name = ?').get(user.rank);
  let rankProgress = null;
  if (next && currentRank) {
    const span = next.min_conversions - currentRank.min_conversions;
    const done = conversions - currentRank.min_conversions;
    rankProgress = {
      currentRank: user.rank,
      nextRank: next.name,
      salesToNext: Math.max(0, next.min_conversions - conversions),
      percent: Math.max(0, Math.min(100, Math.round((done / span) * 100))),
    };
  }

  const recentConversions = db
    .prepare(
      `SELECT c.id, c.kind, c.level, c.amount,
              b.name AS buyer_name, p.name AS product_name
       FROM commissions c
       LEFT JOIN users b ON b.id = c.source_user_id
       LEFT JOIN products p ON p.id = c.product_id
       WHERE c.user_id = ?
       ORDER BY c.created_at DESC, c.id DESC
       LIMIT 5`
    )
    .all(userId)
    .map((row) => ({
      id: row.id,
      name: row.buyer_name || 'Customer',
      label: conversionLabel(row),
      amount: row.amount,
    }));

  const payoutDate = nextPayoutDate(db, now);

  return {
    user: { id: user.id, name: user.name, rank: user.rank },
    totalEarnedThisMonth,
    linkClicks,
    conversions,
    nextPayout: { amount: lockedAmount, estimatedDate: payoutDate.toISOString().slice(0, 10) },
    rankProgress,
    recentConversions,
  };
}

module.exports = { getDashboard };
