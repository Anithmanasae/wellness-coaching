import React, { useState } from 'react';
import './login.css';

// Email + password login. Two demo accounts are hinted below the form.
export default function Login({ onLogin }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setError('');
    setBusy(true);
    try {
      const res = await fetch('/api/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Login failed');
      onLogin(data.token, data.user);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const fill = (e, p) => { setEmail(e); setPassword(p); setError(''); };

  return (
    <div className="screen-page">
      <div className="screen-phone lg-phone">
        <div className="lg-brand">
          <span className="lg-logo" aria-hidden="true">✦</span>
          <span className="lg-brand-name">VigorElite</span>
        </div>

        <div className="lg-head">
          <h1 className="lg-title">Welcome back</h1>
          <p className="lg-subtitle">Sign in to your wellness network account.</p>
        </div>

        <form className="app-card lg-card" onSubmit={submit}>
          <label className="lg-label" htmlFor="lg-email">Email</label>
          <input id="lg-email" className="lg-input" type="email" autoComplete="username"
            value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com" required />

          <label className="lg-label" htmlFor="lg-pass">Password</label>
          <input id="lg-pass" className="lg-input" type="password" autoComplete="current-password"
            value={password} onChange={(e) => setPassword(e.target.value)} placeholder="••••••••" required />

          {error && <p className="lg-error" role="alert">{error}</p>}

          <button className="lg-submit" type="submit" disabled={busy}>
            {busy ? 'Signing in…' : 'Sign In'}
          </button>
        </form>

        <div className="lg-demo">
          <p className="lg-demo-title">Demo accounts</p>
          <button type="button" className="lg-demo-btn" onClick={() => fill('coach@epiclife.academy', 'coach123')}>
            <span>Wellness Coach</span><span className="lg-demo-hint">coach@epiclife.academy</span>
          </button>
          <button type="button" className="lg-demo-btn" onClick={() => fill('jessica@example.com', 'jessica123')}>
            <span>Affiliate (Jessica)</span><span className="lg-demo-hint">jessica@example.com</span>
          </button>
        </div>
      </div>
    </div>
  );
}
