import React, { useRef, useState } from 'react';
import './links.css';
import { Avatar, Bell, Link, Lock, Copy, Share, Person, CheckCircle } from './icons.jsx';
import BottomNav from './BottomNav.jsx';

// Styled "Links & Creatives" screen, rendered from the `data` payload
// (GET /api/users/:id/links):
// {
//   referralBase: 'premium-wellness.club/ref/',
//   referralCode: 'jessica',
//   totalClicks: number,
//   campaigns: [{ id, slug, title, tag, clicks, conversions, conversionRate, converterCount, activeDays }],
// }

// Group digits with Indian locale separators, no decimals.
const grp = (n) => new Intl.NumberFormat('en-IN', { maximumFractionDigits: 0 }).format(n);

// Best-effort clipboard write that degrades gracefully.
function copyText(text) {
  if (typeof navigator !== 'undefined' && navigator.clipboard && navigator.clipboard.writeText) {
    return navigator.clipboard.writeText(text).catch(() => {});
  }
  return Promise.resolve();
}

// Tag rule: "Performance" / "Elite" tags read as gold, everything else sage.
function isGoldTag(tag) {
  return /performance|elite/i.test(tag || '');
}

export default function LinksScreen({ data, onNavigate }) {
  const { referralBase, referralCode, campaigns = [] } = data;
  const referralLink = `${referralBase}${referralCode}`;

  const [copiedMain, setCopiedMain] = useState(false);
  const [copiedId, setCopiedId] = useState(null);
  const mainTimer = useRef(null);
  const cardTimer = useRef(null);

  const handleCopyMain = () => {
    copyText(referralLink);
    setCopiedMain(true);
    clearTimeout(mainTimer.current);
    mainTimer.current = setTimeout(() => setCopiedMain(false), 1500);
  };

  const handleCopyCampaign = (campaign) => {
    copyText(`${referralBase}${campaign.slug}`);
    setCopiedId(campaign.id);
    clearTimeout(cardTimer.current);
    cardTimer.current = setTimeout(() => setCopiedId(null), 1500);
  };

  return (
    <div className="screen-page">
      <div className="screen-phone">
        {/* 1. Header */}
        <header className="lk-header">
          <div className="lk-header-left">
            <span className="lk-avatar"><Avatar size={40} /></span>
            <span className="lk-welcome">Welcome back</span>
          </div>
          <button type="button" className="lk-bell" aria-label="Notifications">
            <Bell size={22} />
          </button>
        </header>

        {/* 2-3. Title + subtitle */}
        <h1 className="lk-title">Links &amp; Creatives</h1>
        <p className="lk-subtitle">
          Manage your bespoke referral engine. Generate custom paths or utilize our curated
          campaign assets.
        </p>

        {/* 4. Custom link generator */}
        <section className="app-card lk-generator">
          <div className="lk-gen-head">
            <span className="lk-gen-chip"><Link size={24} /></span>
            <h2 className="lk-gen-title">Custom Link Generator</h2>
          </div>

          <p className="lk-field-label">Destination URL or Campaign Tag</p>
          <div className="lk-field">
            <span className="lk-field-text">{referralLink}</span>
            <span className="lk-field-lock" aria-hidden="true"><Lock size={16} /></span>
          </div>

          <button
            type="button"
            className={`lk-copy-btn${copiedMain ? ' is-copied' : ''}`}
            onClick={handleCopyMain}
            aria-live="polite"
          >
            {copiedMain ? <CheckCircle size={18} /> : <Copy size={18} />}
            <span>{copiedMain ? 'Copied!' : 'Copy Link'}</span>
          </button>
        </section>

        {/* 5. Section heading */}
        <h2 className="lk-section-heading">Active Campaign Links</h2>

        {/* 6. Campaign cards */}
        <div className="lk-campaigns">
          {campaigns.map((c) => {
            const gold = isGoldTag(c.tag);
            const copied = copiedId === c.id;
            return (
              <article key={c.id} className="app-card lk-campaign">
                <div className="lk-camp-top">
                  <span className={`lk-tag${gold ? ' lk-tag-gold' : ' lk-tag-sage'}`}>{c.tag}</span>
                  <div className="lk-camp-actions">
                    <button
                      type="button"
                      className="lk-icon-btn"
                      aria-label={`Share ${c.title}`}
                    >
                      <Share size={20} />
                    </button>
                    <button
                      type="button"
                      className={`lk-icon-btn${copied ? ' is-copied' : ''}`}
                      onClick={() => handleCopyCampaign(c)}
                      aria-label={`Copy link for ${c.title}`}
                    >
                      {copied ? <CheckCircle size={20} /> : <Copy size={20} />}
                    </button>
                  </div>
                </div>

                <h3 className="lk-camp-title">{c.title}</h3>

                <div className="lk-stats">
                  <div className="lk-tile">
                    <span className="lk-tile-label">TOTAL CLICKS</span>
                    <span className="lk-tile-value">{grp(c.clicks)}</span>
                  </div>
                  <div className="lk-tile">
                    <span className="lk-tile-label">CONVERSION</span>
                    <span className="lk-tile-value lk-tile-gold">{c.conversionRate}%</span>
                  </div>
                </div>

                <div className="lk-camp-bottom">
                  <div className="lk-cluster">
                    {[0, 1, 2].map((i) => (
                      <span key={i} className="lk-cluster-avatar">
                        <Person size={16} />
                      </span>
                    ))}
                    <span className="lk-cluster-badge">+{c.converterCount}</span>
                  </div>
                  <span className="lk-active-days">Active for {c.activeDays} days</span>
                </div>
              </article>
            );
          })}
        </div>

        <BottomNav active="links" onChange={onNavigate} />
      </div>
    </div>
  );
}
