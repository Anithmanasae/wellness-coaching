import React, { useState } from 'react';
import './coach-payouts.css';
import CoachBottomNav from './CoachBottomNav.jsx';
import { Bell, Avatar, Banknote, CheckCircle, Processing, Info, Lock } from './icons.jsx';

// Payout Approvals — the coach's review queue, styled from `data`
// (GET /api/coach/payouts):
// [{ id, reference, amount, method, status, date, affiliate: { id, name, tier } }]
//   status: 'requested' -> Approve / Reject | 'processing' -> Mark Paid
// onAction(payoutId, 'approve'|'reject'|'settle') is async; the parent
// refetches on resolve, so the acted-on row disappears/changes next render.

/* ---------- formatting helpers ---------- */

const inr = (n) => '₹' + new Intl.NumberFormat('en-IN', { maximumFractionDigits: 0 }).format(Math.round(n));
const fmtDate = (iso) =>
  new Date(iso + 'T00:00:00').toLocaleDateString('en-US', { month: 'short', day: '2-digit', year: 'numeric' });

// Reference numbers are stored like "PO-7201"; we show "#7201".
const refNo = (reference) => String(reference).replace(/^PO-/i, '');

/* ---------- a caution "reject" glyph, matching the shared icon language ---------- */

function XMark({ size = 18 }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M6 6l12 12" />
      <path d="M18 6L6 18" />
    </svg>
  );
}

const Spinner = () => (
  <span className="cp-spin"><Processing size={18} /></span>
);

export default function CoachPayouts({ data, onAction, onNavigate, onLogout }) {
  // Per-row in-flight state: { id, action } while an approval is being sent.
  const [busy, setBusy] = useState(null);

  const rows = Array.isArray(data) ? data : [];
  const requested = rows.filter((p) => p.status === 'requested');
  const requestedTotal = requested.reduce((sum, p) => sum + p.amount, 0);

  const busyOn = (id, action) => busy && busy.id === id && (!action || busy.action === action);

  const act = async (id, action) => {
    if (busy) return; // one approval at a time
    setBusy({ id, action });
    try {
      await onAction(id, action);
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="screen-page">
      <div className="screen-phone">
        {/* 1. Header */}
        <header className="cp-header">
          <div className="cp-header-left">
            <span className="cp-avatar"><Avatar size={40} /></span>
            <h1 className="cp-title">Payout Approvals</h1>
          </div>
          <button type="button" className="cp-bell" aria-label="Notifications">
            <Bell size={22} />
          </button>
        </header>

        {rows.length === 0 ? (
          /* 4. Empty state */
          <div className="cp-empty">
            <span className="cp-empty-chip"><CheckCircle size={38} /></span>
            <h2 className="cp-empty-title">All caught up</h2>
            <p className="cp-empty-text">No payout requests are waiting for approval.</p>
          </div>
        ) : (
          <>
            {/* 2. Summary strip */}
            <section className="cp-summary">
              <div className="cp-summary-left">
                <p className="cp-summary-count">{requested.length}</p>
                <p className="cp-summary-label">Awaiting approval</p>
              </div>
              <div className="cp-summary-right">
                <p className="cp-summary-total-label">Requested total</p>
                <p className="cp-summary-total">{inr(requestedTotal)}</p>
              </div>
            </section>

            {/* 3. Approval queue */}
            <ul className="cp-list">
              {rows.map((p) => {
                const isRequested = p.status === 'requested';
                const rowBusy = busyOn(p.id);
                return (
                  <li key={p.id} className={`app-card cp-row${rowBusy ? ' cp-row--busy' : ''}`}>
                    <div className="cp-row-top">
                      <span className="cp-row-avatar"><Avatar size={46} /></span>
                      <div className="cp-row-mid">
                        <p className="cp-row-name">{p.affiliate.name}</p>
                        <p className="cp-row-sub">{p.affiliate.tier} • Payout #{refNo(p.reference)}</p>
                      </div>
                      <p className="cp-row-amount">{inr(p.amount)}</p>
                    </div>

                    <div className="cp-row-meta">
                      <span className="cp-row-metatext">{fmtDate(p.date)} • {p.method}</span>
                      <span className={`cp-pill cp-pill--${p.status}`}>
                        {isRequested ? 'Requested' : 'Processing'}
                      </span>
                    </div>

                    {isRequested ? (
                      <div className="cp-actions">
                        <button
                          type="button"
                          className="cp-btn cp-btn-approve"
                          disabled={rowBusy}
                          onClick={() => act(p.id, 'approve')}
                        >
                          {busyOn(p.id, 'approve') ? <Spinner /> : <CheckCircle size={18} />}
                          <span>Approve</span>
                        </button>
                        <button
                          type="button"
                          className="cp-btn cp-btn-reject"
                          disabled={rowBusy}
                          onClick={() => act(p.id, 'reject')}
                        >
                          {busyOn(p.id, 'reject') ? <Spinner /> : <XMark size={18} />}
                          <span>Reject</span>
                        </button>
                      </div>
                    ) : (
                      <div className="cp-actions cp-actions--single">
                        <button
                          type="button"
                          className="cp-btn cp-btn-pay"
                          disabled={rowBusy}
                          onClick={() => act(p.id, 'settle')}
                        >
                          {rowBusy ? <Spinner /> : <Banknote size={18} />}
                          <span>Mark Paid</span>
                        </button>
                        <p className="cp-helper">
                          <Info size={14} />
                          <span>Approved — awaiting disbursement</span>
                        </p>
                      </div>
                    )}
                  </li>
                );
              })}
            </ul>

            {/* Trust footer */}
            <p className="cp-secure">
              <Lock size={12} />
              <span>Every approval is verified and securely logged</span>
            </p>
          </>
        )}

        <CoachBottomNav active="payouts" onChange={onNavigate} />
      </div>
    </div>
  );
}
