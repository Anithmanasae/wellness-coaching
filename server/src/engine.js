// Commission engine — the single place where money is awarded.
//
// Two events create commissions:
//   1. A sale (recordSale): the seller earns their personal rate, their upline
//      earns downline overrides, and the area/taluk/district managers of the
//      seller's pincode earn geo overrides.
//   2. A new affiliate joining (registerAffiliate): the area/taluk/district
//      managers of the new affiliate's pincode earn a flat join bonus.
//
// All rates come from the commission_rules and ranks tables so they can be
// tuned without touching this file.

function getRule(db, key) {
  const row = db.prepare('SELECT value FROM commission_rules WHERE key = ?').get(key);
  if (!row) throw new Error(`Missing commission rule: ${key}`);
  return row.value;
}

function round2(n) {
  return Math.round(n * 100) / 100;
}

function rankForSalesCount(db, count) {
  return db
    .prepare('SELECT * FROM ranks WHERE min_personal_sales <= ? ORDER BY sort_order DESC LIMIT 1')
    .get(count);
}

function nextRank(db, currentRankName) {
  const current = db.prepare('SELECT * FROM ranks WHERE name = ?').get(currentRankName);
  if (!current) return null;
  return db
    .prepare('SELECT * FROM ranks WHERE sort_order > ? ORDER BY sort_order ASC LIMIT 1')
    .get(current.sort_order);
}

// Returns the managers responsible for a pincode as
// { area: userId|null, taluk: userId|null, district: userId|null }.
function managersForPincode(db, pincode) {
  const geo = db.prepare('SELECT * FROM pincodes WHERE pincode = ?').get(pincode);
  const managerFor = db.prepare(
    'SELECT user_id FROM territory_managers WHERE level = ? AND territory = ?'
  );
  const area = managerFor.get('area', pincode);
  const taluk = geo ? managerFor.get('taluk', geo.taluk) : null;
  const district = geo ? managerFor.get('district', geo.district) : null;
  return {
    area: area ? area.user_id : null,
    taluk: taluk ? taluk.user_id : null,
    district: district ? district.user_id : null,
  };
}

function insertCommission(db, { userId, type, saleId = null, sourceUserId = null, rate = null, amount, createdAt = null }) {
  if (amount <= 0) return;
  if (createdAt) {
    db.prepare(
      `INSERT INTO commissions (user_id, type, source_sale_id, source_user_id, rate, amount, created_at)
       VALUES (?, ?, ?, ?, ?, ?, ?)`
    ).run(userId, type, saleId, sourceUserId, rate, round2(amount), createdAt);
  } else {
    db.prepare(
      `INSERT INTO commissions (user_id, type, source_sale_id, source_user_id, rate, amount)
       VALUES (?, ?, ?, ?, ?, ?)`
    ).run(userId, type, saleId, sourceUserId, rate, round2(amount));
  }
}

// Register a new affiliate. Pays the flat join bonus to the geo managers of
// the affiliate's pincode. Runs in a transaction.
function registerAffiliate(db, { name, email = null, phone = null, pincode, sponsorId = null, joinedAt = null }) {
  const tx = db.transaction(() => {
    const info = joinedAt
      ? db.prepare(
          'INSERT INTO users (name, email, phone, pincode, sponsor_id, joined_at) VALUES (?, ?, ?, ?, ?, ?)'
        ).run(name, email, phone, pincode, sponsorId, joinedAt)
      : db.prepare(
          'INSERT INTO users (name, email, phone, pincode, sponsor_id) VALUES (?, ?, ?, ?, ?)'
        ).run(name, email, phone, pincode, sponsorId);
    const newUserId = info.lastInsertRowid;

    const managers = managersForPincode(db, pincode);
    const bonuses = [
      ['area', 'join_bonus_area'],
      ['taluk', 'join_bonus_taluk'],
      ['district', 'join_bonus_district'],
    ];
    for (const [level, ruleKey] of bonuses) {
      const managerId = managers[level];
      // A manager doesn't earn a bonus on their own registration.
      if (managerId && managerId !== newUserId) {
        insertCommission(db, {
          userId: managerId,
          type: `join_bonus_${level}`,
          sourceUserId: newUserId,
          amount: getRule(db, ruleKey),
          createdAt: joinedAt,
        });
      }
    }
    return newUserId;
  });
  return tx();
}

