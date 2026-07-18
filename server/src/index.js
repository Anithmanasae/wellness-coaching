const express = require('express');
const { createDb } = require('./db');
const { registerAffiliate, recordSale, managersForPincode } = require('./engine');
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

// New affiliate joins (triggers geo join bonuses).
app.post('/api/affiliates', (req, res) => {
  const { name, email, phone, pincode, sponsorId } = req.body || {};
  if (!name || !pincode) return res.status(400).json({ error: 'name and pincode are required' });
  try {
    const id = registerAffiliate(db, { name, email, phone, pincode, sponsorId });
    res.status(201).json({ id });
  } catch (err) {
    res.status(400).json({ error: err.message });
  }
});

// Record a sale (triggers personal, downline and geo commissions).
app.post('/api/sales', (req, res) => {
  const { sellerId, productId, customerName, amount } = req.body || {};
  if (!sellerId || !productId) return res.status(400).json({ error: 'sellerId and productId are required' });
  try {
    const id = recordSale(db, { sellerId, productId, customerName, amount });
    res.status(201).json({ id });
  } catch (err) {
    res.status(400).json({ error: err.message });
  }
});

// Track a link click for an affiliate's referral link.
app.post('/api/users/:id/clicks', (req, res) => {
  db.prepare('INSERT INTO link_clicks (user_id) VALUES (?)').run(Number(req.params.id));
  res.status(201).json({ ok: true });
});

// Commission ledger for a user.
app.get('/api/users/:id/commissions', (req, res) => {
  const rows = db
    .prepare('SELECT * FROM commissions WHERE user_id = ? ORDER BY created_at DESC, id DESC LIMIT 100')
    .all(Number(req.params.id));
  res.json(rows);
});

// Who manages a pincode (debug/admin helper).
app.get('/api/pincodes/:pincode/managers', (req, res) => {
  res.json(managersForPincode(db, req.params.pincode));
});

// Admin: view and tune every commission rate.
app.get('/api/rules', (req, res) => {
  res.json(db.prepare('SELECT * FROM commission_rules ORDER BY key').all());
});
app.put('/api/rules/:key', (req, res) => {
  const { value } = req.body || {};
  if (typeof value !== 'number') return res.status(400).json({ error: 'value must be a number' });
  const info = db
    .prepare('UPDATE commission_rules SET value = ? WHERE key = ?')
    .run(value, req.params.key);
  if (info.changes === 0) return res.status(404).json({ error: 'unknown rule' });
  res.json({ ok: true });
});

const PORT = process.env.PORT || 4000;
app.listen(PORT, () => console.log(`API listening on http://localhost:${PORT}`));
