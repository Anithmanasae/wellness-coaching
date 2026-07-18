# Wellness Coaching — Network Marketing Platform

A commission platform for a wellness coach's network marketing team, plus the
advocate-facing mobile home screen.

## Business model

Money is awarded on exactly two events, and every rupee is written to the
`commissions` ledger table (nothing is ever recomputed):

### 1. A sale is recorded

| Who earns | What | Default rate |
|---|---|---|
| The seller | Personal commission at their **rank** rate | Bronze 20% / Silver 22% / Gold 25% / Platinum 30% |
| Their recruiter (upline level 1) | Downline override | 10% |
| Their recruiter's recruiter (level 2) | Downline override | 5% |
| Area manager of the seller's **pincode** | Geo override | 3% |
| Taluk manager of the seller's taluk | Geo override | 2% |
| District manager of the seller's district | Geo override | 1% |

### 2. A new affiliate joins

| Who earns | What | Default |
|---|---|---|
| Area manager of the new affiliate's pincode | Flat join bonus | ₹100 |
| Taluk manager | Flat join bonus | ₹50 |
| District manager | Flat join bonus | ₹25 |

Rules:
- A territory manager never earns a geo override on their **own** sale, and no
  join bonus on their own registration.
- Downline overrides stop after 2 levels.
- Commissions accrue with status `locked` and are paid on the payout day
  (default: the 15th of each month), after which they are marked `paid`.
- Ranks are earned by lifetime personal sales (Silver at 5, Gold at 10,
  Platinum at 17) and are never lost.

**Every number above is data, not code** — see the `commission_rules` and
`ranks` tables. Tune them via `GET/PUT /api/rules/:key` without redeploying.

## Geography

`pincodes` maps each pincode to an area, a taluk and a district. Seeded for
Bengaluru Urban district and its 5 taluks (Bangalore North, Bangalore South,
Bangalore East, Yelahanka, Anekal). `territory_managers` assigns one manager
per territory per level; unassigned territories simply earn nothing.

## Repo layout

```
server/   Express + SQLite API and the commission engine
  src/db.js         schema + default rules/ranks
  src/engine.js     recordSale / registerAffiliate — the only money paths
  src/dashboard.js  home-screen aggregate payload
  src/index.js      HTTP API
  src/seed.js       demo data (Jessica's team, built through the real engine)
  test/             engine tests (node --test)
web/      Vite + React advocate app (mobile home screen)
```

## Run it

```bash
# API (port 4000)
cd server && npm install && node src/seed.js && node src/index.js

# Web app (port 5173, proxies /api to :4000)
cd web && npm install && npx vite
```

Open http://localhost:5173 — you'll see Jessica's dashboard (demo user id 4).

## Tests

```bash
cd server && node --test test/engine.test.js
```

## API

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/affiliates` | Register affiliate `{name, pincode, sponsorId?}` → fires join bonuses |
| POST | `/api/sales` | Record sale `{sellerId, productId, customerName?, amount?}` → fires all commissions |
| POST | `/api/users/:id/clicks` | Track a referral-link click |
| GET | `/api/users/:id/dashboard` | Home screen payload |
| GET | `/api/users/:id/commissions` | Commission ledger |
| GET | `/api/pincodes/:pincode/managers` | Resolve area/taluk/district managers |
| GET/PUT | `/api/rules` `/api/rules/:key` | View / tune commission rates |
