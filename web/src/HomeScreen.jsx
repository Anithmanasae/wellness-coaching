import React from 'react';
import './home.css';

// Styled home screen, implemented against this exact `dashboard` prop shape
// (see App.jsx / GET /api/users/:id/dashboard):
// {
//   user: { id, name, rank },
//   totalEarnedThisMonth: number,
//   linkClicks: number,
//   conversions: number,
//   nextPayout: { amount: number, estimatedDate: 'YYYY-MM-DD' },
//   rankProgress: { currentRank, nextRank, salesToNext, percent } | null,
//   recentConversions: [{ id, name, label, amount }],
// }

/* ---------- formatting helpers ---------- */

// Indian-style grouped integer part, e.g. 1250 -> "1,250", 125000 -> "1,25,000"
function formatIntINR(value) {
  return new Intl.NumberFormat('en-IN', { maximumFractionDigits: 0 }).format(
    Math.trunc(Math.abs(value))
  );
}

// Full amount with 2 decimals, e.g. 450 -> "450.00"
function formatAmountINR(value) {
  return new Intl.NumberFormat('en-IN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
}

// 2-digit decimal suffix, e.g. 1250 -> "00", 1250.5 -> "50"
function decimalsSuffix(value) {
  return Math.round((Math.abs(value) % 1) * 100)
    .toString()
    .padStart(2, '0');
}

const MONTHS = [
  'JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN',
  'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC',
];

// "2026-08-15" -> { month: "AUG", day: "15" }
function parseISODate(iso) {
  const [, m, d] = String(iso).split('-');
  const monthIndex = Number(m) - 1;
  return {
    month: MONTHS[monthIndex] || '',
    day: String(Number(d) || ''),
  };
}

/* ---------- inline SVG icons (stroke-based, currentColor) ---------- */

const iconProps = {
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 1.8,
  strokeLinecap: 'round',
  strokeLinejoin: 'round',
};

function BellIcon({ size = 20 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" {...iconProps} aria-hidden="true">
      <path d="M18 8a6 6 0 0 0-12 0c0 7-3 8-3 8h18s-3-1-3-8" />
      <path d="M13.7 20a2 2 0 0 1-3.4 0" />
    </svg>
  );
}

function CursorClickIcon({ size = 22 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" {...iconProps} aria-hidden="true">
      <path d="M14 4.1 12 6" />
      <path d="m5.1 8-2.9-.8" />
      <path d="m6 12-1.9 2" />
      <path d="M7.2 2.2 8 5.1" />
      <path d="M9.037 9.69a.498.498 0 0 1 .653-.653l11 4.5a.5.5 0 0 1-.074.949l-4.349 1.041a1 1 0 0 0-.74.739l-1.04 4.35a.5.5 0 0 1-.95.074z" />
    </svg>
  );
}

function TrendingUpIcon({ size = 22 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" {...iconProps} aria-hidden="true">
      <path d="M3 17l6-6 4 4 8-8" />
      <path d="M15 7h6v6" />
    </svg>
  );
}

function LockIcon({ size = 12 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" {...iconProps} aria-hidden="true">
      <rect x="4" y="11" width="16" height="10" rx="2.5" />
      <path d="M8 11V7a4 4 0 0 1 8 0v4" />
    </svg>
  );
}

function PersonIcon({ size = 20 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" {...iconProps} aria-hidden="true">
      <circle cx="12" cy="8" r="3.5" />
      <path d="M5 20c0-3.6 3.1-6 7-6s7 2.4 7 6" />
    </svg>
  );
}

function HomeIcon({ size = 20 }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="currentColor"
      stroke="currentColor"
      strokeWidth="1"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M12 3.2 3.5 10v10a1 1 0 0 0 1 1H9.5v-5.5a2.5 2.5 0 0 1 5 0V21h5a1 1 0 0 0 1-1V10z" />
    </svg>
  );
}

function LinkIcon({ size = 22 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" {...iconProps} aria-hidden="true">
      <path d="M10 13a5 5 0 0 0 7.5.5l3-3a5 5 0 0 0-7-7l-1.7 1.7" />
      <path d="M14 11a5 5 0 0 0-7.5-.5l-3 3a5 5 0 0 0 7 7l1.7-1.7" />
    </svg>
  );
}

