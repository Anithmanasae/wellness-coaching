// Demo seed for the coach's team, built through the real engine so the
// affiliate app's four screens (Home, Links, Wallet, Leaderboard) are all
// populated from genuine data. Runs on either driver (DB_DRIVER=sqlite|pg).
const fs = require('fs');
const { openDb, DB_PATH } = require('./db');
const { registerAffiliate, recordPurchase } = require('./engine');
const { requestPayout } = require('./wallet');
const { hashPassword } = require('./auth');
const { getDashboard } = require('./dashboard');
const { getLinks } = require('./links');
const { getWallet } = require('./wallet');
const { getLeaderboard } = require('./leaderboard');

const now = new Date();
function isoDay(offsetDays, time = '11:00:00') {
  const d = new Date(now.getTime() - offsetDays * 864e5);
  return `${d.toISOString().slice(0, 10)} ${time}`;
}

async function main() {
  const driver = process.env.DB_DRIVER || 'sqlite';
  if (driver === 'sqlite') {
    for (const suffix of ['', '-shm', '-wal']) {
      if (fs.existsSync(DB_PATH + suffix)) fs.unlinkSync(DB_PATH + suffix);
    }
  }
  // pg: drop + recreate for a fresh, current schema (SQLite starts fresh via
  // the file delete above). Ids stay deterministic (Jessica = 3).
  const db = await openDb({ reset: driver === 'pg' });

  const setTierMax = (id) => db.run('UPDATE users SET highest_tier_rank = 99 WHERE id = ?', [id]);

  // --- Geography -------------------------------------------------------------
  const pincodes = [
    ['560001', 'Shivajinagar', 'Bangalore North', 'Bengaluru Urban'],
    ['560003', 'Malleswaram', 'Bangalore North', 'Bengaluru Urban'],
    ['560004', 'Basavanagudi', 'Bangalore South', 'Bengaluru Urban'],
    ['560043', 'Banaswadi', 'Bangalore East', 'Bengaluru Urban'],
    ['560064', 'Yelahanka New Town', 'Yelahanka', 'Bengaluru Urban'],
    ['562106', 'Anekal', 'Anekal', 'Bengaluru Urban'],
    ['561203', 'Doddaballapura', 'Doddaballapura', 'Bengaluru Rural'],
    ['562157', 'Nelamangala', 'Nelamangala', 'Bengaluru Rural'],
    ['561101', 'Devanahalli', 'Devanahalli', 'Bengaluru Rural'],
    ['562149', 'Hoskote', 'Hoskote', 'Bengaluru Rural'],
    ['562123', 'Ramanagara', 'Ramanagara', 'Bengaluru Rural'],
  ];
  for (const p of pincodes) {
    await db.run('INSERT INTO pincodes (pincode, area_name, taluk, district) VALUES (?, ?, ?, ?)', p);
  }

  // --- Territory holders -----------------------------------------------------
  const deepa = (await registerAffiliate(db, { name: 'Deepa S.', pincode: '560003', joinedAt: isoDay(120, '08:00:00') })).userId;
  const suresh = (await registerAffiliate(db, { name: 'Suresh K.', pincode: '560004', joinedAt: isoDay(120, '08:05:00') })).userId;
  await setTierMax(deepa);
  await recordPurchase(db, { buyerId: deepa, productCode: 'P5', createdAt: isoDay(119) });
  await db.run("INSERT INTO territory_holders (level, territory, user_id) VALUES ('district', 'Bengaluru Urban', ?) ON CONFLICT DO NOTHING", [suresh]);

  // --- Jessica ---------------------------------------------------------------
  const jessica = (await registerAffiliate(db, { name: 'Jessica', email: 'jessica@example.com', pincode: '560001', sponsorId: deepa, joinedAt: isoDay(60, '09:00:00') })).userId;
  await setTierMax(jessica);
  await recordPurchase(db, { buyerId: jessica, productCode: 'P3', createdAt: isoDay(59) });
  await db.run('UPDATE users SET title = ?, location = ?, password_hash = ? WHERE id = ?', ['Wellness Advocate', 'Bengaluru', hashPassword('jessica123'), jessica]);

  const linkA = (await db.get("INSERT INTO campaign_links (user_id, slug, title, tag, created_at) VALUES (?, 'holistic-reset', 'Holistic Reset Package', 'Health Reset', ?) RETURNING id", [jessica, isoDay(45, '09:00:00')])).id;
  const linkB = (await db.get("INSERT INTO campaign_links (user_id, slug, title, tag, created_at) VALUES (?, 'elite-performance', 'Elite Performance Protocol', 'High Performance', ?) RETURNING id", [jessica, isoDay(12, '09:00:00')])).id;

  const recruitPlan = [
    ['Ananya R.', '560001', linkA, 40], ['Marcus K.', '560001', linkA, 38],
    ['Kavya T.', '560001', linkA, 36], ['Nikhil B.', '560001', linkA, 34],
    ['Sara J.', '560003', linkA, 32], ['Vivek P.', '560001', linkA, 20],
    ['Meera L.', '560001', linkA, 14], ['Aditya R.', '560043', linkA, 10],
    ['Farah H.', '560001', linkA, 6], ['Dinesh C.', '560001', linkB, 9],
    ['Lakshmi V.', '560001', linkB, 7], ['Tanya G.', '560064', linkB, 5],
  ];
  const recruitId = {};
  for (const [name, pin, link, ago] of recruitPlan) {
    recruitId[name] = (await registerAffiliate(db, { name, pincode: pin, sponsorId: jessica, campaignLinkId: link, joinedAt: isoDay(ago, '10:00:00') })).userId;
  }

  const rohan = (await registerAffiliate(db, { name: 'Rohan V.', pincode: '560043', sponsorId: recruitId['Ananya R.'], joinedAt: isoDay(15, '12:00:00') })).userId;
  await recordPurchase(db, { buyerId: rohan, productCode: 'P1', createdAt: isoDay(15, '13:00:00') });
  await recordPurchase(db, { buyerId: recruitId['Ananya R.'], productCode: 'P4', campaignLinkId: linkB, createdAt: isoDay(4, '15:00:00') });
  await recordPurchase(db, { buyerId: recruitId['Marcus K.'], productCode: 'P2', campaignLinkId: linkB, createdAt: isoDay(3, '15:00:00') });

  // Campaign-link clicks (214 on A -> ~4.2%, 74 on B -> ~6.8%).
  await db.tx(async (t) => {
    for (let i = 0; i < 214; i++) await t.run('INSERT INTO link_clicks (user_id, campaign_link_id, clicked_at) VALUES (?, ?, ?)', [jessica, linkA, isoDay(45 - (i % 45), '12:00:00')]);
    for (let i = 0; i < 74; i++) await t.run('INSERT INTO link_clicks (user_id, campaign_link_id, clicked_at) VALUES (?, ?, ?)', [jessica, linkB, isoDay(12 - (i % 12), '12:00:00')]);
  });

  // Wallet history: settle last month's earnings, leave this month pending.
  const thisMonthStart = new Date(now.getFullYear(), now.getMonth(), 1).toISOString().slice(0, 10);
  const lastMonthEarned = (await db.get('SELECT COALESCE(SUM(amount),0) AS t FROM commissions WHERE user_id = ? AND created_at < ?', [jessica, thisMonthStart])).t;
  if (lastMonthEarned > 0) {
    await db.run("INSERT INTO payouts (user_id, reference_no, amount, method, status, created_at) VALUES (?, 'PO-7412', ?, 'Bank Transfer', 'paid', ?)", [jessica, lastMonthEarned, isoDay(40, '10:00:00')]);
    await db.run("UPDATE commissions SET status = 'paid' WHERE user_id = ? AND created_at < ?", [jessica, thisMonthStart]);
  }
  await db.run("INSERT INTO payouts (user_id, reference_no, amount, method, status, created_at) VALUES (?, 'PO-7201', 24500, 'Bank Transfer', 'paid', ?)", [jessica, isoDay(72, '10:00:00')]);
  await db.run("INSERT INTO payouts (user_id, reference_no, amount, method, status, created_at) VALUES (?, 'PO-7698', 8600, 'UPI', 'processing', ?)", [jessica, isoDay(1, '10:00:00')]);

  // --- Leaderboard field -----------------------------------------------------
  const NAME_POOL = [
    'Aarav Nair', 'Isha Reddy', 'Kabir Shah', 'Ananya Iyer', 'Rohit Menon',
    'Sneha Pillai', 'Arjun Rao', 'Diya Kapoor', 'Vikram Bose', 'Neha Gupta',
    'Karan Malhotra', 'Priya Varma', 'Aditya Singh', 'Riya Desai', 'Sameer Khan',
    'Tara Joshi', 'Nikhil Chauhan', 'Meera Krishnan', 'Rahul Verma', 'Pooja Hegde',
    'Daniel Foster', 'Grace Lim', 'Omar Haddad', 'Sofia Reyes', 'Ethan Clarke',
    'Lena Novak', 'Marco Bianchi', 'Chloe Adams', 'Ibrahim Sy', 'Hana Kim',
    'Lucas Moreau', 'Amelia Ford', 'Yusuf Demir', 'Zara Ahmed', 'Noah Bennett',
    'Emma Walsh', 'Raj Patel', 'Fatima Noor', 'Leo Martins', 'Ava Sullivan',
    'Dev Sharma', 'Kiara Jain', 'Rehan Mirza', 'Anjali Nanda', 'Vivaan Kohli',
    'Maya Fernandes', 'Aryan Ghosh', 'Simran Kaur', 'Tanvi Rao', 'Krish Anand',
  ];
  let namePtr = 0;
  const nextName = () => NAME_POOL[namePtr++ % NAME_POOL.length];

  const RURAL = ['561203', '562157', '561101', '562149', '562123'];
  // name, recruits, packages, title, location, requestsPayout
  const leaders = [
    ['Marcus V.', 30, ['P5', 'P5', 'P4'], 'Executive Performance Coach', 'New York', false],
    ['Julianne R.', 18, ['P4', 'P4', 'P4'], 'Holistic Nutrition Expert', 'Madrid', true],
    ['Elena S.', 17, ['P5', 'P4'], 'Integrative Wellness Lead', 'London', false],
    ['Dr. Sarah Chen', 17, ['P4', 'P4'], 'Mindfulness Systems Specialist', 'Singapore', true],
    ['Oliver Bennett', 30, ['P4'], 'Peak Performance Mentor', 'Sydney', true],
    ['Amara Okafor', 17, ['P3', 'P3', 'P3'], 'Life Transformation Coach', 'Lagos', true],
    ['Rahul Mehta', 11, ['P3', 'P2'], 'Wellness Program Director', 'Bengaluru', true],
    ['Nadia Khan', 6, ['P2', 'P2'], 'Health & Habit Consultant', 'Dubai', true],
    ['Liam Wong', 5, ['P1', 'P6'], 'Fitness & Recovery Coach', 'Hong Kong', false],
  ];
  let leadAgo = 100;
  const requesters = [];
  for (let li = 0; li < leaders.length; li++) {
    const [name, recruits, pkgs, title, location, requests] = leaders[li];
    const pin = RURAL[li % RURAL.length];
    const leaderId = (await registerAffiliate(db, { name, pincode: pin, joinedAt: isoDay(leadAgo, '08:00:00') })).userId;
    await setTierMax(leaderId);
    await db.run('UPDATE users SET title = ?, location = ? WHERE id = ?', [title, location, leaderId]);
    for (let i = 0; i < recruits; i++) {
      const r = (await registerAffiliate(db, { name: nextName(), pincode: pin, sponsorId: leaderId, joinedAt: isoDay(leadAgo - 1, '09:00:00') })).userId;
      if (i < pkgs.length) await recordPurchase(db, { buyerId: r, productCode: pkgs[i], createdAt: isoDay(leadAgo - 2, '10:00:00') });
    }
    if (requests) requesters.push(leaderId);
    leadAgo -= 3;
  }

  // Several affiliates request payouts -> the coach's approval queue.
  for (const id of requesters) await requestPayout(db, id, {});

  // The wellness coach account (login: coach@epiclife.academy / coach123).
  // Created last so affiliate ids stay deterministic (Jessica = 3).
  await db.run("INSERT INTO users (name, email, role, password_hash) VALUES (?, ?, 'coach', ?)", ['Coach Varadarajan', 'coach@epiclife.academy', hashPassword('coach123')]);

  // --- Report ----------------------------------------------------------------
  console.log(`Seed complete (driver: ${driver}). Jessica id =`, jessica);
  const dash = await getDashboard(db, jessica);
  console.log('\nHOME  :', 'rank', dash.user.rank, '| this-month ₹' + dash.totalEarnedThisMonth, '| clicks', dash.linkClicks, '| conversions', dash.conversions, '|', dash.rankProgress ? dash.rankProgress.salesToNext + ' from ' + dash.rankProgress.nextRank : '');
  const links = await getLinks(db, jessica);
  console.log('LINKS :', links.campaigns.map((c) => `${c.title} ${c.clicks}clk ${c.conversionRate}% (${c.activeDays}d)`).join(' | '));
  const wallet = await getWallet(db, jessica);
  console.log('WALLET:', 'paid ₹' + wallet.totalPayoutsToDate, '| pending ₹' + wallet.pendingCommissions, '| prestige', wallet.prestige.level, '→', wallet.prestige.nextLevel, '| verifying', wallet.verifyingCount, '| txns', wallet.transactions.length);
  const lb = await getLeaderboard(db, jessica);
  console.log('BOARD :', 'total', lb.total, '| podium', lb.podium.map((p) => `${p.name}[${p.tier}] ₹${p.earnings}`).join(', '));
  console.log('        me: rank', lb.me.rank, '₹' + lb.me.earnings, 'top ' + lb.me.percentile + '%');

  if (db.close) await db.close();
}

main().catch((err) => { console.error(err); process.exit(1); });
