# How to test the app

## 1. Run it (two terminals)

You need Node 18+ installed.

**Terminal A — the API + database (SQLite, zero setup):**
```bash
cd server
npm install
node src/seed.js      # creates the demo data (safe to re-run anytime to reset)
node src/index.js     # API on http://localhost:4000
```

**Terminal B — the web app:**
```bash
cd web
npm install
npx vite              # opens http://localhost:5173
```

Open **http://localhost:5173** in your browser.

## 2. Log in

Two demo accounts (buttons on the login screen fill them in for you):

| Role | Email | Password |
|---|---|---|
| **Wellness Coach** | `coach@epiclife.academy` | `coach123` |
| **Affiliate (Jessica)** | `jessica@example.com` | `jessica123` |

The app routes you automatically: coach → coach app, affiliate → affiliate app.
Tap the **avatar (top-left)** to sign out and switch accounts.

## 3. Affiliate side (log in as Jessica)

- **Home tab** — total earned this month, link clicks, conversions, next payout, rank progress, recent conversions. All computed from real data.
- **Links tab** — your referral link + campaign links with click/conversion stats.
  - Tap **Copy Link** → it copies your link to the clipboard (button shows "Copied!").
- **Wallet tab** — total paid, prestige level, pending commissions, transaction history.
  - Tap **Request Payout** → creates a request; the button changes to **"Awaiting Approval"**. (The coach approves it — see below.)
- **Leaderboard tab** — podium of top advocates, standings, and your rank.

## 4. Coach side (log in as Coach Varadarajan)

- **Dashboard** — total network sales, active affiliates, pending payouts, top affiliates.
  - Tap **Approve Payouts** → jumps to the Payouts tab.
- **Affiliates tab** (people icon) — the full directory.
  - Type in the **search box** (e.g. "Elena", "London", "Nutrition") → the list filters live.
  - Tap the **tier chips** (Diamond / Platinum / Gold) → filters by tier.
- **Payouts tab** (money icon) — the approval queue.
  - Tap **Approve** on a request → it moves to "processing" (a **Mark Paid** button appears).
  - Tap **Mark Paid** → it settles; that affiliate's balance is paid.
  - Tap **Reject** → the request is declined and the affiliate's balance is released.
- **Library tab** (folder) — stub (creatives library, designed later).

**End-to-end payout test:** log in as Jessica → Wallet → Request Payout. Sign out,
log in as the Coach → Payouts → you'll see Jessica's request → Approve → Mark Paid.
Sign back in as Jessica → Wallet → it now shows as paid.

## 5. Test the referral → sale attribution (the core money flow)

This proves a sale on the coach's website is traced back to the affiliate and
pays the whole upline. Run these in a terminal while the API is up:

```bash
# (a) A visitor opens Jessica's link -> records a click, redirects to the course site
curl -i "http://localhost:4000/ref/jessica"
#     -> HTTP 302, Location: https://epiclife.academy/course.asp?ref=jessica

# (b) The course site reports a completed sale (₹10,000 Advanced Course)
curl -X POST http://localhost:4000/api/conversions \
  -H 'Content-Type: application/json' \
  -H 'X-Webhook-Secret: dev-secret' \
  -d '{"ref":"jessica","productCode":"P2","externalOrderId":"TEST-1",
       "customerName":"Test Buyer","customerEmail":"test@buyer.com","pincode":"560001"}'
#     -> shows Jessica earning L-1 ₹3,000 and her sponsor L-2 ₹1,000

# (c) Re-run (b) exactly -> returns {"duplicate":true} and does NOT pay again
```

Then refresh Jessica's **Home** tab in the browser — her earnings and conversions
went up. Product codes: `REG, P1, P2, P3, P4, P5, P6, P7`.

## 6. Run the automated tests

```bash
cd server
node --test test/*.test.js      # 22 tests: commission engine, payouts, referral
```

## 7. (Optional) Run on PostgreSQL instead of SQLite

```bash
export DB_DRIVER=pg DATABASE_URL=postgres://user:pass@host:5432/dbname
node src/seed.js && node src/index.js
```
Everything behaves identically; the test suite passes on both.

## Reset the demo data anytime
```bash
cd server && node src/seed.js
```