function WalletIcon({ size = 22 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" {...iconProps} aria-hidden="true">
      <rect x="2.5" y="6" width="19" height="13" rx="3" />
      <path d="M2.5 10h19" opacity="0" />
      <path d="M16.5 12.5h5" opacity="0" />
      <path d="M17 6V5a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v3" />
      <circle cx="16.5" cy="12.5" r="1.4" fill="currentColor" stroke="none" />
    </svg>
  );
}

function TrophyIcon({ size = 22 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" {...iconProps} aria-hidden="true">
      <path d="M8 4h8v6a4 4 0 0 1-8 0z" />
      <path d="M8 5H4.5v1.5A3.5 3.5 0 0 0 8 10" />
      <path d="M16 5h3.5v1.5A3.5 3.5 0 0 1 16 10" />
      <path d="M12 14v3.5" />
      <path d="M8.5 20.5h7" />
      <path d="M10 17.5h4l.8 3h-5.6z" />
    </svg>
  );
}

function AvatarSVG({ size = 48 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 48 48" aria-hidden="true">
      <circle cx="24" cy="24" r="24" fill="#E8D9C5" />
      <circle cx="24" cy="19" r="7.5" fill="#3A423C" />
      <path d="M24 29c-8.3 0-14 5-14.8 11.3A24 24 0 0 0 24 48a24 24 0 0 0 14.8-7.7C38 34 32.3 29 24 29z" fill="#3A423C" />
    </svg>
  );
}

/* ---------- screen ---------- */

export default function HomeScreen({ dashboard }) {
  const {
    user,
    totalEarnedThisMonth,
    linkClicks,
    conversions,
    nextPayout,
    rankProgress,
    recentConversions,
  } = dashboard;

  const payoutDate = parseISODate(nextPayout.estimatedDate);

  return (
    <div className="hs-page">
      <div className="hs-phone">
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
              <BellIcon />
              <span className="hs-bell-dot" aria-hidden="true" />
            </button>
            <div className="hs-avatar">
              <AvatarSVG />
            </div>
          </div>
        </header>

        {/* 2. Total earned */}
        <section className="hs-card hs-total-card">
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
          <div className="hs-card hs-stat-card">
            <span className="hs-stat-chip">
              <CursorClickIcon />
            </span>
            <p className="hs-stat-value">{formatIntINR(linkClicks)}</p>
            <p className="hs-stat-label">Link Clicks</p>
          </div>
          <div className="hs-card hs-stat-card">
            <span className="hs-stat-chip">
              <TrendingUpIcon />
            </span>
            <p className="hs-stat-value">{formatIntINR(conversions)}</p>
            <p className="hs-stat-label">Conversions</p>
          </div>
        </section>

        {/* 4. Next payout */}
        <section className="hs-card hs-payout-card">
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
              <p className="hs-payout-locked">
                <LockIcon />
                <span>LOCKED</span>
              </p>
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
                <div
                  className="hs-progress-fill"
                  style={{ width: `${rankProgress.percent}%` }}
                />
              </div>
            </>
          )}
        </section>

        {/* 5-6. Recent conversions */}
        <h2 className="hs-section-heading">Recent Conversions</h2>
        <ul className="hs-conversion-list">
          {recentConversions.slice(0, 2).map((item) => (
            <li key={item.id} className="hs-card hs-conversion-card">
              <span className="hs-conversion-chip">
                <PersonIcon />
              </span>
              <div className="hs-conversion-mid">
                <p className="hs-conversion-name">{item.name}</p>
                <p className="hs-conversion-label">{item.label}</p>
              </div>
              <p className="hs-conversion-amount">+₹{formatAmountINR(item.amount)}</p>
            </li>
          ))}
        </ul>

        {/* 7. Bottom nav */}
        <nav className="hs-bottom-nav" aria-label="Main navigation">
          <button type="button" className="hs-nav-slot hs-nav-active" aria-label="Home">
            <HomeIcon />
          </button>
          <button type="button" className="hs-nav-slot" aria-label="Links">
            <LinkIcon />
          </button>
          <button type="button" className="hs-nav-slot" aria-label="Wallet">
            <WalletIcon />
          </button>
          <button type="button" className="hs-nav-slot" aria-label="Achievements">
            <TrophyIcon />
          </button>
        </nav>
      </div>
    </div>
  );
}
