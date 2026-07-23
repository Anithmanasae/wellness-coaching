import React from 'react';
import './leaderboard.css';
import BottomNav from './BottomNav.jsx';
import { Bell, Avatar, TrendingUp } from './icons.jsx';

// Styled leaderboard, rendered from the `data` payload
// (GET /api/leaderboard?me=:id):
// {
//   total: number,
//   podium: [{ rank, id, name, tier, earnings }],   // ranks 1,2,3 (index 0 = #1)
//   rows:   [{ rank, id, name, tier, earnings }],    // ranks 4..N
//   me:     { rank, earnings, percentile },
// }

/* ---------- helpers ---------- */

const inr = (n) =>
  '₹' + new Intl.NumberFormat('en-IN', { maximumFractionDigits: 0 }).format(Math.round(n));

const pad2 = (n) => String(n).padStart(2, '0');

/* A gold five-point star that sits above the champion. */
function Star({ size = 26 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M12 2l2.9 6.26 6.85.62-5.17 4.53 1.54 6.7L12 17.27 5.88 20.64l1.54-6.7L2.25 8.88l6.85-.62z" />
    </svg>
  );
}

/* One podium slot. `place` (1|2|3) drives ring colour, size and badge. */
function PodiumColumn({ entry, place }) {
  const avatarSize = place === 1 ? 86 : 64;
  return (
    <div className={`lb-podium-col lb-podium-col--${place}`}>
      {place === 1 && (
        <span className="lb-star" aria-hidden="true">
          <Star size={26} />
        </span>
      )}
      <div className={`lb-ring lb-ring--${place}`}>
        <div className="lb-ring-avatar">
          <Avatar size={avatarSize} />
        </div>
        <span className={`lb-badge lb-badge--${place}`}>{entry.rank}</span>
      </div>
      <p className="lb-podium-name">{entry.name}</p>
      <p className="lb-podium-earn">{inr(entry.earnings)}</p>
    </div>
  );
}

export default function LeaderboardScreen({ data, onNavigate }) {
  const { podium = [], rows = [], me } = data || {};
  const [first, second, third] = podium;

  return (
    <div className="screen-page">
      <div className="screen-phone">
        {/* 1. Header */}
        <header className="lb-header">
          <div className="lb-header-left">
            <span className="lb-header-avatar">
              <Avatar size={40} />
            </span>
            <h1 className="lb-title">Elite Advocates</h1>
          </div>
          <button type="button" className="lb-bell" aria-label="Notifications">
            <Bell size={22} />
          </button>
        </header>

        {/* 2. Podium — visual order is #2, #1, #3 with the champion elevated. */}
        <section className="lb-podium" aria-label="Top advocates">
          {second && <PodiumColumn entry={second} place={2} />}
          {first && <PodiumColumn entry={first} place={1} />}
          {third && <PodiumColumn entry={third} place={3} />}
        </section>

        {/* 3. Column headers */}
        <div className="lb-col-headers">
          <span className="lb-col-head lb-col-head--rank">Affiliates Rank</span>
          <span className="lb-col-head lb-col-head--earn">Total Earnings</span>
        </div>

        {/* 4. Rank list (ranks 4..N) */}
        <ul className="lb-list">
          {rows.map((row) => (
            <li key={row.id} className={`app-card lb-row${me && row.id === me.id ? ' lb-row--me' : ''}`}>
              <span className="lb-row-rank">{pad2(row.rank)}</span>
              <span className="lb-row-avatar">
                <Avatar size={48} />
              </span>
              <div className="lb-row-mid">
                <p className="lb-row-name">{row.name}</p>
                <p className="lb-row-tier">{row.tier} Tier</p>
              </div>
              <p className="lb-row-earn">{inr(row.earnings)}</p>
            </li>
          ))}
        </ul>

        {/* 5. Your current rank — the hero card */}
        {me && (
          <section className="lb-me">
            <div className="lb-me-rank">{me.rank}</div>
            <div className="lb-me-mid">
              <p className="lb-me-label">
                <TrendingUp size={14} />
                <span>Your Current Rank</span>
              </p>
              <p className="lb-me-headline">You're in the top {me.percentile}%</p>
            </div>
            <div className="lb-me-right">
              <p className="lb-me-earn-label">Current Earnings</p>
              <p className="lb-me-earn">{inr(me.earnings)}</p>
            </div>
          </section>
        )}

        <BottomNav active="leaderboard" onChange={onNavigate} />
      </div>
    </div>
  );
}
