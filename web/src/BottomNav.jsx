import React from 'react';
import { Home, Link, Wallet, Trophy } from './icons.jsx';

const TABS = [
  { key: 'home', label: 'Home', Icon: Home },
  { key: 'links', label: 'Links', Icon: Link },
  { key: 'wallet', label: 'Wallet', Icon: Wallet },
  { key: 'leaderboard', label: 'Leaderboard', Icon: Trophy },
];

// Shared bottom navigation. `active` is the current tab key; `onChange(key)`
// switches tabs.
export default function BottomNav({ active, onChange }) {
  return (
    <nav className="nav" aria-label="Main navigation">
      {TABS.map(({ key, label, Icon }) => (
        <button
          key={key}
          type="button"
          className={`nav-slot${active === key ? ' nav-active' : ''}`}
          aria-label={label}
          aria-current={active === key ? 'page' : undefined}
          onClick={() => onChange(key)}
        >
          <Icon />
        </button>
      ))}
    </nav>
  );
}
