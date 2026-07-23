import React from 'react';
import './coach-affiliates.css';
import CoachBottomNav from './CoachBottomNav.jsx';
import { Bell, Avatar, Search, Chevron } from './icons.jsx';

// Styled from `data` (GET /api/coach/affiliates):
// [{ id, name, tier, title, location, totalSales }]  tier: Bronze|Silver|Gold|Platinum|Diamond
// The screen owns its search box + tier filter chips (client-side).

const inr = (n) =>
  '₹' + new Intl.NumberFormat('en-IN', { maximumFractionDigits: 0 }).format(Math.round(n));

// Primary chips shown first; Silver/Bronze rounded out for completeness.
const FILTERS = [
  { label: 'All Affiliates', tier: null },
  { label: 'Diamond', tier: 'Diamond' },
  { label: 'Platinum', tier: 'Platinum' },
  { label: 'Gold', tier: 'Gold' },
  { label: 'Silver', tier: 'Silver' },
  { label: 'Bronze', tier: 'Bronze' },
];

export default function CoachAffiliates({ data, onNavigate, onLogout }) {
  const [query, setQuery] = React.useState('');
  const [tier, setTier] = React.useState(null);

  const list = Array.isArray(data) ? data : [];
  const q = query.trim().toLowerCase();

  const filtered = list.filter((a) => {
    if (tier && a.tier !== tier) return false;
    if (!q) return true;
    return (
      (a.name && a.name.toLowerCase().includes(q)) ||
      (a.title && a.title.toLowerCase().includes(q)) ||
      (a.location && a.location.toLowerCase().includes(q))
    );
  });

  return (
    <div className="screen-page">
      <div className="screen-phone">
        {/* 1. Header */}
        <header className="ca-header">
          <div className="ca-header-left">
            <span className="ca-header-avatar">
              <Avatar size={40} />
            </span>
            <span className="ca-brand">VigorElite</span>
          </div>
          <button type="button" className="ca-bell" aria-label="Notifications">
            <Bell size={22} />
          </button>
        </header>

        {/* 2. Title */}
        <h1 className="ca-title">Affiliates</h1>

        {/* 3. Search */}
        <div className="ca-search">
          <Search size={20} />
          <input
            className="ca-search-input"
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search affiliates…"
            aria-label="Search affiliates"
          />
        </div>

        {/* 4. Filter chips */}
        <div className="ca-chips" role="tablist" aria-label="Filter by tier">
          {FILTERS.map((f) => {
            const active = tier === f.tier;
            return (
              <button
                key={f.label}
                type="button"
                role="tab"
                aria-selected={active}
                className={`ca-chip${active ? ' ca-chip--active' : ''}`}
                onClick={() => setTier(f.tier)}
              >
                {f.label}
              </button>
            );
          })}
        </div>

        {/* 5. Affiliate cards */}
        {filtered.length > 0 ? (
          <ul className="ca-list">
            {filtered.map((a) => (
              <li key={a.id} className="app-card ca-card">
                <div className="ca-card-avatar">
                  <Avatar size={68} />
                </div>
                <p className="ca-card-name">{a.name}</p>
                <span className={`ca-pill ca-pill--${String(a.tier).toLowerCase()}`}>
                  {a.tier}
                </span>
                <p className="ca-card-meta">
                  {a.title} • {a.location}
                </p>
                <div className="ca-divider" />
                <div className="ca-card-foot">
                  <div className="ca-card-total">
                    <p className="ca-total-label">Total Sales</p>
                    <p className="ca-total-value">{inr(a.totalSales)}</p>
                  </div>
                  <span className="ca-card-chevron" aria-hidden="true">
                    <Chevron size={20} />
                  </span>
                </div>
              </li>
            ))}
          </ul>
        ) : (
          <p className="ca-empty">No affiliates match your search.</p>
        )}

        <CoachBottomNav active="affiliates" onChange={onNavigate} />
      </div>
    </div>
  );
}
