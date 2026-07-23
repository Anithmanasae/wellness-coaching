// Demo seed for the coach's team, built through the real engine so the
// affiliate app's four screens (Home, Links, Wallet, Leaderboard) are all
// populated from genuine data.
const fs = require('fs');
const { createDb, DB_PATH } = require('./db');
const { registerAffiliate, recordPurchase } = require('./engine');
const { getDashboard } = require('./dashboard');
const { getLinks } = require('./links');
const { getWallet } = require('./wallet');
const { getLeaderboard } = require('./leaderboard');

for (const suffix of ['', '-shm', '-wal']) {
  if (fs.existsSync(DB_PATH + suffix)) fs.unlinkSync(DB_PATH + suffix);
}
const db = createDb();

const now = new Date();
function isoDay(offsetDays, time = '11:00:00') {
  const d = new Date(now.getTime() - offsetDays * 864e5);
  return `${d.toISOString().slice(0, 10)} ${time}`;
}

// --- Geography: Bengaluru Urban and its 5 taluks ---------------------------
const pincodes = [
  // Bengaluru Urban — Jessica's district, with territory holders.
  ['560001', 'Shivajinagar', 'Bangalore North', 'Bengaluru Urban'],
  ['560003', 'Malleswaram', 'Bangalore North', 'Bengaluru Urban'],
  ['560004', 'Basavanagudi', 'Bangalore South', 'Bengaluru Urban'],
  ['560043', 'Banaswadi', 'Bangalore East', 'Bengaluru Urban'],
  ['560064', 'Yelahanka New Town', 'Yelahanka', 'Bengaluru Urban'],
  ['562106', 'Anekal', 'Anekal', 'Bengaluru Urban'],
  // Bengaluru Rural — no territory holders, so leaderboard leaders here earn
  // purely from their own downline (no geo cross-pollution into Urban).
  ['561203', 'Doddaballapura', 'Doddaballapura', 'Bengaluru Rural'],
  ['562157', 'Nelamangala', 'Nelamangala', 'Bengaluru Rural'],
  ['561101', 'Devanahalli', 'Devanahalli', 'Bengaluru Rural'],
  ['562149', 'Hoskote', 'Hoskote', 'Bengaluru Rural'],
  ['562123', 'Ramanagara', 'Ramanagara', 'Bengaluru Rural'],
];
const insPin = db.prepare('INSERT INTO pincodes (pincode, area_name, taluk, district) VALUES (?, ?, ?, ?)');
for (const p of pincodes) insPin.run(...p);

const setTierMax = (id) => db.prepare('UPDATE users SET highest_tier_rank = 99 WHERE id = ?').run(id);

// --- Territory holders -------------------------------------------------------
const deepa = registerAffiliate(db, { name: 'Deepa S.', pincode: '560003', joinedAt: isoDay(120, '08:00:00') }).userId;
const suresh = registerAffiliate(db, { name: 'Suresh K.', pincode: '560004', joinedAt: isoDay(120, '08:05:00') }).userId;
setTierMax(deepa);
recordPurchase(db, { buyerId: deepa, productCode: 'P5', createdAt: isoDay(119) }); // Bangalore North taluk holder
db.prepare('INSERT OR IGNORE INTO territory_holders (level, territory, user_id) VALUES (?, ?, ?)')
  .run('district', 'Bengaluru Urban', suresh);

// --- Jessica: our logged-in advocate ----------------------------------------
const jessica = registerAffiliate(db, { name: 'Jessica', email: 'jessica@example.com', pincode: '560001', sponsorId: deepa, joinedAt: isoDay(60, '09:00:00') }).userId;
setTierMax(jessica);
recordPurchase(db, { buyerId: jessica, productCode: 'P3', createdAt: isoDay(59) }); // 560001 area holder

// Two campaign links (A active 45 days, B active 12 days).
const insLink = db.prepare('INSERT INTO campaign_links (user_id, slug, title, tag, created_at) VALUES (?, ?, ?, ?, ?)');
const linkA = insLink.run(jessica, 'holistic-reset', 'Holistic Reset Package', 'Health Reset', isoDay(45, '09:00:00')).lastInsertRowid;
const linkB = insLink.run(jessica, 'elite-performance', 'Elite Performance Protocol', 'High Performance', isoDay(12, '09:00:00')).lastInsertRowid;

// Jessica's 12 direct recruits. 9 came via link A, 3 via link B.
// Half joined last month (already paid out), half this month (pending).
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
  recruitId[name] = registerAffiliate(db, { name, pincode: pin, sponsorId: jessica, campaignLinkId: link, joinedAt: isoDay(ago, '10:00:00') }).userId;
}

// Two high-value upgrades (attributed to link B) — these keep her direct-recruit
// purchase count at 14 (Gold, 3 from Platinum) while driving real earnings.
recordPurchase(db, { buyerId: recruitId['Ananya R.'], productCode: 'P4', campaignLinkId: linkB, createdAt: isoDay(4, '15:00:00') }); // +₹35,000
recordPurchase(db, { buyerId: recruitId['Marcus K.'], productCode: 'P2', campaignLinkId: linkB, createdAt: isoDay(3, '15:00:00') }); // +₹3,000

// Second generation (L-2 for Jessica; does not count as her conversion).
const rohan = registerAffiliate(db, { name: 'Rohan V.', pincode: '560043', sponsorId: recruitId['Ananya R.'], joinedAt: isoDay(8, '12:00:00') }).userId;
recordPurchase(db, { buyerId: rohan, productCode: 'P1', createdAt: isoDay(2, '12:00:00') }); // Jessica L-2 +₹350

