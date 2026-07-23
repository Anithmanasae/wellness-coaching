# Wellness Coaching — Network Marketing Platform

A commission platform for a wellness coach's network marketing team, plus the
advocate-facing mobile home screen.

## The commission model

Money is awarded on exactly one event — a **purchase** — and every rupee is
written to the `commissions` ledger (never recomputed). Registering a new
affiliate is itself a purchase of the ₹250 **Registration** product.

Each purchase generates three kinds of commission:

### 1. 12-level upline payouts (fixed ₹ per level, per product)

When someone buys, a **fixed rupee amount** flows up their sponsorship chain:
**L-1 = the direct sponsor, L-2 = the sponsor's sponsor, … up to L-12.** The
buyer earns nothing on their own purchase. The amounts differ per product:

| Level | Reg. 250 | P1 5k | P2 10k | P3 25k | P4 1L | P5 1.5L | P6 11k | P7 4990 |
|---|--:|--:|--:|--:|--:|--:|--:|--:|
| L-1 | 100 | 2000 | 3000 | 10000 | 35000 | 51000 | 1500 | 1010 |
| L-2 | 5 | 350 | 1000 | 1000 | 4000 | 8000 | 300 | 300 |
| L-3 | 5 | 150 | 500 | 800 | 2000 | 3500 | 100 | 100 |
| L-4 | 5 | 50 | 300 | 500 | 1000 | 2000 | 100 | 100 |
| L-5 | 5 | 50 | 300 | 200 | 500 | 1000 | 100 | 100 |
| L-6 | 5 | 30 | 100 | 100 | 500 | 600 | 50 | 50 |
| L-7 | 5 | 30 | 100 | 100 | 200 | 300 | 50 | 50 |
| L-8 | 5 | 30 | 100 | 100 | 200 | 200 | 50 | 20 |
| L-9 | 5 | 30 | 100 | 100 | 150 | 200 | 50 | 20 |
| L-10 | 5 | 30 | 100 | 100 | 150 | 100 | 50 | 20 |
| L-11 | 5 | 25 | 100 | 100 | 150 | 100 | 50 | 20 |
| L-12 | 5 | 25 | 100 | 100 | 150 | 100 | 50 | 20 |

### 2. Geographic overrides

On each **Registration**, ₹100 goes to the **pincode (area) holder**, ₹100 to
the **taluk holder**, and ₹100 to the **district holder** of the joiner's area.
Package geo overrides default to ₹0 (set them per product when the coach
provides the numbers — see `geo_levels`). Geo overrides are **not** subject to
the qualification gate: the holder paid for the territory.

### 3. Territory grants

Territory rights are earned by buying a package: **Package 3 (₹25k)** makes the
buyer the protected **PIN-code** holder for their pincode, and **Package 5
(₹1.5L)** makes them the **Taluk** holder for their taluk. A territory is
protected — once claimed, a later buyer does not displace the holder. District
holders are assigned by the coach (admin), as there is no district package.

## The two hard rules

- **No compression.** Only actual ancestors are paid. If the chain is shorter
  than 12, or a level's ancestor doesn't qualify, that payout is **forfeited**
  (retained by the company) — never rolled up to someone else.
- **Qualification gate** (`settings.qualification_gate`, default ON). An upline
  earns a level's payout only if they own a package of **equal-or-higher tier**
  than the product purchased. Tiers, low → high: Registration < P7 < P1 < P2 <
  P6 < P3 < P4 < P5. Example: a sponsor who only registered (tier 0) forfeits
  the ₹51,000 L-1 on a Package 5 sale. Turn the gate off to pay everyone
  regardless of tier: `PUT /api/settings/qualification_gate {"value": 0}`.

**Every number above is data, not code** — products, the 12-level tables, geo
overrides, ranks and settings all live in tables and are editable via the API.

## Ranks (cosmetic)

The advocate badge on the home screen (Bronze → Silver → Gold → Platinum →
Diamond) is earned by **conversions** — purchases the advocate's direct
recruits make. It is purely gamification and does **not** affect payouts, since
this plan pays fixed amounts by level.

## Geography

`pincodes` maps each pincode to an area, taluk and district. Seeded for
Bengaluru Urban and its 5 taluks (Bangalore North, Bangalore South, Bangalore
East, Yelahanka, Anekal).

## Referral tracking & sale attribution

Affiliates promote a link that points at **this app**, not directly at the
course site, so sales can be traced back to them:

