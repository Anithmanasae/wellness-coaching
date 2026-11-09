// Cloudflare Worker: receives WhatsApp Cloud API webhooks from Meta.
// For every message that came from a click-to-WhatsApp ad, it forwards the
// lead (phone, name, ad click ID, ad ID, headline) to the Google Sheet script.
//
// Settings (Cloudflare dashboard → Worker → Settings → Variables):
//   VERIFY_TOKEN   any random text; type the same text in Meta's webhook setup
//   APP_SECRET     your Meta app's App Secret (secret variable)
//   SHEET_URL      the Google Apps Script web app URL (ends in /exec)
//   SHARED_SECRET  random text; the same value goes in the sheet script

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    // 1. Meta checks the webhook URL once with a GET request.
    if (request.method === "GET") {
      const mode = url.searchParams.get("hub.mode");
      const token = url.searchParams.get("hub.verify_token");
      const challenge = url.searchParams.get("hub.challenge");
      if (mode === "subscribe" && token && token === env.VERIFY_TOKEN) {
        return new Response(challenge || "", { status: 200 });
      }
      return new Response("Forbidden", { status: 403 });
    }

    if (request.method !== "POST") {
      return new Response("Method not allowed", { status: 405 });
    }

    // 2. Every message arrives as a signed POST. Reject anything not signed by Meta.
    const body = await request.text();
    const signature = request.headers.get("x-hub-signature-256") || "";
    if (!(await isValidSignature(body, signature, env.APP_SECRET))) {
      return new Response("Invalid signature", { status: 401 });
    }

    let payload;
    try {
      payload = JSON.parse(body);
    } catch {
      return new Response("Bad JSON", { status: 400 });
    }

    const leads = extractAdLeads(payload);
    for (const lead of leads) {
      // Apps Script answers POSTs with a redirect; fetch follows it by default.
      await fetch(env.SHEET_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ secret: env.SHARED_SECRET, lead }),
      });
    }

    // Always answer 200 quickly, or Meta keeps retrying.
    return new Response("OK", { status: 200 });
  },
};

// Pulls out only messages that came from an ad (they carry a referral with ctwa_clid).
export function extractAdLeads(payload) {
  const leads = [];
  for (const entry of payload?.entry || []) {
    const wabaId = entry.id;
    for (const change of entry.changes || []) {
      const value = change.value || {};
      const names = {};
      for (const c of value.contacts || []) {
        names[c.wa_id] = c.profile?.name || "";
      }
      for (const msg of value.messages || []) {
        const ref = msg.referral;
        if (!ref || !ref.ctwa_clid) continue;
        leads.push({
          wabaId,
          phone: msg.from,
          name: names[msg.from] || "",
          ctwaClid: ref.ctwa_clid,
          adId: ref.source_id || "",
          headline: ref.headline || "",
          timestamp: Number(msg.timestamp) || Math.floor(Date.now() / 1000),
        });
      }
    }
  }
  return leads;
}

export async function isValidSignature(body, header, appSecret) {
  if (!appSecret || !header.startsWith("sha256=")) return false;
  const key = await crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(appSecret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  );
  const mac = await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(body));
  const expected = [...new Uint8Array(mac)].map((b) => b.toString(16).padStart(2, "0")).join("");
  const given = header.slice("sha256=".length);
  if (given.length !== expected.length) return false;
  let diff = 0;
  for (let i = 0; i < expected.length; i++) diff |= expected.charCodeAt(i) ^ given.charCodeAt(i);
  return diff === 0;
}
