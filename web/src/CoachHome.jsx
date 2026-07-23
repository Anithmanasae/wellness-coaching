import React from 'react';
import './coach-home.css';
import CoachBottomNav from './CoachBottomNav.jsx';
import { Bell, Avatar, People, Banknote } from './icons.jsx';

// Coach Dashboard — styled from the `data` payload (GET /api/coach/overview):
// {
//   coachName, totalNetworkSales, activeAffiliates,
//   pendingPayoutsTotal, pendingPayoutsCount, payoutDueInDays,
//   topAffiliates: [{ id, name, tier, earnings }],
// }
// onNavigate(tab) switches coach tabs ('payouts' for Approve Payouts).

const inr = (n) =>
  '₹' + new Intl.NumberFormat('en-IN', { maximumFractionDigits: 0 }).format(Math.round(n));

// Small filled star used for the #1 affiliate badge (no Star export in icons.jsx).
function StarBadge({ size = 12 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M12 2.5l2.9 5.88 6.49.95-4.7 4.58 1.11 6.46L12 17.9l-5.8 3.05 1.1-6.46-4.69-4.58 6.49-.95z" />
    </svg>
  );
}

export default function CoachHome({ data, onNavigate, onLogout }) {
  const {
    coachName,
    totalNetworkSales,
    activeAffiliates,
    pendingPayoutsTotal,
    pendingPayoutsCount,
    payoutDueInDays,
    topAffiliates = [],
  } = data;

  return (
    <div className="screen-page">
      <div className="screen-phone">
        {/* 1. Header */}
        <header className="ch-header">
          <button
            type="button"
            className="ch-avatar"
            onClick={onLogout}
            aria-label="Account and sign out"
          >
            <Avatar size={44} />
          </button>
          <div className="ch-welcome">
            <span className="ch-welcome-line">Welcome back,</span>
            <span className="ch-coach-name">{coachName}</span>
          </div>
          <button type="button" className="ch-bell" aria-label="Notifications">
            <Bell size={22} />
          </button>
        </header>

        {/* 2. Total network sales */}
        <section className="app-card ch-total-card">
          <svg
            className="ch-wave"
            viewBox="0 0 220 160"
            preserveAspectRatio="none"
            aria-hidden="true"
          >
            <path
              d="M220 44C168 44 150 118 96 132S18 118 0 160H220Z"
              fill="rgba(30,42,35,0.05)"
            />
            <path
              d="M220 86C182 86 168 128 122 138S52 130 26 160H220Z"
              fill="rgba(30,42,35,0.045)"
            />
          </svg>
          <p className="ch-total-label">Total Network Sales</p>
          <p className="ch-total-amount">{inr(totalNetworkSales)}</p>
        </section>

        {/* 3. Stat cards */}
        <section className="ch-stats-grid">
          <div className="app-card ch-stat-card">
            <span className="ch-stat-chip ch-chip-stone">
              <People size={22} />
            </span>
            <p className="ch-stat-label">Active Affiliates</p>
            <p className="ch-stat-value">{activeAffiliates}</p>
          </div>
          <div className="app-card ch-stat-card">
            <span className="ch-stat-chip ch-chip-gold">
              <Banknote size={22} />
            </span>
            <p className="ch-stat-label">Pending Payouts</p>
            <p className="ch-stat-value ch-stat-value-gold">{inr(pendingPayoutsTotal)}</p>
          </div>
        </section>

        {/* 4. Payouts-due CTA */}
        <section className="ch-cta-card">
          <p className="ch-cta-headline">Payouts due in {payoutDueInDays} days.</p>
          <p className="ch-cta-sub">{pendingPayoutsCount} affiliates pending.</p>
          <button
            type="button"
            className="ch-cta-btn"
            onClick={() => onNavigate('payouts')}
          >
            Approve Payouts
          </button>
        </section>

        {/* 5. Top affiliates heading */}
        <h2 className="ch-section-heading">Top Affiliates</h2>

        {/* 6. Top affiliates list */}
        <ul className="ch-affiliate-list">
          {topAffiliates.map((a, i) => (
            <li key={a.id} className="app-card ch-affiliate-card">
              <span className="ch-affiliate-avatar">
                <Avatar size={44} />
                {i === 0 && (
                  <span className="ch-affiliate-star" aria-label="Top affiliate">
                    <StarBadge size={11} />
                  </span>
                )}
              </span>
              <div className="ch-affiliate-mid">
                <p className="ch-affiliate-name">{a.name}</p>
                <p className="ch-affiliate-tier">TIER: {a.tier.toUpperCase()}</p>
              </div>
              <p className="ch-affiliate-earnings">{inr(a.earnings)}</p>
            </li>
          ))}
        </ul>

        <CoachBottomNav active="home" onChange={onNavigate} />
      </div>
    </div>
  );
}