1. **Share** — an affiliate's link is `{REFERRAL_BASE}{code}`, where `code` is
   their personal `referral_code` or a campaign slug (e.g.
   `premium-wellness.club/ref/jessica`).
2. **Redirect** — a visitor opens it → `GET /ref/:code` records a click and
   **302-redirects to the coach's course page** (`COURSE_URL`) with `?ref=<code>`
   appended so the code survives to checkout.
3. **Attribute** — when the sale completes, the coach's site posts back to
   `POST /api/conversions` (header `X-Webhook-Secret: <CONVERSION_SECRET>`) with
   `{ ref, productCode, externalOrderId, customerName?, customerEmail?, pincode? }`.
   We resolve the referrer, attach the buyer as a node **under them**, and fire
   the full commission cascade (upline levels + geo overrides + qualification
   gate). Idempotent on `externalOrderId`, so a retried webhook never double-pays.

## Payouts require coach approval

`request → (coach) approve → (coach) settle → paid`, or `reject`. Requesting
reserves the affiliate's balance (`requested`) but pays nothing until the coach
approves and settles; rejecting releases it. See `POST /api/users/:id/payouts`
and the coach actions `POST /api/payouts/:id/{approve,settle,reject}`.

## Database drivers

The app runs on either driver through one async adapter (`src/adapter.js`):

- **SQLite** (default) — zero setup, great for dev and the test suite.
- **PostgreSQL** — production. Set `DB_DRIVER=pg` and `DATABASE_URL`.

The schema is generated per-dialect and the full test suite passes on both.
See `server/.env.example` for all environment variables.

## Repo layout

```
server/   Express API + commission engine (dual-driver: SQLite | Postgres)
  src/adapter.js    async DB adapter (SQLite + Postgres), placeholder + tx handling
  src/db.js         dialect-aware schema + the coach's plan (products, tables, settings)
  src/engine.js     recordPurchase / registerAffiliate — the only money paths
  src/referral.js   link resolution, click tracking, sale attribution
  src/dashboard.js  src/links.js  src/wallet.js  src/leaderboard.js   read-models
  src/index.js      HTTP API
  src/seed.js       demo data (Jessica's team), runs on either driver
  test/             engine / wallet / referral tests (node --test)
web/      Vite + React advocate app (Home, Links, Wallet, Leaderboard tabs)
```

## Run it

```bash
# --- API on SQLite (default, no setup) ---
cd server && npm install && node src/seed.js && node src/index.js

# --- API on Postgres ---
export DB_DRIVER=pg DATABASE_URL=postgres://user:pass@host:5432/dbname
node src/seed.js && node src/index.js

# --- Web app (port 5173, proxies /api to :4000) ---
cd web && npm install && npx vite
```

Open http://localhost:5173 — Jessica's four tabs (demo user id 3). Every figure
is computed by the engine from the seeded team, not hardcoded.

## Tests

```bash
cd server && node --test test/*.test.js                              # SQLite
DB_DRIVER=pg DB_RESET=1 DATABASE_URL=... node --test test/*.test.js  # Postgres
```

## API

| Method | Path | Purpose |
|---|---|---|
| GET | `/ref/:code` | Referral redirect → records click, forwards to course page |
| POST | `/api/conversions` | Sale postback (secured) → attributes sale + fires commissions |
| POST | `/api/affiliates` | Register affiliate `{name, pincode, sponsorId?}` |
| POST | `/api/purchases` | Package purchase `{buyerId, productCode}` |
| GET | `/api/users/:id/dashboard` | Home payload |
| GET | `/api/users/:id/links` | Links & Creatives payload (share URLs + campaign stats) |
| POST | `/api/users/:id/links` | Create a campaign link |
| GET | `/api/users/:id/wallet` | Wallet payload |
| POST | `/api/users/:id/payouts` | Affiliate requests a payout (awaits approval) |
| GET | `/api/payouts?status=requested` | Coach: pending payout queue |
| POST | `/api/payouts/:id/{approve,settle,reject}` | Coach: act on a payout |
| GET | `/api/leaderboard?me=:id` | Standings + your rank |
| GET | `/api/users/:id/commissions` | Commission ledger |
| GET | `/api/products` | Catalogue with 12-level and geo payout tables |
| GET | `/api/pincodes/:pincode/holders` | Resolve area/taluk/district holders |
| PUT | `/api/products/:code/levels/:level` | Tune a level payout `{amount}` |
| PUT | `/api/products/:code/geo/:geoLevel` | Set a geo override `{amount}` |
| GET/PUT | `/api/settings` `/api/settings/:key` | View / tune gate and payout day |
