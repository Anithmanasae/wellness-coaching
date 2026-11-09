// Run with: node --test whatsapp-conversions/webhook/worker.test.mjs
import { test } from "node:test";
import assert from "node:assert/strict";
import { createHmac } from "node:crypto";
import worker, { extractAdLeads, isValidSignature } from "./worker.js";

const SECRET = "test-app-secret";

const adMessage = {
  object: "whatsapp_business_account",
  entry: [{
    id: "WABA123",
    changes: [{
      field: "messages",
      value: {
        contacts: [{ wa_id: "919876543210", profile: { name: "Ravi" } }],
        messages: [{
          from: "919876543210",
          id: "wamid.1",
          timestamp: "1762700000",
          type: "text",
          text: { body: "Hi, I need an app" },
          referral: {
            source_url: "https://fb.me/x",
            source_id: "120251830492340183",
            source_type: "ad",
            headline: "Your business has grown",
            ctwa_clid: "ARAkLkA8rmlFeiCktEJQ",
          },
        }],
      },
    }],
  }],
};

const normalMessage = structuredClone(adMessage);
delete normalMessage.entry[0].changes[0].value.messages[0].referral;

function sign(body) {
  return "sha256=" + createHmac("sha256", SECRET).update(body).digest("hex");
}

test("extracts a lead from an ad message", () => {
  const leads = extractAdLeads(adMessage);
  assert.equal(leads.length, 1);
  assert.deepEqual(leads[0], {
    wabaId: "WABA123",
    phone: "919876543210",
    name: "Ravi",
    ctwaClid: "ARAkLkA8rmlFeiCktEJQ",
    adId: "120251830492340183",
    headline: "Your business has grown",
    timestamp: 1762700000,
  });
});

test("ignores messages that did not come from an ad", () => {
  assert.equal(extractAdLeads(normalMessage).length, 0);
  assert.equal(extractAdLeads({}).length, 0);
});

test("signature check accepts Meta's signature and rejects others", async () => {
  const body = JSON.stringify(adMessage);
  assert.equal(await isValidSignature(body, sign(body), SECRET), true);
  assert.equal(await isValidSignature(body, sign(body + "x"), SECRET), false);
  assert.equal(await isValidSignature(body, "", SECRET), false);
});

test("GET verification echoes the challenge only with the right token", async () => {
  const env = { VERIFY_TOKEN: "abc" };
  const ok = await worker.fetch(new Request("https://w.dev/?hub.mode=subscribe&hub.verify_token=abc&hub.challenge=42"), env);
  assert.equal(ok.status, 200);
  assert.equal(await ok.text(), "42");
  const bad = await worker.fetch(new Request("https://w.dev/?hub.mode=subscribe&hub.verify_token=no&hub.challenge=42"), env);
  assert.equal(bad.status, 403);
});

test("POST forwards ad leads to the sheet and rejects unsigned requests", async () => {
  const sent = [];
  const realFetch = globalThis.fetch;
  globalThis.fetch = async (url, init) => { sent.push({ url, body: JSON.parse(init.body) }); return new Response("ok"); };
  try {
    const env = { APP_SECRET: SECRET, SHEET_URL: "https://script.google.com/x/exec", SHARED_SECRET: "s3" };
    const body = JSON.stringify(adMessage);
    const res = await worker.fetch(new Request("https://w.dev/", { method: "POST", body, headers: { "x-hub-signature-256": sign(body) } }), env);
    assert.equal(res.status, 200);
    assert.equal(sent.length, 1);
    assert.equal(sent[0].body.secret, "s3");
    assert.equal(sent[0].body.lead.ctwaClid, "ARAkLkA8rmlFeiCktEJQ");

    const unsigned = await worker.fetch(new Request("https://w.dev/", { method: "POST", body }), env);
    assert.equal(unsigned.status, 401);
    assert.equal(sent.length, 1);
  } finally {
    globalThis.fetch = realFetch;
  }
});
