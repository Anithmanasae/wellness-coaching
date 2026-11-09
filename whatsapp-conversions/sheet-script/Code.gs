/**
 * Google Apps Script for the "Log Book" sheet.
 *
 * 1. doPost: receives new ad leads from the webhook and adds a row to "Ad Leads".
 * 2. onStatusEdit: when a row's Status becomes Qualified / Proposal sent / Won,
 *    sends a lead event to Meta; when it is Won with a Deal value, sends Purchase.
 *    Rows from the webhook are matched by click ID; other rows by phone number.
 *
 * Script properties (Extensions → Apps Script → Project Settings → Script properties):
 *   DATASET_ID      1547338533449042  (from your Events Manager link)
 *   ACCESS_TOKEN    Conversions API access token from Events Manager
 *   SHARED_SECRET   same random text as the webhook's SHARED_SECRET
 *   GRAPH_VERSION   e.g. v23.0 (use the current Graph API version)
 *   TEST_EVENT_CODE optional; set while testing so events show in "Test events"
 */

const SHEET_NAME = 'Ad Leads';
const COL = {
  leadDate: 1, name: 2, phone: 3, campaign: 7, status: 11, dealValue: 12,
  saleDate: 13, notes: 15, uploaded: 16,
  ctwaClid: 17, adId: 18, headline: 19, wabaId: 20, leadSent: 21, purchaseSent: 22,
};
const EXTRA_HEADERS = ['Click to WhatsApp ID', 'Ad ID', 'Ad headline',
  'WhatsApp Business account ID', 'Lead sent to Meta', 'Purchase sent to Meta'];
const LEAD_STATUSES = ['Qualified', 'Proposal sent', 'Won'];

/** Run once: adds the extra columns this script needs. */
function setupColumns() {
  const sheet = getSheet_();
  sheet.getRange(1, COL.ctwaClid, 1, EXTRA_HEADERS.length).setValues([EXTRA_HEADERS])
    .setFontWeight('bold').setFontColor('#FFFFFF').setBackground('#1F4E78');
  sheet.getRange(2, COL.leadSent, sheet.getMaxRows() - 1, 2).setNumberFormat('dd-mmm-yyyy hh:mm');
}

/**
 * Run once: sends events when you edit Status or Deal value, and also checks
 * every hour (edits made by Claude or other tools don't fire the edit trigger).
 */
function installTrigger() {
  ScriptApp.getProjectTriggers()
    .filter(t => ['onStatusEdit', 'processAllRows'].indexOf(t.getHandlerFunction()) !== -1)
    .forEach(t => ScriptApp.deleteTrigger(t));
  ScriptApp.newTrigger('onStatusEdit').forSpreadsheet(SpreadsheetApp.getActive()).onEdit().create();
  ScriptApp.newTrigger('processAllRows').timeBased().everyHours(1).create();
}

/** Webhook → sheet: one new row per ad lead. */
function doPost(e) {
  const props = PropertiesService.getScriptProperties();
  let data;
  try {
    data = JSON.parse(e.postData.contents);
  } catch (err) {
    return text_('bad json');
  }
  if (!data || data.secret !== props.getProperty('SHARED_SECRET')) return text_('forbidden');
  const lead = data.lead || {};
  if (!lead.ctwaClid) return text_('no click id');

  const lock = LockService.getScriptLock();
  lock.waitLock(20000);
  try {
    const sheet = getSheet_();
    const last = sheet.getLastRow();
    if (last >= 2) {
      const ids = sheet.getRange(2, COL.ctwaClid, last - 1, 1).getValues().flat();
      if (ids.indexOf(lead.ctwaClid) !== -1) return text_('duplicate');
    }
    const row = new Array(COL.purchaseSent).fill('');
    row[COL.leadDate - 1] = new Date((lead.timestamp || Date.now() / 1000) * 1000);
    row[COL.name - 1] = lead.name || '';
    row[COL.phone - 1] = String(lead.phone || '');
    row[COL.status - 1] = 'New';
    row[COL.notes - 1] = lead.headline ? 'From ad: ' + lead.headline : 'From ad';
    row[COL.uploaded - 1] = 'No';
    row[COL.ctwaClid - 1] = lead.ctwaClid;
    row[COL.adId - 1] = String(lead.adId || '');
    row[COL.headline - 1] = lead.headline || '';
    row[COL.wabaId - 1] = String(lead.wabaId || '');
    sheet.getRange(last + 1, 1, 1, row.length).setValues([row]);
  } finally {
    lock.releaseLock();
  }
  return text_('ok');
}