// Record a sale and create every commission it generates.
// amount defaults to the product's list price; pass amount to override
// (discounted sales still commission on the actual amount charged).
function recordSale(db, { sellerId, productId, customerName = null, amount = null, note = null, createdAt = null }) {
  const tx = db.transaction(() => {
    const seller = db.prepare('SELECT * FROM users WHERE id = ?').get(sellerId);
    if (!seller) throw new Error(`Unknown seller ${sellerId}`);
    const product = db.prepare('SELECT * FROM products WHERE id = ?').get(productId);
    if (!product) throw new Error(`Unknown product ${productId}`);
    const saleAmount = amount != null ? amount : product.price;

    const saleInfo = createdAt
      ? db.prepare(
          'INSERT INTO sales (seller_id, product_id, customer_name, amount, note, created_at) VALUES (?, ?, ?, ?, ?, ?)'
        ).run(sellerId, productId, customerName, saleAmount, note, createdAt)
      : db.prepare(
          'INSERT INTO sales (seller_id, product_id, customer_name, amount, note) VALUES (?, ?, ?, ?, ?)'
        ).run(sellerId, productId, customerName, saleAmount, note);
    const saleId = saleInfo.lastInsertRowid;

    // 1. Personal commission at the seller's current rank rate.
    const rank = db.prepare('SELECT * FROM ranks WHERE name = ?').get(seller.rank);
    const personalRate = rank ? rank.personal_rate : 20;
    insertCommission(db, {
      userId: sellerId,
      type: 'personal_sale',
      saleId,
      rate: personalRate,
      amount: (saleAmount * personalRate) / 100,
      createdAt,
    });

    // 2. Downline overrides: direct sponsor (level 1), then their sponsor (level 2).
    const levels = [
      ['downline_l1', getRule(db, 'downline_l1_rate')],
      ['downline_l2', getRule(db, 'downline_l2_rate')],
    ];
    let uplineId = seller.sponsor_id;
    for (const [type, rate] of levels) {
      if (!uplineId) break;
      insertCommission(db, {
        userId: uplineId,
        type,
        saleId,
        rate,
        amount: (saleAmount * rate) / 100,
        createdAt,
      });
      const upline = db.prepare('SELECT sponsor_id FROM users WHERE id = ?').get(uplineId);
      uplineId = upline ? upline.sponsor_id : null;
    }

    // 3. Geo overrides for the seller's territory managers.
    const managers = managersForPincode(db, seller.pincode);
    const geoLevels = [
      ['area', getRule(db, 'geo_sale_area_rate')],
      ['taluk', getRule(db, 'geo_sale_taluk_rate')],
      ['district', getRule(db, 'geo_sale_district_rate')],
    ];
    for (const [level, rate] of geoLevels) {
      const managerId = managers[level];
      // Managers don't earn a geo override on their own personal sales.
      if (managerId && managerId !== sellerId) {
        insertCommission(db, {
          userId: managerId,
          type: `geo_sale_${level}`,
          saleId,
          rate,
          amount: (saleAmount * rate) / 100,
          createdAt,
        });
      }
    }

    // 4. Rank progression: promote the seller if this sale crosses a threshold.
    const salesCount = db
      .prepare('SELECT COUNT(*) AS n FROM sales WHERE seller_id = ?')
      .get(sellerId).n;
    const earned = rankForSalesCount(db, salesCount);
    if (earned && earned.name !== seller.rank) {
      const current = db.prepare('SELECT sort_order FROM ranks WHERE name = ?').get(seller.rank);
      // Ranks are only ever gained, never lost.
      if (!current || earned.sort_order > current.sort_order) {
        db.prepare('UPDATE users SET rank = ? WHERE id = ?').run(earned.name, sellerId);
      }
    }

    return saleId;
  });
  return tx();
}

// Next payout date: the coming `payout_day` of this month, or of next month
// if it has already passed.
function nextPayoutDate(db, from = new Date()) {
  const day = getRule(db, 'payout_day');
  const d = new Date(from);
  const candidate = new Date(d.getFullYear(), d.getMonth(), day);
  if (candidate <= d) candidate.setMonth(candidate.getMonth() + 1);
  return candidate;
}

module.exports = {
  registerAffiliate,
  recordSale,
  managersForPincode,
  rankForSalesCount,
  nextRank,
  nextPayoutDate,
  getRule,
};
