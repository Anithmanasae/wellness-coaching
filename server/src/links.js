// Links & Creatives read-model: an affiliate's referral base plus the
// performance of each of their campaign links.

const REFERRAL_BASE = process.env.REFERRAL_BASE || 'premium-wellness.club/ref/';
const COURSE_URL = process.env.COURSE_URL || 'https://epiclife.academy/course.asp';

function slugify(name) {
  return String(name).toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
}

function daysBetween(fromIso, now) {
  const from = new Date(fromIso);
  return Math.max(0, Math.floor((now - from) / (1000 * 60 * 60 * 24)));
}

function getLinks(db, userId, now = new Date()) {
  const user = db.prepare('SELECT * FROM users WHERE id = ?').get(userId);
  if (!user) return null;

  const links = db
    .prepare('SELECT * FROM campaign_links WHERE user_id = ? ORDER BY created_at DESC')
    .all(userId);

  const clicksFor = db.prepare('SELECT COUNT(*) AS n FROM link_clicks WHERE campaign_link_id = ?');
  const convFor = db.prepare(
    'SELECT COUNT(*) AS n, COUNT(DISTINCT buyer_id) AS buyers FROM purchases WHERE campaign_link_id = ?'
  );

  const campaigns = links.map((link) => {
    const clicks = clicksFor.get(link.id).n;
    const conv = convFor.get(link.id);
    const conversions = conv.n;
    return {
      id: link.id,
      slug: link.slug,
      title: link.title,
      tag: link.tag,
      shareUrl: `${REFERRAL_BASE}${link.slug}`,
      clicks,
      conversions,
      conversionRate: clicks > 0 ? Math.round((conversions / clicks) * 1000) / 10 : 0,
      converterCount: conv.buyers,
      activeDays: daysBetween(link.created_at, now),
    };
  });

  const referralCode = user.referral_code || slugify(user.name);
  return {
    referralBase: REFERRAL_BASE,
    referralCode,
    referralUrl: `${REFERRAL_BASE}${referralCode}`,
    destination: COURSE_URL,
    totalClicks: campaigns.reduce((s, c) => s + c.clicks, 0),
    campaigns,
  };
}

module.exports = { getLinks, slugify, REFERRAL_BASE };
