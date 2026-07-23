// Demo seed for the coach's team, built entirely through the real engine so
// every number on Jessica's home screen is genuinely computed.
//
// Jessica owns Package 3, so she is the PIN-code (area) holder for 560001 and
// qualifies (tier 5) to earn on her recruits' registrations and packages.
const fs = require('fs');
const { createDb, DB_PATH } = require('./db');
const { registerAffiliate, recordPurchase } = require('./engine');
const { getDashboard } = require('./dashboard');

if (fs.existsSync(DB_PATH)) fs.unlinkSync(DB_PATH);
['-shm', '-wal'].forEach((s) => fs.existsSync(DB_PATH + s) && fs.unlinkSync(DB_PATH + s));
const db = createDb();

const now = new Date();
const ym = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
const at = (d, time = '11:00:00') => `${ym}-${String(d).padStart(2, '0')} ${time}`;

// --- Geography: Bengaluru Urban and its 5 taluks ---------------------------
const pincodes = [
  ['560001', 'Shivajinagar', 'Bangalore North', 'Bengaluru Urban'],
  ['560003', 'Malleswaram', 'Bangalore North', 'Bengaluru Urban'],
  ['560004', 'Basavanagudi', 'Bangalore South', 'Bengaluru Urban'],
  ['560043', 'Banaswadi', 'Bangalore East', 'Bengaluru Urban'],
  ['560064', 'Yelahanka New Town', 'Yelahanka', 'Bengaluru Urban'],
  ['562106', 'Anekal', 'Anekal', 'Bengaluru Urban'],
];
const insPin = db.prepare('INSERT INTO pincodes (pincode, area_name, taluk, district) VALUES (?, ?, ?, ?)');
for (const p of pincodes) insPin.run(...p);

// --- Territory holders (taluk + district) ----------------------------------
// The coach / upline leaders. Deepa holds the taluk, Suresh the district.
const deepa = registerAffiliate(db, { name: 'Deepa S.', pincode: '560003', joinedAt: at(1, '08:00:00') }).userId;
const suresh = registerAffiliate(db, { name: 'Suresh K.', pincode: '560004', joinedAt: at(1, '08:05:00') }).userId;
recordPurchase(db, { buyerId: deepa, productCode: 'P5' }); // grants Bangalore North taluk
const insHolder = db.prepare('INSERT OR IGNORE INTO territory_holders (level, territory, user_id) VALUES (?, ?, ?)');
insHolder.run('district', 'Bengaluru Urban', suresh);

// --- Jessica: sponsored by Deepa, buys Package 3 (becomes 560001 area holder)
const jessica = registerAffiliate(db, { name: 'Jessica', email: 'jessica@example.com', pincode: '560001', sponsorId: deepa, joinedAt: at(2, '09:00:00') }).userId;
recordPurchase(db, { buyerId: jessica, productCode: 'P3', createdAt: at(2, '09:30:00') });

// --- Jessica's downline ------------------------------------------------------
// 12 direct recruits register under Jessica (12 conversions + ₹100 L-1 each,
// and ₹100 area override each for those in 560001). A few then buy packages,
// adding more conversions and larger L-1 payouts, taking her to 14 conversions
// (Gold, 3 away from Platinum) and a realistic month's earnings.
const recruits = [
  ['Ananya R.', '560001'], ['Marcus K.', '560001'], ['Kavya T.', '560001'],
  ['Nikhil B.', '560001'], ['Sara J.', '560003'], ['Vivek P.', '560001'],
  ['Meera L.', '560001'], ['Aditya R.', '560043'], ['Farah H.', '560001'],
  ['Dinesh C.', '560001'], ['Lakshmi V.', '560001'], ['Tanya G.', '560064'],
];
const recruitIds = {};
let day = 3;
for (const [name, pin] of recruits) {
  recruitIds[name] = registerAffiliate(db, { name, pincode: pin, sponsorId: jessica, joinedAt: at(day++, '10:00:00') }).userId;
}

// --- Second generation: a recruit of a recruit (gives Jessica an L-2) --------
const rohan = registerAffiliate(db, { name: 'Rohan V.', pincode: '560043', sponsorId: recruitIds['Ananya R.'], joinedAt: at(15, '12:00:00') }).userId;
recordPurchase(db, { buyerId: rohan, productCode: 'P1', createdAt: at(15, '13:00:00') }); // Jessica L-2 +₹350

// Two recruits upgrade to packages — Jessica (tier 5) qualifies for both.
// These are the most recent activity, so they surface on the home screen.
recordPurchase(db, { buyerId: recruitIds['Ananya R.'], productCode: 'P1', createdAt: at(16, '15:00:00') }); // Jessica +₹2000
recordPurchase(db, { buyerId: recruitIds['Marcus K.'], productCode: 'P2', createdAt: at(17, '15:00:00') }); // Jessica +₹3000

// --- 842 referral-link clicks ------------------------------------------------
const insClick = db.prepare('INSERT INTO link_clicks (user_id, clicked_at) VALUES (?, ?)');
const clickTx = db.transaction(() => {
  for (let i = 0; i < 842; i++) insClick.run(jessica, at(2 + (i % 18), '12:00:00'));
});
clickTx();

const dash = getDashboard(db, jessica);
console.log('Seed complete. Jessica id =', jessica);
console.log(JSON.stringify(dash, null, 2));