// Campaign-link clicks: 214 on A (→ ~4.2%), 74 on B (→ ~6.8%).
const insClick = db.prepare('INSERT INTO link_clicks (user_id, campaign_link_id, clicked_at) VALUES (?, ?, ?)');
const clickTx = db.transaction(() => {
  for (let i = 0; i < 214; i++) insClick.run(jessica, linkA, isoDay(45 - (i % 45), '12:00:00'));
  for (let i = 0; i < 74; i++) insClick.run(jessica, linkB, isoDay(12 - (i % 12), '12:00:00'));
});
clickTx();

// Wallet history: settle last month's earnings, leave this month pending.
const lastMonthStart = new Date(now.getFullYear(), now.getMonth() - 1, 1).toISOString().slice(0, 10);
const thisMonthStart = new Date(now.getFullYear(), now.getMonth(), 1).toISOString().slice(0, 10);
const lastMonthEarned = db
  .prepare(`SELECT COALESCE(SUM(amount),0) AS t FROM commissions WHERE user_id = ? AND created_at < ?`)
  .get(jessica, thisMonthStart).t;
if (lastMonthEarned > 0) {
  db.prepare(`INSERT INTO payouts (user_id, reference_no, amount, method, status, created_at) VALUES (?, ?, ?, 'Bank Transfer', 'paid', ?)`)
    .run(jessica, 'PO-7412', lastMonthEarned, isoDay(40, '10:00:00'));
  db.prepare(`UPDATE commissions SET status = 'paid' WHERE user_id = ? AND created_at < ?`).run(jessica, thisMonthStart);
}
// An earlier settlement and an in-flight one, for a fuller history.
db.prepare(`INSERT INTO payouts (user_id, reference_no, amount, method, status, created_at) VALUES (?, 'PO-7201', 24500, 'Bank Transfer', 'paid', ?)`)
  .run(jessica, isoDay(72, '10:00:00'));
db.prepare(`INSERT INTO payouts (user_id, reference_no, amount, method, status, created_at) VALUES (?, 'PO-7698', 8600, 'UPI', 'processing', ?)`)
  .run(jessica, isoDay(1, '10:00:00'));

// --- Leaderboard: a field of Elite Advocates with real downline earnings -----
// Each leader has a team of `recruits` registrations (which set their rank
// tier by conversion count) and a few high-value package buyers (which drive
// earnings). Tier and earnings vary independently — mirroring how a Diamond
// advocate can out-rank a Platinum on tier yet earn less (e.g. Oliver below
// Dr. Sarah in the design).
const RURAL = ['561203', '562157', '561101', '562149', '562123'];
const leaders = [
  // name, recruits, packages the first buyers purchase
  ['Marcus V.', 30, ['P5', 'P5', 'P4']],
  ['Julianne R.', 18, ['P4', 'P4', 'P4']],
  ['Elena S.', 17, ['P5', 'P4']],
  ['Dr. Sarah Chen', 17, ['P4', 'P4']],
  ['Oliver Bennett', 30, ['P4']],
  ['Amara Okafor', 17, ['P3', 'P3', 'P3']],
  ['Rahul Mehta', 11, ['P3', 'P2']],
  ['Nadia Khan', 6, ['P2', 'P2']],
  ['Liam Wong', 5, ['P1', 'P6']],
];
// Real names for team members so anyone who surfaces on the leaderboard
// (e.g. a team member who bought a territory package and earns geo overrides)
// reads as a genuine advocate.
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

let leadAgo = 100;
leaders.forEach(([name, recruits, pkgs], li) => {
  const pin = RURAL[li % RURAL.length];
  const leaderId = registerAffiliate(db, { name, pincode: pin, joinedAt: isoDay(leadAgo, '08:00:00') }).userId;
  setTierMax(leaderId);
  for (let i = 0; i < recruits; i++) {
    const r = registerAffiliate(db, { name: nextName(), pincode: pin, sponsorId: leaderId, joinedAt: isoDay(leadAgo - 1, '09:00:00') }).userId;
    if (i < pkgs.length) recordPurchase(db, { buyerId: r, productCode: pkgs[i], createdAt: isoDay(leadAgo - 2, '10:00:00') });
  }
  leadAgo -= 3;
});

// --- Report -----------------------------------------------------------------
console.log('Seed complete. Jessica id =', jessica);
const dash = getDashboard(db, jessica);
console.log('\nHOME  :', 'rank', dash.user.rank, '| this-month ₹' + dash.totalEarnedThisMonth, '| clicks', dash.linkClicks, '| conversions', dash.conversions, '| ' + (dash.rankProgress ? dash.rankProgress.salesToNext + ' from ' + dash.rankProgress.nextRank : ''));
const links = getLinks(db, jessica);
console.log('LINKS :', links.campaigns.map((c) => `${c.title} ${c.clicks}clk ${c.conversionRate}% (${c.activeDays}d)`).join(' | '));
const wallet = getWallet(db, jessica);
console.log('WALLET:', 'paid ₹' + wallet.totalPayoutsToDate, '| pending ₹' + wallet.pendingCommissions, '| prestige', wallet.prestige.level, '→', wallet.prestige.nextLevel, '| verifying', wallet.verifyingCount, '| txns', wallet.transactions.length);
const lb = getLeaderboard(db, jessica);
console.log('BOARD :', 'total', lb.total);
console.log('        podium:', lb.podium.map((p) => `#${p.rank} ${p.name} [${p.tier}] ₹${p.earnings}`).join(' | '));
lb.rows.slice(0, 6).forEach((r) => console.log('       ', `#${r.rank} ${r.name} [${r.tier}] ₹${r.earnings}`));
console.log('        me: rank', lb.me.rank, '₹' + lb.me.earnings, 'top ' + lb.me.percentile + '%');
