import React from 'react';

const items = [
  { key: 'sys', label: '≡ SYS' },
  { key: 'comms', label: '📡 COMMS' },
  { key: 'nav', label: '🗺 NAV' },
  { key: 'power', label: '⚡ POWER' },
  { key: 'diag', label: '🔬 DIAG' },
  { key: 'emerg', label: '🛑 EMERG' },
];

const hubs = ['flight', 'habitat', 'power', 'comms'];

export default function MenuBar({ activeHub, onHubChange }) {
  return (
    <div style={{
      display: 'flex', gap: 6, padding: '4px 0', overflow: 'auto',
      WebkitOverflowScrolling: 'touch', scrollbarWidth: 'none',
    }}>
      {items.map(item => {
        const isHub = hubs.includes(item.key);
        const hubKey = isHub ? item.key : null;
        return (
          <button key={item.key} style={{
            flexShrink: 0, minHeight: 52, minWidth: 80,
            padding: '8px 16px', border: '2px solid var(--border)',
            borderRadius: 10, background: hubKey === activeHub ? 'var(--bg3)' : 'var(--bg2)',
            color: hubKey === activeHub ? 'var(--accent)' : 'var(--text)',
            fontSize: 13, fontWeight: 600, cursor: 'pointer',
            touchAction: 'manipulation', WebkitTapHighlightColor: 'transparent',
            borderColor: hubKey === activeHub ? 'var(--accent)' : 'var(--border)',
          }}
            onClick={() => hubKey && onHubChange(hubKey)} onTouchEnd={() => hubKey && onHubChange(hubKey)}>
            {item.label}
          </button>
        );
      })}
    </div>
  );
}
