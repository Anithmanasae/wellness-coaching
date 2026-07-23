const express = require('express');
const { createDb } = require('./db');
const { registerAffiliate, recordPurchase, holdersForPincode } = require('./engine');
const { getDashboard } = require('./dashboard');

const db = createDb();
const app = express();
app.use(express.json());

// Allow the Vite dev server (different port) to call the API.
app.use((req, res, next) => {
  res.set('Access-Control-Allow-Origin', '*');
  res.set('Access-Control-Allow-Headers', 'Content-Type');
  res.set('Access-Control-Allow-Methods', 'GET,POST,PUT');
  if (req.method === 'OPTIONS') return res.sendStatus(204);
  next();
});

app.get('/api/health', (req, res) => res.json({ ok: true }));

// Home screen payload.
app.get('/api/users/:id/dashboard', (req, res) => {
  const data = getDashboard(db, Number(req.params.id));
  if (!data) return res.status(404).json({ error: 'user not found' });
  res.json(data);
});

// Register a new affiliate (records their ₹250 Registration purchase).
app.post('/api/affiliates', (req, res) => {
  const { name, email, phone, pincode, sponsorId } = req.body || {};
  if (!name || !pincode) return res.status(400).json({ error: 'name and pincode are required' });
  try {
    const result = registerAffiliate(db, { name, email, phone, pincode, sponsorId });
    res.status(201).json(result);
  } catch (err) {
    res.status(400).json({ error: err.message });
  }
});

// Record a package purchase by an existing affiliate.
app.post('/api/purchases', (req, res) => {
  const { buyerId, productCode } = req.body || {};
  if (!buyerId || !productCode) return res.status(400).json({ error: 'buyerId and productCode are required' });
  try {
    const result = recordPurchase(db, { buyerId, productCode });
    res.status(201).json(result);
  } catch (err) {
    res.status(400).json({ error: err.message });
  }
});

// Track a referral-link click.
app.post('/api/users/:id/clicks', (req, res) => {
  db.prepare('INSERT INTO link_clicks (user_id) VALUES (?)').run(Number(req.params.id));
  res.status(201).json({ ok: true });
});

// Commission ledger for a user.
app.get('/api/users/:id/commissions', (req, res) => {
  const rows = db
    .prepare(
      `SELECT c.*, p.name AS product_name, b.name AS buyer_name
       FROM commissions c
       LEFT JOIN products p ON p.id = c.product_id
       LEFT JOIN users b ON b.id = c.source_user_id
       WHERE c.user_id = ? ORDER BY c.created_at DESC, c.id DESC LIMIT 200`
    )
    .all(Number(req.params.id));
  res.json(rows);
});

// Catalogue: products with their 12-level and geo payout tables.
app.get('/api/products', (req, res) => {
  const products = db.prepare('SELECT * FROM products ORDER BY tier_rank').all();
  for (const p of products) {
    p.levels = db.prepare('SELECT level, amount FROM commission_levels WHERE product_id = ? ORDER BY level').all(p.id);
    p.geo = db.prepare('SELECT level, amount FROM geo_levels WHERE product_id = ?').all(p.id);
  }
  res.json(products);
});

// Who holds a pincode's area / taluk / district.
app.get('/api/pincodes/:pincode/holders', (req, res) => {
  res.json(holdersForPincode(db, req.params.pincode));
});

// Admin: view / tune the level payout for a product.
app.put('/api/products/:code/levels/:level', (req, res) => {
  const { amount } = req.body || {};
  if (typeof amount !== 'number') return res.status(400).json({ error: 'amount must be a number' });
  const product = db.prepare('SELECT id FROM products WHERE code = ?').get(req.params.code);
  if (!product) return res.status(404).json({ error: 'unknown product' });
  db.prepare('UPDATE commission_levels SET amount = ? WHERE product_id = ? AND level = ?')
    .run(amount, product.id, Number(req.params.level));
  res.json({ ok: true });
});

// Admin: set a product's geo override (area/taluk/district).
app.put('/api/products/:code/geo/:geoLevel', (req, res) => {
  const { amount } = req.body || {};
  if (typeof amount !== 'number') return res.status(400).json({ error: 'amount must be a number' });
  const product = db.prepare('SELECT id FROM products WHERE code = ?').get(req.params.code);
  if (!product) return res.status(404).json({ error: 'unknown product' });
  db.prepare('UPDATE geo_levels SET amount = ? WHERE product_id = ? AND level = ?')
    .run(amount, product.id, req.params.geoLevel);
  res.json({ ok: true });
});

// Admin: settings (qualification gate, payout day).
app.get('/api/settings', (req, res) => res.json(db.prepare('SELECT * FROM settings').all()));
app.put('/api/settings/:key', (req, res) => {
  const { value } = req.body || {};
  if (typeof value !== 'number') return res.status(400).json({ error: 'value must be a number' });
  const info = db.prepare('UPDATE settings SET value = ? WHERE key = ?').run(value, req.params.key);
  if (info.changes === 0) return res.status(404).json({ error: 'unknown setting' });
  res.json({ ok: true });
});

const PORT = process.env.PORT || 4000;
if (require.main === module) {
  app.listen(PORT, () => console.log(`API listening on http://localhost:${PORT}`));
}

module.exports = { app, db };
