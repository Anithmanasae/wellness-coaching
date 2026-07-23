// Leaderboard read-model: ranks every advocate by lifetime commission
// earnings and locates the requesting user within the standings.

async function getLeaderboard(db, meId = null, { rowLimit = 12 } = {}) {
  const standings = await db.all(
    `SELECT u.id, u.name, u.rank AS tier,
            COALESCE(SUM(c.amount), 0) AS earnings
     FROM users u
     LEFT JOIN commissions c ON c.user_id = u.id
     GROUP BY u.id, u.name, u.rank
     HAVING COALESCE(SUM(c.amount), 0) > 0
     ORDER BY earnings DESC, u.id ASC`
  );

  const total = standings.length;
  const ranked = standings.map((row, i) => ({
    rank: i + 1,
    id: row.id,
    name: row.name,
    tier: row.tier,
    earnings: Number(row.earnings),
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
        percentile: Math.max(1, Math.ceil((mine.rank / total) * 100)),
      };
    }
  }

  return { total, podium, rows, me };
}

module.exports = { getLeaderboard };
