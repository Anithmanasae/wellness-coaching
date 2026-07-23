import React, { useEffect, useState } from 'react';
import HomeScreen from './HomeScreen.jsx';

// Jessica is the demo login; a real auth flow would set this.
const CURRENT_USER_ID = 3;

export default function App() {
  const [dashboard, setDashboard] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetch(`/api/users/${CURRENT_USER_ID}/dashboard`)
      .then((r) => {
        if (!r.ok) throw new Error(`API error ${r.status}`);
        return r.json();
      })
      .then(setDashboard)
      .catch((e) => setError(e.message));
  }, []);

  if (error) return <p style={{ padding: 24 }}>Could not load dashboard: {error}</p>;
  if (!dashboard) return null;
  return <HomeScreen dashboard={dashboard} />;
}
