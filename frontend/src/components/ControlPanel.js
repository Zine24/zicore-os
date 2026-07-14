import React from 'react';

const modes = ['AUTO', 'MANUAL', 'AI-ASSIST'];
const btnStyle = {
  flex: 1, minHeight: 48, border: '2px solid var(--border)', borderRadius: 8,
  background: 'var(--bg2)', color: 'var(--text)', fontSize: 13, fontWeight: 700,
  cursor: 'pointer', touchAction: 'manipulation', WebkitTapHighlightColor: 'transparent',
  transition: 'all 0.1s',
};

export default function ControlPanel({ mode, onModeChange, onCommand }) {
  const handleCmd = (cmd) => {
    if (onCommand) onCommand(cmd);
  };
  return (
    <div className="panel" style={{ padding: '8px 12px' }}>
      <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
        <button className="danger" style={{ minWidth: 80, minHeight: 56, fontSize: 16, fontWeight: 900 }}
          onClick={() => handleCmd('ABORT')} onTouchEnd={() => handleCmd('ABORT')}>ABORT</button>
        <button className="primary" style={{ flex: 1, minHeight: 56, fontSize: 16 }}
          onClick={() => handleCmd('HOLD')} onTouchEnd={() => handleCmd('HOLD')}>HOLD</button>
        <button style={{ flex: 1, minHeight: 56, border: '2px solid var(--accent)' }}
          onClick={() => handleCmd('THROTTLE_UP')} onTouchEnd={() => handleCmd('THROTTLE_UP')}>
          <span style={{ fontSize: 18 }}>▲</span>
        </button>
        <button style={{ flex: 1, minHeight: 56, border: '2px solid var(--accent)' }}
          onClick={() => handleCmd('THROTTLE_DOWN')} onTouchEnd={() => handleCmd('THROTTLE_DOWN')}>
          <span style={{ fontSize: 18 }}>▼</span>
        </button>
        <button className="danger" style={{ minWidth: 80, minHeight: 56, fontSize: 16, fontWeight: 900 }}
          onClick={() => handleCmd('FIRE')} onTouchEnd={() => handleCmd('FIRE')}>FIRE</button>
      </div>
      <div style={{ display: 'flex', gap: 8 }}>
        {modes.map(m => (
          <button key={m} style={{
            ...btnStyle,
            borderColor: m === mode ? 'var(--accent)' : 'var(--border)',
            background: m === mode ? 'var(--bg3)' : 'var(--bg2)',
            color: m === mode ? 'var(--accent)' : 'var(--text-dim)',
          }} onClick={() => onModeChange(m)} onTouchEnd={() => onModeChange(m)}>
            {m}
          </button>
        ))}
      </div>
    </div>
  );
}
