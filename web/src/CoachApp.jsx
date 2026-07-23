import React, { useEffect, useState } from 'react';
import CoachHome from './CoachHome.jsx';
import CoachAffiliates from './CoachAffiliates.jsx';
import CoachPayouts from './CoachPayouts.jsx';
import CoachFolder from './CoachFolder.jsx';
import { api } from './api';

const ENDPOINTS = {
  home: '/api/coach/overview',
  affiliates: '/api/coach/affiliates',
  payouts: '/api/coach/payouts',
};

// The wellness coach experience.
export default function CoachApp({ user, onLogout }) {
  const [tab, setTab] = useState('home');
  const [cache, setCache] = useState({});
  const [error, setError] = useState(null);

  useEffect(() => {
    if (tab === 'folder' || cache[tab]) return;
    let alive = true;
    api(ENDPOINTS[tab])
      .then((data) => alive && setCache((c) => ({ ...c, [tab]: data })))
      .catch((e) => alive && setError(e.message));
    return () => { alive = false; };
  }, [tab, cache]);

  const refresh = (key) => setCache((c) => { const n = { ...c }; delete n[key]; return n; });

  // Coach acts on a payout, then we refresh both the queue and the dashboard.
  const payoutAction = async (payoutId, action) => {
    await api(`/api/payouts/${payoutId}/${action}`, { method: 'POST' });
    refresh('payouts');
    refresh('home');
  };

  if (error) return <p style={{ padding: 24 }}>Could not load: {error}</p>;

  if (tab === 'folder') return <CoachFolder onNavigate={setTab} onLogout={onLogout} />;

  const data = cache[tab];
  if (!data) return <div className="screen-page"><div className="screen-phone" /></div>;

  switch (tab) {
    case 'affiliates':
      return <CoachAffiliates data={data} onNavigate={setTab} onLogout={onLogout} />;
    case 'payouts':
      return <CoachPayouts data={data} onAction={payoutAction} onNavigate={setTab} onLogout={onLogout} />;
    case 'home':
    default:
      return <CoachHome data={data} onNavigate={setTab} onLogout={onLogout} />;
  }
}
