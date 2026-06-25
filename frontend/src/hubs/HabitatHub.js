import React from 'react';
import TelemetryPanel from '../components/TelemetryPanel';

export default function HabitatHub({ telemetry }) {
  const hab = telemetry.zihab;
  const pow = telemetry.zipower;
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8, height: '100%' }}>
      <div style={{ flex: 1, display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
        <TelemetryPanel data={hab} type="zihab" />
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          <div className="panel" style={{ textAlign: 'center', flex: 1 }}>
            <div style={{ fontSize: 36 }}>🏠</div>
            <div className="label" style={{ marginTop: 4 }}>HÁBITAT</div>
            <div style={{ marginTop: 8, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <span className={`status-dot ${hab.status}`} />
              <span style={{ fontSize: 18, fontWeight: 700, textTransform: 'uppercase' }}>{hab.status}</span>
            </div>
          </div>
          <div className="panel" style={{
            display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, flex: 1, alignItems: 'center',
          }}>
            <div style={{ textAlign: 'center' }}>
              <div className="label">Tripulantes</div>
              <div className="value">0</div>
            </div>
            <div style={{ textAlign: 'center' }}>
              <div className="label">O₂ restante</div>
              <div className="value">{Math.round(hab.o2 / 0.5)}<span style={{ fontSize: 14, color: 'var(--text-dim)' }}>h</span></div>
            </div>
            <div style={{ textAlign: 'center' }}>
              <div className="label">Potencia</div>
              <div className="value">{pow.load_w}<span style={{ fontSize: 14, color: 'var(--text-dim)' }}>W</span></div>
            </div>
            <div style={{ textAlign: 'center' }}>
              <div className="label">Presurización</div>
              <div className="value" style={{ color: hab.pressure > 99 ? 'var(--success)' : 'var(--danger)' }}>
                {hab.pressure}<span style={{ fontSize: 14, color: 'var(--text-dim)' }}>kPa</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
