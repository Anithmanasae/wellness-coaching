// Referral tracking and sale attribution.
//
// Flow:
//   1. An affiliate shares a link:  {REFERRAL_BASE}/{code}
//      where `code` is either their personal referral_code or a campaign slug.
//   2. A visitor opens it -> GET /ref/:code records a click and 302-redirects
//      to the coach's course page with ?ref=<code> appended so the code
//      survives to checkout.
//   3. When the sale completes, the coach's site posts back to
//      POST /api/conversions { ref, productCode, externalOrderId, ... }.
//      We resolve the referrer, attach the buyer under them, and run the full
//      commission cascade via the engine — upline levels, geo overrides, the
//      qualification gate, everything.

const { recordPurchase, createUserNode } = require('./engine');

const COURSE_URL = process.env.COURSE_URL || 'https://epiclife.academy/course.asp';
const REFERRAL_BASE = process.env.REFERRAL_BASE || 'premium-wellness.club/ref/';

// Resolve a share code to its owning affiliate (and campaign link, if any).
// A code can be a campaign slug or an affiliate's personal referral_code.
function resolveRef(db, code) {
  if (!code) return null;
  const link = db.prepare('SELECT id, user_id FROM campaign_links WHERE slug = ?').get(code);
  if (link) return { referrerId: link.user_id, campaignLinkId: link.id };
  const user = db.prepare('SELECT id FROM users WHERE referral_code = ?').get(code);
  if (user) return { referrerId: user.id, campaignLinkId: null };
  return null;
}

// The full destination a share code redirects to (code echoed for checkout).
function destinationFor(code) {
  const sep = COURSE_URL.includes('?') ? '&' : '?';
  return `${COURSE_URL}${sep}ref=${encodeURIComponent(code)}`;
}

// Record a click on a share code. Returns the redirect destination regardless
// (an unknown code still forwards to the course, just untracked).
function recordClick(db, code) {
  const ref = resolveRef(db, code);
  if (ref) {
    db.prepare('INSERT INTO link_clicks (user_id, campaign_link_id) VALUES (?, ?)')
      .run(ref.referrerId, ref.campaignLinkId);
  }
  return { matched: !!ref, destination: destinationFor(code) };
}

// Attribute a completed sale to the referring affiliate and fire commissions.
// Idempotent on externalOrderId. The buyer is attached under the referrer;
// a repeat buyer (same email) reuses their existing node.
function recordConversion(db, { ref, productCode, externalOrderId, customerName = null, customerEmail = null, pincode = null }) {
  if (!ref) throw new Error('ref is required');
  if (!productCode) throw new Error('productCode is required');
  if (!externalOrderId) throw new Error('externalOrderId is required');

  const resolved = resolveRef(db, ref);
  if (!resolved) throw new Error(`Unknown referral code: ${ref}`);

  const tx = db.transaction(() => {
    const already = db.prepare('SELECT id FROM purchases WHERE external_order_id = ?').get(externalOrderId);
    if (already) return { duplicate: true, purchaseId: already.id };

    // Find the buyer by email, or create a new node under the referrer.
    let buyer = customerEmail
      ? db.prepare('SELECT * FROM users WHERE email = ?').get(customerEmail)
      : null;
    let buyerId;
    if (buyer) {
      buyerId = buyer.id;
      // Backfill a pincode if we now have one and didn't before (enables geo).
      if (pincode && !buyer.pincode) {
        db.prepare('UPDATE users SET pincode = ? WHERE id = ?').run(pincode, buyerId);
      }
    } else {
      buyerId = createUserNode(db, {
        name: customerName || 'Referred Customer',
        email: customerEmail,
        pincode,
        sponsorId: resolved.referrerId,
      });
    }

    const result = recordPurchase(db, {
      buyerId,
      productCode,
      campaignLinkId: resolved.campaignLinkId,
      externalOrderId,
    });
    return { duplicate: false, buyerId, referrerId: resolved.referrerId, ...result };
  });
  return tx();
}

module.exports = { resolveRef, recordClick, recordConversion, destinationFor, COURSE_URL, REFERRAL_BASE };
