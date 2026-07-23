// Leaderboard read-model: ranks every advocate by lifetime commission
// earnings and locates the requesting user within the standings.

function getLeaderboard(db, meId = null, { rowLimit = 12 } = {}) {
  const standings = db
    .prepare(
      `SELECT u.id, u.name, u.rank AS tier,
              COALESCE(SUM(c.amount), 0) AS earnings
       FROM users u
       LEFT JOIN commissions c ON c.user_id = u.id
       GROUP BY u.id
       HAVING earnings > 0
       ORDER BY earnings DESC, u.id ASC`
    )
    .all();

  const total = standings.length;
  const ranked = standings.map((row, i) => ({
    rank: i + 1,
    id: row.id,
    name: row.name,
    tier: row.tier,
    earnings: row.earnings,
  }));

  const podium = ranked.slice(0, 3);
  const rows = ranked.slice(3, rowLimit);

  let me = null;
  if (meId != null) {
    const mine = ranked.find((r) => r.id === Number(meId));
    if (mine) {
      me = {
        id: mine.id,
        rank: mine.rank,
        tier: mine.tier,
        earnings: mine.earnings,
        // "top X%" — smaller is better; rank 1 of 20 => top 5%.
        percentile: Math.max(1, Math.ceil((mine.rank / total) * 100)),
      };
    }
  }

  return { total, podium, rows, me };
}

module.exports = { getLeaderboard };
