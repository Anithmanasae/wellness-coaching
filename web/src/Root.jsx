import React, { useEffect, useState } from 'react';
import { api, getToken, setSession, clearSession, getStoredUser } from './api';
import Login from './Login.jsx';
import AffiliateApp from './AffiliateApp.jsx';
import CoachApp from './CoachApp.jsx';

// Top-level auth gate + role router: coach -> CoachApp, affiliate -> AffiliateApp.
export default function Root() {
  const [user, setUser] = useState(getStoredUser());
  const [loading, setLoading] = useState(!!getToken());

  useEffect(() => {
    if (!getToken()) return;
    api('/api/me')
      .then((r) => setUser(r.user))
      .catch(() => { clearSession(); setUser(null); })
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="screen-page"><div className="screen-phone" /></div>;

  if (!user) {
    return <Login onLogin={(token, u) => { setSession(token, u); setUser(u); }} />;
  }

  const logout = () => { clearSession(); setUser(null); };
  return user.role === 'coach'
    ? <CoachApp user={user} onLogout={logout} />
    : <AffiliateApp user={user} onLogout={logout} />;
}
