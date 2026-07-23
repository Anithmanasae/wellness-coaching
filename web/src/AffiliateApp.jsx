import React, { useEffect, useState } from 'react';
import HomeScreen from './HomeScreen.jsx';
import LinksScreen from './LinksScreen.jsx';
import WalletScreen from './WalletScreen.jsx';
import LeaderboardScreen from './LeaderboardScreen.jsx';
import { api } from './api';

// The affiliate experience for the logged-in user.
export default function AffiliateApp({ user, onLogout }) {
  const uid = user.id;
  const ENDPOINTS = {
    home: `/api/users/${uid}/dashboard`,
    links: `/api/users/${uid}/links`,
    wallet: `/api/users/${uid}/wallet`,
    leaderboard: `/api/leaderboard?me=${uid}`,
  };

  const [tab, setTab] = useState('home');
  const [cache, setCache] = useState({});
  const [error, setError] = useState(null);

  useEffect(() => {
    if (cache[tab]) return;
    let alive = true;
    api(ENDPOINTS[tab])
      .then((data) => alive && setCache((c) => ({ ...c, [tab]: data })))
      .catch((e) => alive && setError(e.message));
    return () => { alive = false; };
  }, [tab, cache]);

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
      return <WalletScreen data={data} userId={uid} onNavigate={setTab} onChanged={() => refresh('wallet')} />;
    case 'leaderboard':
      return <LeaderboardScreen data={data} onNavigate={setTab} />;
    case 'home':
    default:
      return <HomeScreen dashboard={data} onNavigate={setTab} />;
  }
}
