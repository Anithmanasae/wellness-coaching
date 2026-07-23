// Commission engine — the single place where money is awarded.
//
// The coach's plan pays FIXED rupee amounts up 12 upline levels, per product,
// plus a geographic override to the pincode/taluk/district holders of the
// buyer's area. Two rules from the coach:
//   - No compression: only real ancestors are paid; missing/unqualified levels
//     are forfeited (retained by the company), never rolled up.
//   - Qualification gate: an upline earns a level payout only if they own a
//     package of equal-or-higher tier than the purchased product. Geographic
//     overrides are NOT gated (the holder paid for the territory).

function getSetting(db, key) {
  const row = db.prepare('SELECT value FROM settings WHERE key = ?').get(key);
  if (!row) throw new Error(`Missing setting: ${key}`);
  return row.value;
}

function productByCode(db, code) {
  const p = db.prepare('SELECT * FROM products WHERE code = ?').get(code);
  if (!p) throw new Error(`Unknown product code: ${code}`);
  return p;
}

// Resolve the area/taluk/district holders for a pincode.
// Returns { area, taluk, district } of userId | null.
function holdersForPincode(db, pincode) {
  const geo = db.prepare('SELECT * FROM pincodes WHERE pincode = ?').get(pincode);
  const holderFor = db.prepare(
    'SELECT user_id FROM territory_holders WHERE level = ? AND territory = ?'
  );
  const area = holderFor.get('area', pincode);
  const taluk = geo ? holderFor.get('taluk', geo.taluk) : null;
  const district = geo ? holderFor.get('district', geo.district) : null;
  return {
    area: area ? area.user_id : null,
    taluk: taluk ? taluk.user_id : null,
    district: district ? district.user_id : null,
  };
}

function insertCommission(db, { userId, kind, level = null, purchaseId, sourceUserId, productId, amount, createdAt }) {
  if (!amount || amount <= 0) return;
  if (createdAt) {
    db.prepare(
      `INSERT INTO commissions (user_id, kind, level, source_purchase_id, source_user_id, product_id, amount, created_at)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?)`
    ).run(userId, kind, level, purchaseId, sourceUserId, productId, amount, createdAt);
  } else {
    db.prepare(
      `INSERT INTO commissions (user_id, kind, level, source_purchase_id, source_user_id, product_id, amount)
       VALUES (?, ?, ?, ?, ?, ?, ?)`
    ).run(userId, kind, level, purchaseId, sourceUserId, productId, amount);
  }
}

// The core money path. Records a purchase and every commission it generates.
// Returns { purchaseId, paid: [...], forfeited: [...] } for transparency.
function recordPurchase(db, { buyerId, productCode, campaignLinkId = null, createdAt = null }) {
  const tx = db.transaction(() => {
    const buyer = db.prepare('SELECT * FROM users WHERE id = ?').get(buyerId);
    if (!buyer) throw new Error(`Unknown buyer ${buyerId}`);
    const product = productByCode(db, productCode);
    const gateOn = getSetting(db, 'qualification_gate') === 1;

    const purchaseInfo = createdAt
      ? db.prepare('INSERT INTO purchases (buyer_id, product_id, amount, campaign_link_id, created_at) VALUES (?, ?, ?, ?, ?)')
          .run(buyerId, product.id, product.price, campaignLinkId, createdAt)
      : db.prepare('INSERT INTO purchases (buyer_id, product_id, amount, campaign_link_id) VALUES (?, ?, ?, ?)')
          .run(buyerId, product.id, product.price, campaignLinkId);
    const purchaseId = purchaseInfo.lastInsertRowid;

    const paid = [];
    const forfeited = [];

    // 1. 12-level upline payouts.
    const levelRows = db
      .prepare('SELECT level, amount FROM commission_levels WHERE product_id = ? ORDER BY level')
      .all(product.id);
    const payoutByLevel = new Map(levelRows.map((r) => [r.level, r.amount]));

    let ancestorId = buyer.sponsor_id;
    for (let level = 1; level <= 12; level++) {
      if (!ancestorId) break; // chain ended — remaining levels forfeited (no compression)
      const ancestor = db.prepare('SELECT id, sponsor_id, highest_tier_rank FROM users WHERE id = ?').get(ancestorId);
      const amount = payoutByLevel.get(level) || 0;

      if (amount > 0) {
        const qualified = !gateOn || ancestor.highest_tier_rank >= product.tier_rank;
        if (qualified) {
          insertCommission(db, {
            userId: ancestor.id, kind: 'level', level, purchaseId,
            sourceUserId: buyerId, productId: product.id, amount, createdAt,
          });
          paid.push({ userId: ancestor.id, level, amount });
        } else {
          forfeited.push({ userId: ancestor.id, level, amount, reason: 'unqualified_tier' });
        }
      }
      ancestorId = ancestor.sponsor_id;
    }

    // 2. Geographic overrides (not gated).
    const holders = holdersForPincode(db, buyer.pincode);
    const geoRows = db
      .prepare('SELECT level, amount FROM geo_levels WHERE product_id = ?')
      .all(product.id);
    const geoByLevel = new Map(geoRows.map((r) => [r.level, r.amount]));
    for (const geoLevel of ['area', 'taluk', 'district']) {
      const holderId = holders[geoLevel];
      const amount = geoByLevel.get(geoLevel) || 0;
      // A holder earns no override on their own purchase.
      if (holderId && holderId !== buyerId && amount > 0) {
        insertCommission(db, {
          userId: holderId, kind: `geo_${geoLevel}`, purchaseId,
          sourceUserId: buyerId, productId: product.id, amount, createdAt,
        });
        paid.push({ userId: holderId, geoLevel, amount });
      }
    }

    // 3. Territory grant: some packages make the buyer the protected holder
    //    of their own pincode (area) or taluk, if it is not already claimed.
    if (product.grants_territory) {
      const geo = db.prepare('SELECT * FROM pincodes WHERE pincode = ?').get(buyer.pincode);
      const territory = product.grants_territory === 'area'
        ? buyer.pincode
        : geo ? geo.taluk : null;
      if (territory) {
        db.prepare(
          `INSERT OR IGNORE INTO territory_holders (level, territory, user_id, granted_by_purchase_id)
           VALUES (?, ?, ?, ?)`
        ).run(product.grants_territory, territory, buyerId, purchaseId);
      }
    }

    // 4. Raise the buyer's qualification tier to this product's tier.
    if (product.tier_rank > buyer.highest_tier_rank) {
      db.prepare('UPDATE users SET highest_tier_rank = ? WHERE id = ?').run(product.tier_rank, buyerId);
    }

    // 5. Refresh the buyer's sponsor's cosmetic rank (their conversion count grew).
    if (buyer.sponsor_id) refreshRank(db, buyer.sponsor_id);

    return { purchaseId, paid, forfeited };
  });
  return tx();
}

