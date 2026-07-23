import React from 'react';
import './home.css';
import { Bell, CursorClick, TrendingUp, Lock, Person, Avatar } from './icons.jsx';
import BottomNav from './BottomNav.jsx';

// Styled home screen, rendered from the `dashboard` payload
// (GET /api/users/:id/dashboard):
// {
//   user: { id, name, rank },
//   totalEarnedThisMonth, linkClicks, conversions,
//   nextPayout: { amount, estimatedDate },
//   rankProgress: { currentRank, nextRank, salesToNext, percent } | null,
//   recentConversions: [{ id, name, label, amount }],
// }

/* ---------- formatting helpers ---------- */

function formatIntINR(value) {
  return new Intl.NumberFormat('en-IN', { maximumFractionDigits: 0 }).format(Math.trunc(Math.abs(value)));
}

function formatAmountINR(value) {
  return new Intl.NumberFormat('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(value);
}

function decimalsSuffix(value) {
  return Math.round((Math.abs(value) % 1) * 100).toString().padStart(2, '0');
}

const MONTHS = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC'];

function parseISODate(iso) {
  const [, m, d] = String(iso).split('-');
  return { month: MONTHS[Number(m) - 1] || '', day: String(Number(d) || '') };
}

export default function HomeScreen({ dashboard, onNavigate }) {
  const { user, totalEarnedThisMonth, linkClicks, conversions, nextPayout, rankProgress, recentConversions } = dashboard;
  const payoutDate = parseISODate(nextPayout.estimatedDate);

  return (
    <div className="screen-page">
      <div className="screen-phone">
        {/* 1. Header */}
        <header className="hs-header">
          <div className="hs-header-left">
            <h1 className="hs-greeting">Hello, {user.name}!</h1>
            <span className="hs-rank-badge">
              <span className="hs-rank-sparkle" aria-hidden="true">✦</span>
              {user.rank.toUpperCase()} LEVEL ADVOCATE
            </span>
          </div>
          <div className="hs-header-right">
            <button type="button" className="hs-bell-btn" aria-label="Notifications">
              <Bell />
              <span className="hs-bell-dot" aria-hidden="true" />
            </button>
            <div className="hs-avatar"><Avatar /></div>
          </div>
        </header>

        {/* 2. Total earned */}
        <section className="app-card hs-total-card">
          <p className="hs-total-label">Total Earned</p>
          <p className="hs-total-amount">
            <span className="hs-total-rupee">₹</span>
            {formatIntINR(totalEarnedThisMonth)}
            <span className="hs-total-decimals">.{decimalsSuffix(totalEarnedThisMonth)}</span>
          </p>
          <span className="hs-month-pill">
            <span className="hs-month-dot" aria-hidden="true" />
            This Month
          </span>
        </section>

        {/* 3. Stat cards */}
        <section className="hs-stats-grid">
          <div className="app-card hs-stat-card">
            <span className="hs-stat-chip"><CursorClick /></span>
            <p className="hs-stat-value">{formatIntINR(linkClicks)}</p>
            <p className="hs-stat-label">Link Clicks</p>
          </div>
          <div className="app-card hs-stat-card">
            <span className="hs-stat-chip"><TrendingUp /></span>
            <p className="hs-stat-value">{formatIntINR(conversions)}</p>
            <p className="hs-stat-label">Conversions</p>
          </div>
        </section>

        {/* 4. Next payout */}
        <section className="app-card hs-payout-card">
          <div className="hs-payout-top">
            <div className="hs-date-tile">
              <span className="hs-date-month">{payoutDate.month}</span>
              <span className="hs-date-day">{payoutDate.day}</span>
            </div>
            <div className="hs-payout-mid">
              <p className="hs-payout-title">Next Payout</p>
              <p className="hs-payout-sub">Estimated Date</p>
            </div>
            <div className="hs-payout-right">
              <p className="hs-payout-amount">₹{formatAmountINR(nextPayout.amount)}</p>
              <p className="hs-payout-locked"><Lock /><span>LOCKED</span></p>
            </div>
          </div>

          {rankProgress && (
            <>
              <div className="hs-rank-row">
                <span className="hs-rank-title">Rank Progress</span>
                <span className="hs-rank-away">
                  {rankProgress.salesToNext} sales away from{' '}
                  <span className="hs-rank-next">{rankProgress.nextRank}</span>
                </span>
              </div>
              <div className="hs-progress-track">
                <div className="hs-progress-fill" style={{ width: `${rankProgress.percent}%` }} />
              </div>
            </>
          )}
        </section>

        {/* 5-6. Recent conversions */}
        <h2 className="hs-section-heading">Recent Conversions</h2>
        <ul className="hs-conversion-list">
          {recentConversions.slice(0, 2).map((item) => (
            <li key={item.id} className="app-card hs-conversion-card">
              <span className="hs-conversion-chip"><Person /></span>
              <div className="hs-conversion-mid">
                <p className="hs-conversion-name">{item.name}</p>
                <p className="hs-conversion-label">{item.label}</p>
              </div>
              <p className="hs-conversion-amount">+₹{formatAmountINR(item.amount)}</p>
            </li>
          ))}
        </ul>

        <BottomNav active="home" onChange={onNavigate} />
      </div>
    </div>
  );
}
