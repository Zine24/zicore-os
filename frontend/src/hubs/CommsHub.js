import React from 'react';

export default function CommsHub({ telemetry }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8, height: '100%' }}>
      <div style={{ flex: 1, display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
        <div className="panel">
          <div className="label" style={{ marginBottom: 8 }}>ENLACES</div>
          {[
            { name: 'Tierra', snr: 14.2, lat: 420, status: 'online' },
            { name: 'Base Lunar', snr: 22.1, lat: 12, status: 'online' },
            { name: 'ZiRØN-Σ', snr: 8.5, lat: 850, status: 'degraded' },
            { name: 'Mars Relay', snr: 0, lat: 0, status: 'offline' },
          ].map(link => (
            <div key={link.name} style={{
              display: 'flex', justifyContent: 'space-between', alignItems: 'center',
              padding: '8px 4px', borderBottom: '1px solid var(--border)',
            }}>
              <div>
                <div style={{ fontWeight: 600 }}>{link.name}</div>
                <div style={{ fontSize: 12, color: 'var(--text-dim)' }}>SNR: {link.snr}dB | LAT: {link.lat}ms</div>
              </div>
              <span className={`status-dot ${link.status === 'online' ? 'nominal' : link.status === 'degraded' ? 'warning' : 'critical'}`} />
            </div>
          ))}
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          <div className="panel" style={{ textAlign: 'center', flex: 1 }}>
            <div style={{ fontSize: 48 }}>📡</div>
            <div className="label">COMUNICACIONES</div>
            <div style={{ marginTop: 8, fontSize: 14, color: 'var(--text-dim)' }}>
              Antena principal: activa<br />
              Banda: S-band / Ka-band<br />
              Cripto: AES-256
            </div>
          </div>
          <div className="panel" style={{ flex: 1 }}>
            <div className="label" style={{ marginBottom: 4 }}>ÚLTIMA TRANSMISIÓN</div>
            <div style={{ fontSize: 13, color: 'var(--text-dim)' }}>
              {new Date().toLocaleTimeString()} - Telemetría nominal<br />
              Buffer: 98% | Paquetes perdidos: 0.02%
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
