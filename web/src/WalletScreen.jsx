import React, { useState } from 'react';
import './wallet.css';
import BottomNav from './BottomNav.jsx';
import {
  Bell,
  Avatar,
  Award,
  Statement,
  CheckCircle,
  Processing,
  Info,
  Filter,
  Search,
  Wallet,
} from './icons.jsx';

// Styled Wallet / Payouts screen, rendered from the `data` payload
// (GET /api/users/:id/wallet):
// {
//   totalPayoutsToDate, prestige: { level, nextLevel, percent },
//   pendingCommissions, nextSettlement: 'YYYY-MM-DD', verifyingCount,
//   transactions: [{ id, reference, date, method, amount, status }], // paid|processing|requested
// }

/* ---------- formatting helpers ---------- */

const grp = (n) => new Intl.NumberFormat('en-IN', { maximumFractionDigits: 0 }).format(Math.round(n));
const inr = (n) => '₹' + grp(n);
const fmtDate = (iso) =>
  new Date(iso + 'T00:00:00').toLocaleDateString('en-US', { month: 'short', day: '2-digit', year: 'numeric' });

// Reference numbers are stored like "PO-7201"; the mockup shows "#7201".
const refNo = (reference) => String(reference).replace(/^PO-/i, '');

/* ---------- per-status presentation ---------- */

const STATUS = {
  paid: { key: 'paid', label: 'PAID', Icon: CheckCircle },
  processing: { key: 'processing', label: 'PROCESSING', Icon: Processing },
  requested: { key: 'requested', label: 'REQUESTED', Icon: Processing },
};
const statusOf = (s) => STATUS[s] || STATUS.requested;

export default function WalletScreen({ data, userId, onNavigate, onChanged }) {
  const { totalPayoutsToDate, prestige, pendingCommissions, nextSettlement, verifyingCount, transactions } = data;

  const [requesting, setRequesting] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  const requestPayout = async () => {
    if (requesting) return;
    setErrorMsg('');
    setRequesting(true);
    try {
      const res = await fetch(`/api/users/${userId}/payouts`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: '{}',
      });
      if (!res.ok) throw new Error(`Request failed (${res.status})`);
      if (onChanged) onChanged();
    } catch (err) {
      setErrorMsg(err.message || 'Could not request payout');
      setTimeout(() => setErrorMsg(''), 4000);
    } finally {
      setRequesting(false);
    }
  };

  return (
    <div className="screen-page">
      <div className="screen-phone">
        {/* 1. Header */}
        <header className="wl-header">
          <div className="wl-header-left">
            <span className="wl-avatar"><Avatar size={40} /></span>
            <h1 className="wl-welcome">Welcome back</h1>
          </div>
          <button type="button" className="wl-bell" aria-label="Notifications">
            <Bell size={22} />
          </button>
        </header>

        {/* 2. Total payouts to date */}
        <section className="app-card wl-total-card">
          <p className="wl-total-label">Total Payouts to Date</p>
          <p className="wl-total-amount">
            <span className="wl-total-rupee">₹</span>{grp(totalPayoutsToDate)}
          </p>
          <div className="wl-actions">
            <button
              type="button"
              className="wl-btn wl-btn-primary"
              onClick={requestPayout}
              disabled={requesting}
            >
              <Wallet size={18} />
              <span>{requesting ? 'Requesting…' : 'Request Payout'}</span>
            </button>
            <button type="button" className="wl-btn wl-btn-outline">
              <Statement size={18} />
              <span>Statement</span>
            </button>
          </div>
          {errorMsg && <p className="wl-error" role="alert">{errorMsg}</p>}
        </section>

        {/* 3. Affiliate prestige */}
        <section className="app-card wl-prestige-card">
          <div className="wl-prestige-row">
            <span className="wl-medal"><Award size={24} /></span>
            <div className="wl-prestige-mid">
              <p className="wl-prestige-label">Affiliate Prestige Level</p>
              <p className="wl-prestige-level">{prestige.level}</p>
            </div>
          </div>
          {prestige.nextLevel && (
            <p className="wl-next-level">Next Level: {prestige.nextLevel}</p>
          )}
          <div className="wl-progress-track">
            <div className="wl-progress-fill" style={{ width: `${prestige.nextLevel ? prestige.percent : 100}%` }} />
          </div>
        </section>

        {/* 4. Pending commissions */}
        <section className="app-card wl-pending-card">
          <p className="wl-pending-label">Pending Commissions</p>
          <p className="wl-pending-amount">{inr(pendingCommissions)}</p>
          <p className="wl-pending-sentence">
            Next settlement scheduled for <strong>{fmtDate(nextSettlement)}</strong>.
          </p>
          <div className="wl-verifying">
            <Info size={16} />
            <span>Verifying {verifyingCount} recent sales</span>
          </div>
        </section>

        {/* 5. Transaction history */}
        <section className="app-card wl-history-card">
          <div className="wl-history-head">
            <h2 className="wl-history-title">Transaction History</h2>
            <div className="wl-history-tools">
              <button type="button" className="wl-tool-btn" aria-label="Filter"><Filter size={20} /></button>
              <button type="button" className="wl-tool-btn" aria-label="Search"><Search size={20} /></button>
            </div>
          </div>

          <ul className="wl-tx-list">
            {transactions.map((t) => {
              const s = statusOf(t.status);
              return (
                <li key={t.id} className="wl-tx-row">
                  <span className={`wl-tx-chip wl-chip--${s.key}`}><s.Icon size={22} /></span>
                  <div className="wl-tx-mid">
                    <p className="wl-tx-ref">Payout #{refNo(t.reference)}</p>
                    <p className="wl-tx-meta">{fmtDate(t.date)} • {t.method}</p>
                  </div>
                  <div className="wl-tx-right">
                    <p className="wl-tx-amount">{inr(t.amount)}</p>
                    <span className={`wl-tx-pill wl-pill--${s.key}`}>{s.label}</span>
                  </div>
                </li>
              );
            })}
          </ul>

          <button type="button" className="wl-load-more">Load Older Transactions</button>
        </section>

        <BottomNav active="wallet" onChange={onNavigate} />
      </div>
    </div>
  );
}
