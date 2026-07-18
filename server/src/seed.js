// Demo seed for the coach's team, built through the real commission engine so
// every number on Jessica's home screen is genuinely computed, not faked:
//   Total earned this month  ₹1,250.00
//   Link clicks              842
//   Conversions              14
//   Next payout (locked)     ₹450.00
//   Rank                     Gold, 3 sales away from Platinum
//   Recent: Ananya R. +₹65.00 (Cleanse Program Referral),
//           Marcus K. +₹12.50 (Subscription Plan renewal)
const fs = require('fs');
const { createDb, DB_PATH } = require('./db');
const { registerAffiliate, recordSale } = require('./engine');

if (fs.existsSync(DB_PATH)) fs.unlinkSync(DB_PATH);
const db = createDb();

const now = new Date();
const ym = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
const day = (d, time) => `${ym}-${String(d).padStart(2, '0')} ${time}`;

// --- Geography: Bengaluru Urban district and its 5 taluks -------------------
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

// --- Territory managers (created first, then assigned) ----------------------
const arjun = registerAffiliate(db, { name: 'Arjun M.', email: 'arjun@example.com', pincode: '560001' });
const deepa = registerAffiliate(db, { name: 'Deepa S.', email: 'deepa@example.com', pincode: '560003' });
const suresh = registerAffiliate(db, { name: 'Suresh K.', email: 'suresh@example.com', pincode: '560004' });
const insMgr = db.prepare('INSERT INTO territory_managers (level, territory, user_id) VALUES (?, ?, ?)');
insMgr.run('area', '560001', arjun);
insMgr.run('taluk', 'Bangalore North', deepa);
insMgr.run('district', 'Bengaluru Urban', suresh);

// --- Products ---------------------------------------------------------------
const insProduct = db.prepare('INSERT INTO products (name, price) VALUES (?, ?)');
const retreat = insProduct.run('Wellness Retreat Pass', 800).lastInsertRowid;
const subscription = insProduct.run('Subscription Plan', 250).lastInsertRowid;
const tea = insProduct.run('Herbal Tea Kit', 100).lastInsertRowid;
const cleanse = insProduct.run('Cleanse Program', 650).lastInsertRowid;

// --- Team: Jessica and her downline ----------------------------------------
// Registering them fires the geo join bonuses to Arjun/Deepa/Suresh.
const jessica = registerAffiliate(db, {
  name: 'Jessica', email: 'jessica@example.com', pincode: '560001', joinedAt: day(1, '09:00:00'),
});
const priya = registerAffiliate(db, {
  name: 'Priya N.', email: 'priya@example.com', pincode: '560003', sponsorId: jessica, joinedAt: day(2, '09:00:00'),
});
const rohan = registerAffiliate(db, {
  name: 'Rohan V.', email: 'rohan@example.com', pincode: '560043', sponsorId: priya, joinedAt: day(3, '09:00:00'),
});

// --- Jessica's 14 personal sales, walking her Bronze -> Silver -> Gold ------
// 5 x ₹800 at Bronze 20%  = ₹800.00 (these get paid out)
// 5 x ₹250 at Silver 22%  = ₹275.00
// 3 x ₹100 + 1 x ₹90 at Gold 25% = ₹97.50
const customers = ['Kavya T.', 'Nikhil B.', 'Sara J.', 'Vivek P.', 'Meera L.',
  'Aditya R.', 'Farah H.', 'Dinesh C.', 'Lakshmi V.', 'Tanya G.',
  'Ishaan D.', 'Pooja M.', 'Ritu S.', 'Karan W.'];
let d = 2;
for (let i = 0; i < 5; i++) {
  recordSale(db, { sellerId: jessica, productId: retreat, customerName: customers[i], createdAt: day(d++, '11:00:00') });
}
for (let i = 5; i < 10; i++) {
  recordSale(db, { sellerId: jessica, productId: subscription, customerName: customers[i], createdAt: day(d++, '11:00:00') });
}
for (let i = 10; i < 13; i++) {
  recordSale(db, { sellerId: jessica, productId: tea, customerName: customers[i], createdAt: day(d++, '11:00:00') });
}
recordSale(db, { sellerId: jessica, productId: tea, customerName: customers[13], amount: 90, createdAt: day(d++, '11:00:00') });

// --- Downline activity that lands on Jessica's home screen ------------------
// Rohan (level 2 under Jessica) renews Marcus K.'s subscription -> Jessica +₹12.50
recordSale(db, {
  sellerId: rohan, productId: subscription, customerName: 'Marcus K.',
  note: 'Subscription Plan renewal', createdAt: day(16, '10:00:00'),
});
// Priya (level 1 under Jessica) sells a Cleanse Program to Ananya R. -> Jessica +₹65.00
recordSale(db, {
  sellerId: priya, productId: cleanse, customerName: 'Ananya R.',
  note: 'Cleanse Program Referral', createdAt: day(17, '15:00:00'),
});

// --- Payout state: her first five commissions have already been paid --------
db.prepare(
  `UPDATE commissions SET status = 'paid' WHERE id IN (
     SELECT id FROM commissions WHERE user_id = ? AND type = 'personal_sale'
     ORDER BY created_at LIMIT 5)`
).run(jessica);

// --- 842 link clicks --------------------------------------------------------
const insClick = db.prepare('INSERT INTO link_clicks (user_id, clicked_at) VALUES (?, ?)');
const clickTx = db.transaction(() => {
  for (let i = 0; i < 842; i++) insClick.run(jessica, day(1 + (i % 17), '12:00:00'));
});
clickTx();

console.log('Seed complete.');
console.log({ jessica, priya, rohan, arjun, deepa, suresh });
