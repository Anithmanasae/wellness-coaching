# Notes for Claude

## Ad leads and sales log (Anith's Meta ads)

When Anith reports a lead or a sale from an ad, update the **Log Book** Google Sheet:
https://docs.google.com/spreadsheets/d/1E-ngMqRAGNSj4oVXtZIqz3vHwdzUu8NBT4OaJMkngf8/edit

**Ad Leads** tab, one row per person:
- A Lead date · B Name · C WhatsApp number · D Business type · E City · F Age range
- G Campaign: must match the campaign name in the **Ad Campaigns** tab exactly, or the totals there miss it
- H Needs · I Budget they stated · J Ad placement
- K Status: New / Qualified / Proposal sent / Won / Lost
- L Deal value (₹, Won only) · M Sale date · N Follow-up date · O Notes
- P Uploaded to Meta? and Q–V are filled by the sheet script. Don't edit them.

Rules:
- Write phone numbers as text with a leading apostrophe, e.g. `'+91 98765 43210`. A bare `+91 …` turns into a formula error.
- If the person already has a row (same number), update that row. Don't add a second one.
- Log every serious chat, not just sales. Qualified leads are what Meta learns from.
- Add a new campaign to the **Ad Campaigns** tab when a new ad starts (dates, spend, chats from Ads Manager).
- The sheet's Apps Script sends Lead/Purchase events to Meta (dataset 1547338533449042) by itself. Hand edits trigger it at once; edits made through the API are picked up by an hourly run. Never send events to Meta yourself, or they will be counted twice.

Code: `whatsapp-conversions/` (see its README).
