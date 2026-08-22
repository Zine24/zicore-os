import React from 'react';

const styles = {
  container: {
    display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '8px', padding: '4px 0',
  },
  hub: {
    display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
    padding: '10px 8px', borderRadius: 10, border: '2px solid var(--border)',
    background: 'var(--bg2)', cursor: 'pointer', minHeight: 64,
    touchAction: 'manipulation', WebkitTapHighlightColor: 'transparent',
    transition: 'border-color 0.15s, background 0.15s',
  },
  label: { fontSize: 11, fontWeight: 700, letterSpacing: 1, marginTop: 4, color: 'var(--text-dim)' },
  icon: { fontSize: 20 },
};

export default function HubSelector({ hubs, active, onSelect }) {
  return (
    <div style={styles.container}>
      {Object.entries(hubs).map(([key, hub]) => (
        <div
          key={key}
          style={{
            ...styles.hub,
            borderColor: key === active ? 'var(--accent)' : 'var(--border)',
            background: key === active ? 'var(--bg3)' : 'var(--bg2)',
          }}
          onClick={() => onSelect(key)}
          onTouchEnd={() => onSelect(key)}
        >
          <span style={styles.icon}>{hub.icon}</span>
          <span style={{ ...styles.label, color: key === active ? 'var(--accent)' : 'var(--text-dim)' }}>
            {hub.label}
          </span>
        </div>
      ))}
    </div>
  );
}
