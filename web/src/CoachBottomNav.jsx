import React from 'react';
import { Home, People, Banknote, Folder } from './icons.jsx';

const TABS = [
  { key: 'home', label: 'Dashboard', Icon: Home },
  { key: 'affiliates', label: 'Affiliates', Icon: People },
  { key: 'payouts', label: 'Payouts', Icon: Banknote },
  { key: 'folder', label: 'Library', Icon: Folder },
];

export default function CoachBottomNav({ active, onChange }) {
  return (
    <nav className="nav" aria-label="Coach navigation">
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