/** Installable onEdit trigger: sends events when Status or Deal value changes. */
function onStatusEdit(e) {
  const range = e && e.range;
  if (!range || range.getSheet().getName() !== SHEET_NAME) return;
  const col = range.getColumn();
  if (col !== COL.status && col !== COL.dealValue) return;
  for (let r = range.getRow(); r < range.getRow() + range.getNumRows(); r++) {
    if (r >= 2) processRow_(range.getSheet(), r);
  }
}

/** Can also be run by hand from the Apps Script editor to resend anything missed. */
function processAllRows() {
  const lock = LockService.getScriptLock();
  if (!lock.tryLock(30000)) return;
  try {
    const sheet = getSheet_();
    for (let r = 2; r <= sheet.getLastRow(); r++) processRow_(sheet, r);
  } finally {
    lock.releaseLock();
  }
}

function processRow_(sheet, r) {
  const v = sheet.getRange(r, 1, 1, COL.purchaseSent).getValues()[0];
  const clid = v[COL.ctwaClid - 1];
  const waba = v[COL.wabaId - 1];
  const phone = normalizePhone_(v[COL.phone - 1]);
  const status = v[COL.status - 1];

  // Ad chats captured by the webhook carry a click ID (best match).
  // Everything else is matched by the customer's phone number (hashed).
  let base, key, leadName;
  if (clid && waba) {
    key = clid;
    leadName = 'LeadSubmitted';
    base = {
      action_source: 'business_messaging', messaging_channel: 'whatsapp',
      user_data: { whatsapp_business_account_id: String(waba), ctwa_clid: clid },
    };
  } else if (phone) {
    key = phone;
    leadName = 'Lead';
    base = {
      action_source: 'system_generated',
      user_data: { ph: [sha256_(phone)], country: [sha256_('in')] },
    };
  } else {
    return; // no click ID and no phone number: nothing Meta can match
  }

  if (LEAD_STATUSES.indexOf(status) !== -1 && !v[COL.leadSent - 1]) {
    const ev = Object.assign({}, base, { event_name: leadName, event_id: 'lead-' + key });
    if (leadName === 'Lead') ev.custom_data = { event_source: 'crm', lead_event_source: 'Log Book sheet' };
    record_(sheet, r, COL.leadSent, sendEvent_(ev));
  }

  const value = Number(String(v[COL.dealValue - 1]).replace(/[^0-9.]/g, ''));
  if (status === 'Won' && value > 0 && !v[COL.purchaseSent - 1]) {
    const res = sendEvent_(Object.assign({}, base, {
      event_name: 'Purchase',
      event_id: 'purchase-' + key,
      custom_data: { currency: 'INR', value: value, order_id: 'order-' + key },
    }));
    record_(sheet, r, COL.purchaseSent, res);
  }
}

/** Digits only, with India's 91 in front: "098765 43210" -> "919876543210". */
function normalizePhone_(raw) {
  let d = String(raw || '').replace(/\D/g, '').replace(/^0+/, '');
  if (d.length === 10) d = '91' + d;
  return d.length >= 11 ? d : '';
}

function sha256_(text) {
  return Utilities.computeDigest(Utilities.DigestAlgorithm.SHA_256, text, Utilities.Charset.UTF_8)
    .map(b => ('0' + (b & 0xff).toString(16)).slice(-2)).join('');
}

function sendEvent_(event) {
  const props = PropertiesService.getScriptProperties();
  const version = props.getProperty('GRAPH_VERSION') || 'v23.0';
  const url = 'https://graph.facebook.com/' + version + '/' + props.getProperty('DATASET_ID') + '/events';
  const payload = {
    data: [Object.assign({ event_time: Math.floor(Date.now() / 1000) }, event)],
    access_token: props.getProperty('ACCESS_TOKEN'),
  };
  const testCode = props.getProperty('TEST_EVENT_CODE');
  if (testCode) payload.test_event_code = testCode;
  const resp = UrlFetchApp.fetch(url, {
    method: 'post', contentType: 'application/json',
    payload: JSON.stringify(payload), muteHttpExceptions: true,
  });
  return { ok: resp.getResponseCode() === 200, body: resp.getContentText() };
}

function record_(sheet, r, col, res) {
  const cell = sheet.getRange(r, col);
  if (res.ok) {
    cell.setValue(new Date()).setNote('');
    sheet.getRange(r, COL.uploaded).setValue('Yes');
  } else {
    cell.setValue('').setNote('Meta rejected the event: ' + res.body.slice(0, 400));
  }
}

function getSheet_() {
  const sheet = SpreadsheetApp.getActive().getSheetByName(SHEET_NAME);
  if (!sheet) throw new Error('Tab "' + SHEET_NAME + '" not found');
  return sheet;
}

function text_(s) {
  return ContentService.createTextOutput(s);
}
