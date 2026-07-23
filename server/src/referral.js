// Referral tracking and sale attribution.
//
// Flow:
//   1. An affiliate shares a link:  {REFERRAL_BASE}{code}
//      where `code` is either their personal referral_code or a campaign slug.
//   2. A visitor opens it -> GET /ref/:code records a click and 302-redirects
//      to the coach's course page with ?ref=<code> appended so the code
//      survives to checkout.
//   3. When the sale completes, the coach's site posts back to
//      POST /api/conversions { ref, productCode, externalOrderId, ... }.
//      We resolve the referrer, attach the buyer under them, and run the full
//      commission cascade via the engine.

const { recordPurchase, createUserNode } = require('./engine');

const COURSE_URL = process.env.COURSE_URL || 'https://epiclife.academy/course.asp';
const REFERRAL_BASE = process.env.REFERRAL_BASE || 'premium-wellness.club/ref/';

// Resolve a share code to its owning affiliate (and campaign link, if any).
async function resolveRef(db, code) {
  if (!code) return null;
  const link = await db.get('SELECT id, user_id FROM campaign_links WHERE slug = ?', [code]);
  if (link) return { referrerId: link.user_id, campaignLinkId: link.id };
  const user = await db.get('SELECT id FROM users WHERE referral_code = ?', [code]);
  if (user) return { referrerId: user.id, campaignLinkId: null };
  return null;
}

function destinationFor(code) {
  const sep = COURSE_URL.includes('?') ? '&' : '?';
  return `${COURSE_URL}${sep}ref=${encodeURIComponent(code)}`;
}

// Record a click on a share code. Returns the redirect destination regardless
// (an unknown code still forwards to the course, just untracked).
async function recordClick(db, code) {
  const ref = await resolveRef(db, code);
  if (ref) {
    await db.run('INSERT INTO link_clicks (user_id, campaign_link_id) VALUES (?, ?)', [ref.referrerId, ref.campaignLinkId]);
  }
  return { matched: !!ref, destination: destinationFor(code) };
}

// Attribute a completed sale to the referring affiliate and fire commissions.
// Idempotent on externalOrderId. The buyer is attached under the referrer;
// a repeat buyer (same email) reuses their existing node.
async function recordConversion(db, { ref, productCode, externalOrderId, customerName = null, customerEmail = null, pincode = null }) {
  if (!ref) throw new Error('ref is required');
  if (!productCode) throw new Error('productCode is required');
  if (!externalOrderId) throw new Error('externalOrderId is required');

  const resolved = await resolveRef(db, ref);
  if (!resolved) throw new Error(`Unknown referral code: ${ref}`);

  return db.tx(async (t) => {
    const already = await t.get('SELECT id FROM purchases WHERE external_order_id = ?', [externalOrderId]);
    if (already) return { duplicate: true, purchaseId: already.id };

    let buyer = customerEmail ? await t.get('SELECT * FROM users WHERE email = ?', [customerEmail]) : null;
    let buyerId;
    if (buyer) {
      buyerId = buyer.id;
      if (pincode && !buyer.pincode) {
        await t.run('UPDATE users SET pincode = ? WHERE id = ?', [pincode, buyerId]);
      }
    } else {
      buyerId = await createUserNode(t, {
        name: customerName || 'Referred Customer',
        email: customerEmail,
        pincode,
        sponsorId: resolved.referrerId,
      });
    }

    const result = await recordPurchase(t, {
      buyerId,
      productCode,
      campaignLinkId: resolved.campaignLinkId,
      externalOrderId,
    });
    return { duplicate: false, buyerId, referrerId: resolved.referrerId, ...result };
  });
}

module.exports = { resolveRef, recordClick, recordConversion, destinationFor, COURSE_URL, REFERRAL_BASE };
