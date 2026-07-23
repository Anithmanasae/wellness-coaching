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
//
// All database access goes through the async adapter (`db`), which may be a
// top-level handle or a transaction handle; calling db.tx() nests correctly.

async function getSetting(db, key) {
  const row = await db.get('SELECT value FROM settings WHERE key = ?', [key]);
  if (!row) throw new Error(`Missing setting: ${key}`);
  return row.value;
}

async function productByCode(db, code) {
  const p = await db.get('SELECT * FROM products WHERE code = ?', [code]);
  if (!p) throw new Error(`Unknown product code: ${code}`);
  return p;
}

function slugifyName(name) {
  return String(name).toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '') || 'ref';
}

// Give a user a unique, human-readable referral code (their share link tail).
async function assignReferralCode(db, userId, name) {
  const base = slugifyName(name);
  let code = base;
  let n = 1;
  while (await db.get('SELECT 1 FROM users WHERE referral_code = ? AND id != ?', [code, userId])) {
    code = `${base}-${++n}`;
  }
  await db.run('UPDATE users SET referral_code = ? WHERE id = ?', [code, userId]);
  return code;
}

// Insert a user node in the network (no purchase). Used both when an affiliate
// registers and when a referred customer first appears via a conversion.
async function createUserNode(db, { name, email = null, phone = null, pincode = null, sponsorId = null, joinedAt = null }) {
  const row = joinedAt
    ? await db.get('INSERT INTO users (name, email, phone, pincode, sponsor_id, joined_at) VALUES (?, ?, ?, ?, ?, ?) RETURNING id', [name, email, phone, pincode, sponsorId, joinedAt])
    : await db.get('INSERT INTO users (name, email, phone, pincode, sponsor_id) VALUES (?, ?, ?, ?, ?) RETURNING id', [name, email, phone, pincode, sponsorId]);
  await assignReferralCode(db, row.id, name);
  return row.id;
}

// Resolve the area/taluk/district holders for a pincode.
// Returns { area, taluk, district } of userId | null.
async function holdersForPincode(db, pincode) {
  const geo = await db.get('SELECT * FROM pincodes WHERE pincode = ?', [pincode]);
  const holderFor = (level, territory) =>
    db.get('SELECT user_id FROM territory_holders WHERE level = ? AND territory = ?', [level, territory]);
  const area = await holderFor('area', pincode);
  const taluk = geo ? await holderFor('taluk', geo.taluk) : null;
  const district = geo ? await holderFor('district', geo.district) : null;
  return {
    area: area ? area.user_id : null,
    taluk: taluk ? taluk.user_id : null,
    district: district ? district.user_id : null,
  };
}

async function insertCommission(db, { userId, kind, level = null, purchaseId, sourceUserId, productId, amount, createdAt }) {
  if (!amount || amount <= 0) return;
  if (createdAt) {
    await db.run(
      `INSERT INTO commissions (user_id, kind, level, source_purchase_id, source_user_id, product_id, amount, created_at)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?)`,
      [userId, kind, level, purchaseId, sourceUserId, productId, amount, createdAt]
    );
  } else {
    await db.run(
      `INSERT INTO commissions (user_id, kind, level, source_purchase_id, source_user_id, product_id, amount)
       VALUES (?, ?, ?, ?, ?, ?, ?)`,
      [userId, kind, level, purchaseId, sourceUserId, productId, amount]
    );
  }
}

