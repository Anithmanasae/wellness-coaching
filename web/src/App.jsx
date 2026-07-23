import React, { useEffect, useState } from 'react';
import HomeScreen from './HomeScreen.jsx';
import LinksScreen from './LinksScreen.jsx';
import WalletScreen from './WalletScreen.jsx';
import LeaderboardScreen from './LeaderboardScreen.jsx';

// Jessica is the demo login; real auth will set this.
const CURRENT_USER_ID = 3;

// Each tab knows how to fetch its own payload.
const ENDPOINTS = {
  home: `/api/users/${CURRENT_USER_ID}/dashboard`,
  links: `/api/users/${CURRENT_USER_ID}/links`,
  wallet: `/api/users/${CURRENT_USER_ID}/wallet`,
  leaderboard: `/api/leaderboard?me=${CURRENT_USER_ID}`,
};

export default function App() {
  const [tab, setTab] = useState('home');
  const [cache, setCache] = useState({});
  const [error, setError] = useState(null);

  useEffect(() => {
    if (cache[tab]) return;
    let alive = true;
    fetch(ENDPOINTS[tab])
      .then((r) => {
        if (!r.ok) throw new Error(`API error ${r.status}`);
        return r.json();
      })
      .then((data) => alive && setCache((c) => ({ ...c, [tab]: data })))
      .catch((e) => alive && setError(e.message));
    return () => {
      alive = false;
    };
  }, [tab, cache]);

  // Re-fetch a tab's data after an action that changes it (e.g. payout request).
  const refresh = (key) => setCache((c) => {
    const next = { ...c };
    delete next[key];
    return next;
  });

  if (error) return <p style={{ padding: 24 }}>Could not load: {error}</p>;

  const data = cache[tab];
  if (!data) return <div className="screen-page"><div className="screen-phone" /></div>;

  switch (tab) {
    case 'links':
      return <LinksScreen data={data} onNavigate={setTab} />;
    case 'wallet':
      return <WalletScreen data={data} userId={CURRENT_USER_ID} onNavigate={setTab} onChanged={() => refresh('wallet')} />;
    case 'leaderboard':
      return <LeaderboardScreen data={data} onNavigate={setTab} />;
    case 'home':
    default:
      return <HomeScreen dashboard={data} onNavigate={setTab} />;
  }
}
