import React from 'react';
import TelemetryPanel from '../components/TelemetryPanel';

export default function FlightHub({ telemetry }) {
  const nav = telemetry.zinav;
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8, height: '100%' }}>
      <div style={{ flex: 1, display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
        <TelemetryPanel data={nav} type="zinav" />
        <div className="panel" style={{
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          background: 'var(--bg)', border: '2px solid var(--border)',
          borderRadius: 12, minHeight: 160, fontSize: 14, color: 'var(--text-dim)',
        }}>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: 48, marginBottom: 8 }}>🛸</div>
            <div>3D ORBIT VIEW</div>
            <div style={{ fontSize: 12, marginTop: 4 }}>[Cesium.js integration pending]</div>
          </div>
        </div>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8 }}>
        <div className="panel" style={{ textAlign: 'center' }}>
          <div className="label">ALTITUD</div>
          <div className="value">{nav.alt_km}</div>
          <div className="label">km</div>
        </div>
        <div className="panel" style={{ textAlign: 'center' }}>
          <div className="label">VELOCIDAD</div>
          <div className="value">{nav.vel_kms}</div>
          <div className="label">km/s</div>
        </div>
        <div className="panel" style={{ textAlign: 'center' }}>
          <div className="label">COMBUSTIBLE</div>
          <div className="value">{nav.fuel_pct}<span style={{ fontSize: 14, color: 'var(--text-dim)' }}>%</span></div>
          <div className="meter" style={{ marginTop: 4 }}>
            <div className={`meter-fill ${nav.fuel_pct > 40 ? 'ok' : nav.fuel_pct > 20 ? 'warn' : 'crit'}`}
              style={{ width: `${nav.fuel_pct}%` }} />
          </div>
        </div>
      </div>
    </div>
  );
}
