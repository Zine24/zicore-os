import React from 'react';
import TelemetryPanel from '../components/TelemetryPanel';

export default function PowerHub({ telemetry }) {
  const pow = telemetry.zipower;
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8, height: '100%' }}>
      <div style={{ flex: 1, display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
        <TelemetryPanel data={pow} type="zipower" />
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, alignContent: 'start' }}>
          <div className="panel" style={{ textAlign: 'center' }}>
            <div className="label">PANELES SOLARES</div>
            <div style={{ fontSize: 32 }}>☀️</div>
            <div className="value">{pow.solar_w}<span style={{ fontSize: 14, color: 'var(--text-dim)' }}>W</span></div>
          </div>
          <div className="panel" style={{ textAlign: 'center' }}>
            <div className="label">BATERÍA</div>
            <div style={{ fontSize: 32 }}>🔋</div>
            <div className="value">{pow.battery_pct}<span style={{ fontSize: 14, color: 'var(--text-dim)' }}>%</span></div>
          </div>
          <div className="panel" style={{ textAlign: 'center' }}>
            <div className="label">CONSUMO</div>
            <div style={{ fontSize: 32 }}>⚡</div>
            <div className="value">{pow.load_w}<span style={{ fontSize: 14, color: 'var(--text-dim)' }}>W</span></div>
          </div>
          <div className="panel" style={{ textAlign: 'center' }}>
            <div className="label">BALANCE</div>
            <div style={{ fontSize: 32 }}>{pow.solar_w - pow.load_w >= 0 ? '✅' : '⚠️'}</div>
            <div className="value" style={{ color: pow.solar_w - pow.load_w >= 0 ? 'var(--success)' : 'var(--danger)' }}>
              {pow.solar_w - pow.load_w > 0 ? '+' : ''}{pow.solar_w - pow.load_w}<span style={{ fontSize: 14, color: 'var(--text-dim)' }}>W</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
