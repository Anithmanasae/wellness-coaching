# WhatsApp ad leads → Log Book sheet → Meta Conversions API

What this does:

1. Someone taps your click-to-WhatsApp ad and sends you a message.
2. A small free web service (Cloudflare Worker) receives the message from Meta and adds a row to the **Ad Leads** tab of the Log Book sheet, with the ad's click ID.
3. You change the row's **Status**:
   - **Qualified**, **Proposal sent** or **Won** → the sheet sends **LeadSubmitted** to Meta.
   - **Won** with a **Deal value** → the sheet also sends **Purchase** (₹ value) to Meta.

Meta then knows which ad chats became real leads and sales, and can find more people like them.

**Cost:** no monthly fee. Cloudflare Workers and Google Apps Script are free at this size. WhatsApp replies to people who message you from an ad are free.

---

## Part A: Meta setup (needs your Meta logins)

1. **Check that your number can use the Cloud API without leaving your phone.**
   In WhatsApp Manager (business.facebook.com → WhatsApp accounts), look for the option to connect your existing **WhatsApp Business app** number to the Cloud API ("coexistence"). If it's offered, use it: you keep replying from your phone as usual. If it isn't offered for your number, stop here and decide before going further, because moving the number fully to the API changes how you reply.
2. **Create a Meta app** at developers.facebook.com → My Apps → Create app → type **Business**. Add the **WhatsApp** product and link your WhatsApp Business account.
   Note down the **App Secret** (App settings → Basic).
3. **Get a Conversions API access token.** Events Manager → your dataset (**1547338533449042**) → Settings → Conversions API → **Generate access token**. Keep it private.
4. **Link the dataset to your WhatsApp Business account** if Events Manager asks you to (Settings → Connected assets).

## Part B: Google Sheet script

1. Open the **Log Book** sheet → **Extensions → Apps Script**.
2. Delete what's there and paste the contents of `sheet-script/Code.gs`. Save.
3. **Project Settings (gear) → Script properties**, add:
   | Property | Value |
   |---|---|
   | `DATASET_ID` | `1547338533449042` |
   | `ACCESS_TOKEN` | the token from Part A step 3 |
   | `SHARED_SECRET` | any long random text (also used in Part C) |
   | `GRAPH_VERSION` | the current Graph API version, e.g. `v23.0` |
   | `TEST_EVENT_CODE` | only while testing (see Part E) |
4. In the editor, choose **setupColumns** → Run (approve the permissions). This adds columns Q–V to Ad Leads.
5. Choose **installTrigger** → Run. This makes Status changes send events.
6. **Deploy → New deployment → Web app.** Execute as: **Me**. Who has access: **Anyone**. Copy the **Web app URL** (ends in `/exec`).

## Part C: Webhook (Cloudflare Worker, free)

1. Sign up at cloudflare.com → **Workers & Pages → Create → Worker**.
2. Replace the code with `webhook/worker.js` and **Deploy**. Copy the worker URL.
3. Worker → **Settings → Variables and secrets**, add:
   | Name | Value |
   |---|---|
   | `VERIFY_TOKEN` | any random text |
   | `APP_SECRET` | App Secret from Part A step 2 (as a secret) |
   | `SHEET_URL` | Web app URL from Part B step 6 |
   | `SHARED_SECRET` | the same text as in Part B |

## Part D: Connect Meta to the webhook

Meta app → **WhatsApp → Configuration → Webhook → Edit**:
- **Callback URL:** the worker URL
- **Verify token:** the `VERIFY_TOKEN` text
- Click **Verify and save**, then **subscribe** to the **messages** field.

## Part E: Test before going live

1. Events Manager → dataset → **Test events** → copy the test code. Put it in the sheet script's `TEST_EVENT_CODE` property.
2. Message your WhatsApp number by tapping one of your **ads** (from a different phone). A new row should appear in **Ad Leads** with a Click to WhatsApp ID.
3. Set that row's Status to **Qualified**. Within seconds, **LeadSubmitted** should appear in Test events, and "Lead sent to Meta" gets a timestamp.
4. Set Status to **Won** and enter a Deal value. **Purchase** should appear in Test events.
5. If a cell gets a note saying "Meta rejected the event", read the reason in the note.
6. When it works, **delete** the `TEST_EVENT_CODE` property so real events count.

## Day-to-day use

- New ad chats appear in **Ad Leads** automatically. Fill in business type, city and so on as usual.
- Change **Status** as the chat moves. Use **Qualified** only for real business owners with a need and a budget: that's what Meta learns from.
- Rows without a click ID (for example, leads you add by hand) are matched by the **WhatsApp number** column instead: the script sends Meta a hashed copy of the number with a **Lead** / **Purchase** event. Fill in the number with country code if it isn't Indian (e.g. 971...); 10-digit numbers are treated as Indian.
- Missed something? In Apps Script, run **processAllRows** to send anything not yet sent.

## Files

| File | What it is |
|---|---|
| `webhook/worker.js` | Cloudflare Worker that receives WhatsApp webhooks and forwards ad leads to the sheet |
| `webhook/worker.test.mjs` | Tests: `node --test whatsapp-conversions/webhook/worker.test.mjs` |
| `webhook/wrangler.toml` | Config if you deploy with the Wrangler command line instead of the dashboard |
| `sheet-script/Code.gs` | Apps Script for the Log Book sheet |

The code has been tested against sample WhatsApp messages and a mock sheet, not yet against your live Meta account. Part E is the real check.