// Register a new affiliate: create the user record and record their ₹250
// Registration purchase (which pays their upline + geo holders).
function registerAffiliate(db, { name, email = null, phone = null, pincode, sponsorId = null, campaignLinkId = null, joinedAt = null }) {
  const tx = db.transaction(() => {
    const info = joinedAt
      ? db.prepare('INSERT INTO users (name, email, phone, pincode, sponsor_id, joined_at) VALUES (?, ?, ?, ?, ?, ?)')
          .run(name, email, phone, pincode, sponsorId, joinedAt)
      : db.prepare('INSERT INTO users (name, email, phone, pincode, sponsor_id) VALUES (?, ?, ?, ?, ?)')
          .run(name, email, phone, pincode, sponsorId);
    const userId = info.lastInsertRowid;
    const result = recordPurchase(db, { buyerId: userId, productCode: 'REG', campaignLinkId, createdAt: joinedAt });
    return { userId, ...result };
  });
  return tx();
}

// Conversions an advocate has driven = purchases by their direct recruits
// (they were the L-1 earner, or would have been if qualified).
function conversionCount(db, userId) {
  return db
    .prepare(
      `SELECT COUNT(*) AS n FROM purchases p
       JOIN users u ON u.id = p.buyer_id
       WHERE u.sponsor_id = ?`
    )
    .get(userId).n;
}

function rankForConversions(db, count) {
  return db
    .prepare('SELECT * FROM ranks WHERE min_conversions <= ? ORDER BY sort_order DESC LIMIT 1')
    .get(count);
}

function nextRank(db, rankName) {
  const current = db.prepare('SELECT * FROM ranks WHERE name = ?').get(rankName);
  if (!current) return null;
  return db
    .prepare('SELECT * FROM ranks WHERE sort_order > ? ORDER BY sort_order ASC LIMIT 1')
    .get(current.sort_order);
}

function refreshRank(db, userId) {
  const earned = rankForConversions(db, conversionCount(db, userId));
  if (earned) db.prepare('UPDATE users SET rank = ? WHERE id = ?').run(earned.name, userId);
}

// Next payout: the coming payout day this month, or next month if it passed.
function nextPayoutDate(db, from = new Date()) {
  const day = getSetting(db, 'payout_day');
  const d = new Date(from);
  const candidate = new Date(d.getFullYear(), d.getMonth(), day);
  if (candidate <= d) candidate.setMonth(candidate.getMonth() + 1);
  return candidate;
}

module.exports = {
  recordPurchase,
  registerAffiliate,
  holdersForPincode,
  conversionCount,
  rankForConversions,
  nextRank,
  refreshRank,
  nextPayoutDate,
  getSetting,
};
