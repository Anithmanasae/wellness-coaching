import React from 'react';
import CoachBottomNav from './CoachBottomNav.jsx';
import { Folder } from './icons.jsx';

// Stub — the marketing/creatives library is designed later.
export default function CoachFolder({ onNavigate }) {
  return (
    <div className="screen-page">
      <div className="screen-phone">
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: '70vh', textAlign: 'center', gap: 14, color: 'var(--gray)' }}>
          <span style={{ width: 72, height: 72, borderRadius: 20, background: 'var(--sage)', color: 'var(--ink)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <Folder size={32} />
          </span>
          <h2 style={{ color: 'var(--ink)', fontSize: 22, fontWeight: 700 }}>Creatives Library</h2>
          <p style={{ maxWidth: 260, lineHeight: 1.5 }}>Shared banners, videos and campaign assets for your affiliates. Coming soon.</p>
        </div>
        <CoachBottomNav active="folder" onChange={onNavigate} />
      </div>
    </div>
  );
}
