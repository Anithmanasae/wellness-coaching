const express = require('express');
const { openDb } = require('./db');
const { registerAffiliate, recordPurchase, holdersForPincode } = require('./engine');
const { getDashboard } = require('./dashboard');
const { getLinks, slugify } = require('./links');
const { getWallet, requestPayout, approvePayout, settlePayout, rejectPayout } = require('./wallet');
const { getLeaderboard } = require('./leaderboard');
const { recordClick, recordConversion } = require('./referral');

const CONVERSION_SECRET = process.env.CONVERSION_SECRET || 'dev-secret';
const PORT = process.env.PORT || 4000;

// Wrap an async handler so rejections become 400s instead of crashing.
const wrap = (fn) => (req, res) => Promise.resolve(fn(req, res)).catch((err) => {
  res.status(400).json({ error: err.message });
});

async function buildApp() {
  const db = await openDb();
  const app = express();
  app.use(express.json());

  app.use((req, res, next) => {
    res.set('Access-Control-Allow-Origin', '*');
    res.set('Access-Control-Allow-Headers', 'Content-Type');
    res.set('Access-Control-Allow-Methods', 'GET,POST,PUT');
    if (req.method === 'OPTIONS') return res.sendStatus(204);
    next();
  });

  app.get('/api/health', (req, res) => res.json({ ok: true }));

  // Public referral redirect: record the click, forward to the coach's course
  // page carrying the referral code through to checkout.
  app.get('/ref/:code', wrap(async (req, res) => {
    const { destination } = await recordClick(db, req.params.code);
    res.redirect(302, destination);
  }));

  // Sale postback from the coach's site (secured by a shared secret).
  app.post('/api/conversions', wrap(async (req, res) => {
    if ((req.get('X-Webhook-Secret') || '') !== CONVERSION_SECRET) {
      return res.status(401).json({ error: 'invalid webhook secret' });
    }
    const { ref, productCode, externalOrderId, customerName, customerEmail, pincode } = req.body || {};
    const result = await recordConversion(db, { ref, productCode, externalOrderId, customerName, customerEmail, pincode });
    res.status(result.duplicate ? 200 : 201).json(result);
  }));

  app.get('/api/users/:id/dashboard', wrap(async (req, res) => {
    const data = await getDashboard(db, Number(req.params.id));
    if (!data) return res.status(404).json({ error: 'user not found' });
    res.json(data);
  }));

  app.post('/api/affiliates', wrap(async (req, res) => {
    const { name, email, phone, pincode, sponsorId } = req.body || {};
    if (!name || !pincode) return res.status(400).json({ error: 'name and pincode are required' });
    res.status(201).json(await registerAffiliate(db, { name, email, phone, pincode, sponsorId }));
  }));

  app.post('/api/purchases', wrap(async (req, res) => {
    const { buyerId, productCode } = req.body || {};
    if (!buyerId || !productCode) return res.status(400).json({ error: 'buyerId and productCode are required' });
    res.status(201).json(await recordPurchase(db, { buyerId, productCode }));
  }));

  app.post('/api/users/:id/clicks', wrap(async (req, res) => {
    const { campaignLinkId } = req.body || {};
    await db.run('INSERT INTO link_clicks (user_id, campaign_link_id) VALUES (?, ?)', [Number(req.params.id), campaignLinkId || null]);
    res.status(201).json({ ok: true });
  }));

  app.get('/api/users/:id/links', wrap(async (req, res) => {
    const data = await getLinks(db, Number(req.params.id));
    if (!data) return res.status(404).json({ error: 'user not found' });
    res.json(data);
  }));

  app.post('/api/users/:id/links', wrap(async (req, res) => {
    const { title, tag, productCode } = req.body || {};
    if (!title) return res.status(400).json({ error: 'title is required' });
    const product = productCode ? await db.get('SELECT id FROM products WHERE code = ?', [productCode]) : null;
    const base = slugify(title);
    let slug = base;
    let n = 1;
    while (await db.get('SELECT 1 FROM campaign_links WHERE slug = ?', [slug])) slug = `${base}-${++n}`;
    const row = await db.get('INSERT INTO campaign_links (user_id, slug, title, tag, product_id) VALUES (?, ?, ?, ?, ?) RETURNING id', [Number(req.params.id), slug, title, tag || null, product ? product.id : null]);
    res.status(201).json({ id: row.id, slug });
  }));

  app.get('/api/users/:id/wallet', wrap(async (req, res) => {
    const data = await getWallet(db, Number(req.params.id));
    if (!data) return res.status(404).json({ error: 'user not found' });
    res.json(data);
  }));

  app.post('/api/users/:id/payouts', wrap(async (req, res) => {
    res.status(201).json(await requestPayout(db, Number(req.params.id), { method: (req.body || {}).method }));
  }));

  // Coach: pending payout requests, and actions on a payout.
  app.get('/api/payouts', wrap(async (req, res) => {
    const status = req.query.status || 'requested';
    res.json(await db.all(
      `SELECT p.*, u.name AS affiliate_name FROM payouts p
       JOIN users u ON u.id = p.user_id WHERE p.status = ? ORDER BY p.created_at ASC`,
      [status]
    ));
  }));
  const payoutAction = (fn) => wrap(async (req, res) => res.json(await fn(db, Number(req.params.id))));
  app.post('/api/payouts/:id/approve', payoutAction(approvePayout));
  app.post('/api/payouts/:id/settle', payoutAction(settlePayout));
  app.post('/api/payouts/:id/reject', payoutAction(rejectPayout));

  app.get('/api/users/:id/commissions', wrap(async (req, res) => {
    res.json(await db.all(
      `SELECT c.*, p.name AS product_name, b.name AS buyer_name
       FROM commissions c
       LEFT JOIN products p ON p.id = c.product_id
       LEFT JOIN users b ON b.id = c.source_user_id
       WHERE c.user_id = ? ORDER BY c.created_at DESC, c.id DESC LIMIT 200`,
      [Number(req.params.id)]
    ));
  }));

  app.get('/api/products', wrap(async (req, res) => {
    const products = await db.all('SELECT * FROM products ORDER BY tier_rank');
    for (const p of products) {
      p.levels = await db.all('SELECT level, amount FROM commission_levels WHERE product_id = ? ORDER BY level', [p.id]);
      p.geo = await db.all('SELECT level, amount FROM geo_levels WHERE product_id = ?', [p.id]);
    }
    res.json(products);
  }));

  app.get('/api/pincodes/:pincode/holders', wrap(async (req, res) => {
    res.json(await holdersForPincode(db, req.params.pincode));
  }));

  app.put('/api/products/:code/levels/:level', wrap(async (req, res) => {
    const { amount } = req.body || {};
    if (typeof amount !== 'number') return res.status(400).json({ error: 'amount must be a number' });
    const product = await db.get('SELECT id FROM products WHERE code = ?', [req.params.code]);
    if (!product) return res.status(404).json({ error: 'unknown product' });
    await db.run('UPDATE commission_levels SET amount = ? WHERE product_id = ? AND level = ?', [amount, product.id, Number(req.params.level)]);
    res.json({ ok: true });
  }));

  app.put('/api/products/:code/geo/:geoLevel', wrap(async (req, res) => {
    const { amount } = req.body || {};
    if (typeof amount !== 'number') return res.status(400).json({ error: 'amount must be a number' });
    const product = await db.get('SELECT id FROM products WHERE code = ?', [req.params.code]);
    if (!product) return res.status(404).json({ error: 'unknown product' });
    await db.run('UPDATE geo_levels SET amount = ? WHERE product_id = ? AND level = ?', [amount, product.id, req.params.geoLevel]);
    res.json({ ok: true });
  }));

  app.get('/api/settings', wrap(async (req, res) => res.json(await db.all('SELECT * FROM settings'))));
  app.put('/api/settings/:key', wrap(async (req, res) => {
    const { value } = req.body || {};
    if (typeof value !== 'number') return res.status(400).json({ error: 'value must be a number' });
    const r = await db.run('UPDATE settings SET value = ? WHERE key = ?', [value, req.params.key]);
    if (r.changes === 0) return res.status(404).json({ error: 'unknown setting' });
    res.json({ ok: true });
  }));

  app.get('/api/leaderboard', wrap(async (req, res) => {
    res.json(await getLeaderboard(db, req.query.me != null ? Number(req.query.me) : null));
  }));

  return { app, db };
}

if (require.main === module) {
  buildApp().then(({ app }) => {
    app.listen(PORT, () => console.log(`API listening on http://localhost:${PORT} (driver: ${process.env.DB_DRIVER || 'sqlite'})`));
  }).catch((err) => {
    console.error('Failed to start:', err);
    process.exit(1);
  });
}

module.exports = { buildApp };