// The core money path. Records a purchase and every commission it generates.
// Returns { purchaseId, paid: [...], forfeited: [...] } for transparency.
async function recordPurchase(db, { buyerId, productCode, campaignLinkId = null, externalOrderId = null, createdAt = null }) {
  // Idempotency: a repeated webhook for the same external order must not pay twice.
  if (externalOrderId) {
    const existing = await db.get('SELECT id FROM purchases WHERE external_order_id = ?', [externalOrderId]);
    if (existing) return { purchaseId: existing.id, duplicate: true, paid: [], forfeited: [] };
  }
  return db.tx(async (t) => {
    const buyer = await t.get('SELECT * FROM users WHERE id = ?', [buyerId]);
    if (!buyer) throw new Error(`Unknown buyer ${buyerId}`);
    const product = await productByCode(t, productCode);
    const gateOn = (await getSetting(t, 'qualification_gate')) === 1;

    const purchaseRow = createdAt
      ? await t.get('INSERT INTO purchases (buyer_id, product_id, amount, campaign_link_id, external_order_id, created_at) VALUES (?, ?, ?, ?, ?, ?) RETURNING id', [buyerId, product.id, product.price, campaignLinkId, externalOrderId, createdAt])
      : await t.get('INSERT INTO purchases (buyer_id, product_id, amount, campaign_link_id, external_order_id) VALUES (?, ?, ?, ?, ?) RETURNING id', [buyerId, product.id, product.price, campaignLinkId, externalOrderId]);
    const purchaseId = purchaseRow.id;

    const paid = [];
    const forfeited = [];

    // 1. 12-level upline payouts.
    const levelRows = await t.all('SELECT level, amount FROM commission_levels WHERE product_id = ? ORDER BY level', [product.id]);
    const payoutByLevel = new Map(levelRows.map((r) => [r.level, r.amount]));

    let ancestorId = buyer.sponsor_id;
    for (let level = 1; level <= 12; level++) {
      if (!ancestorId) break; // chain ended — remaining levels forfeited (no compression)
      const ancestor = await t.get('SELECT id, sponsor_id, highest_tier_rank FROM users WHERE id = ?', [ancestorId]);
      const amount = payoutByLevel.get(level) || 0;

      if (amount > 0) {
        const qualified = !gateOn || ancestor.highest_tier_rank >= product.tier_rank;
        if (qualified) {
          await insertCommission(t, {
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
    const holders = await holdersForPincode(t, buyer.pincode);
    const geoRows = await t.all('SELECT level, amount FROM geo_levels WHERE product_id = ?', [product.id]);
    const geoByLevel = new Map(geoRows.map((r) => [r.level, r.amount]));
    for (const geoLevel of ['area', 'taluk', 'district']) {
      const holderId = holders[geoLevel];
      const amount = geoByLevel.get(geoLevel) || 0;
      // A holder earns no override on their own purchase.
      if (holderId && holderId !== buyerId && amount > 0) {
        await insertCommission(t, {
          userId: holderId, kind: `geo_${geoLevel}`, purchaseId,
          sourceUserId: buyerId, productId: product.id, amount, createdAt,
        });
        paid.push({ userId: holderId, geoLevel, amount });
      }
    }

    // 3. Territory grant: some packages make the buyer the protected holder
    //    of their own pincode (area) or taluk, if it is not already claimed.
    if (product.grants_territory) {
      const geo = await t.get('SELECT * FROM pincodes WHERE pincode = ?', [buyer.pincode]);
      const territory = product.grants_territory === 'area'
        ? buyer.pincode
        : geo ? geo.taluk : null;
      if (territory) {
        await t.run(
          `INSERT INTO territory_holders (level, territory, user_id, granted_by_purchase_id)
           VALUES (?, ?, ?, ?) ON CONFLICT DO NOTHING`,
          [product.grants_territory, territory, buyerId, purchaseId]
        );
      }
    }

    // 4. Raise the buyer's qualification tier to this product's tier.
    if (product.tier_rank > buyer.highest_tier_rank) {
      await t.run('UPDATE users SET highest_tier_rank = ? WHERE id = ?', [product.tier_rank, buyerId]);
    }

    // 5. Refresh the buyer's sponsor's cosmetic rank (their conversion count grew).
    if (buyer.sponsor_id) await refreshRank(t, buyer.sponsor_id);

    return { purchaseId, paid, forfeited };
  });
}

// Register a new affiliate: create the user record and record their ₹250
// Registration purchase (which pays their upline + geo holders).
async function registerAffiliate(db, { name, email = null, phone = null, pincode, sponsorId = null, campaignLinkId = null, joinedAt = null }) {
  return db.tx(async (t) => {
    const userId = await createUserNode(t, { name, email, phone, pincode, sponsorId, joinedAt });
    const result = await recordPurchase(t, { buyerId: userId, productCode: 'REG', campaignLinkId, createdAt: joinedAt });
    return { userId, ...result };
  });
}

// Conversions an advocate has driven = purchases by their direct recruits.
async function conversionCount(db, userId) {
  const row = await db.get(
    `SELECT COUNT(*) AS n FROM purchases p
     JOIN users u ON u.id = p.buyer_id
     WHERE u.sponsor_id = ?`,
    [userId]
  );
  return Number(row.n);
}

async function rankForConversions(db, count) {
  return db.get('SELECT * FROM ranks WHERE min_conversions <= ? ORDER BY sort_order DESC LIMIT 1', [count]);
}

async function nextRank(db, rankName) {
  const current = await db.get('SELECT * FROM ranks WHERE name = ?', [rankName]);
  if (!current) return null;
  return db.get('SELECT * FROM ranks WHERE sort_order > ? ORDER BY sort_order ASC LIMIT 1', [current.sort_order]);
}

async function refreshRank(db, userId) {
  const earned = await rankForConversions(db, await conversionCount(db, userId));
  if (earned) await db.run('UPDATE users SET rank = ? WHERE id = ?', [earned.name, userId]);
}

// Next payout: the coming payout day this month, or next month if it passed.
async function nextPayoutDate(db, from = new Date()) {
  const day = await getSetting(db, 'payout_day');
  const d = new Date(from);
  const candidate = new Date(d.getFullYear(), d.getMonth(), day);
  if (candidate <= d) candidate.setMonth(candidate.getMonth() + 1);
  return candidate;
}

module.exports = {
  recordPurchase,
  registerAffiliate,
  createUserNode,
  assignReferralCode,
  slugifyName,
  holdersForPincode,
  conversionCount,
  rankForConversions,
  nextRank,
  refreshRank,
  nextPayoutDate,
  getSetting,
};
