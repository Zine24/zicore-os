import React from 'react';

const gaugeStyle = { display: 'flex', flexDirection: 'column', gap: 4, padding: '8px 12px' };
const labelStyle = { fontSize: 11, color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: 1 };
const valueStyle = { fontSize: 20, fontWeight: 700, fontVariantNumeric: 'tabular-nums' };
const meterOuter = { height: 6, background: 'var(--bg3)', borderRadius: 3, overflow: 'hidden' };

function Gauge({ label, value, unit, min = 0, max = 100, pct }) {
  const p = pct ?? ((value - min) / (max - min)) * 100;
  const color = p > 80 ? 'var(--success)' : p > 40 ? 'var(--warning)' : 'var(--danger)';
  return (
    <div style={gaugeStyle}>
      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
        <span style={labelStyle}>{label}</span>
        <span style={{ fontSize: 14, fontWeight: 600 }}>{value}{unit}</span>
      </div>
      <div style={meterOuter}>
        <div style={{ width: `${Math.min(100, Math.max(0, p))}%`, height: '100%', background: color, borderRadius: 3, transition: 'width 0.3s' }} />
      </div>
    </div>
  );
}

function Stat({ label, value, unit, color }) {
  return (
    <div style={gaugeStyle}>
      <span style={labelStyle}>{label}</span>
      <span style={{ ...valueStyle, color: color || 'var(--text)' }}>{value}<span style={{ fontSize: 14, fontWeight: 400, color: 'var(--text-dim)', marginLeft: 4 }}>{unit}</span></span>
    </div>
  );
}

export default function TelemetryPanel({ data, type }) {
  if (type === 'zihab') {
    return (
      <div className="panel" style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
        <Stat label="O₂" value={data.o2} unit="%" color={data.o2 < 20.5 ? 'var(--danger)' : 'var(--success)'} />
        <Gauge label="O₂" value={data.o2} min={18} max={22} />
        <Stat label="CO₂" value={data.co2} unit="%" color={data.co2 > 0.5 ? 'var(--danger)' : 'var(--text)'} />
        <Stat label="Temp" value={data.temp} unit="°C" color={data.temp > 30 ? 'var(--danger)' : 'var(--text)'} />
        <Stat label="Humedad" value={data.humidity} unit="%" />
        <Stat label="Presión" value={data.pressure} unit="kPa" />
      </div>
    );
  }
  if (type === 'zinav') {
    return (
      <div className="panel" style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
        <Stat label="ALTITUD" value={data.alt_km} unit="km" />
        <Stat label="VELOCIDAD" value={data.vel_kms} unit="km/s" />
        <Stat label="INCLINACIÓN" value={data.inclination_deg} unit="°" />
        <Stat label="Δv RESTANTE" value={data.dv_remaining} unit="m/s" color={data.dv_remaining < 200 ? 'var(--warning)' : 'var(--text)'} />
        <Gauge label="COMBUSTIBLE" value={data.fuel_pct} pct={data.fuel_pct} />
      </div>
    );
  }
  if (type === 'zipower') {
    const net = data.solar_w - data.load_w;
    return (
      <div className="panel" style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
        <Stat label="SOLAR" value={data.solar_w} unit="W" />
        <Stat label="BATERÍA" value={data.battery_pct} unit="%" color={data.battery_pct < 20 ? 'var(--danger)' : data.battery_pct < 40 ? 'var(--warning)' : 'var(--success)'} />
        <Gauge label="BATERÍA" value={data.battery_pct} pct={data.battery_pct} />
        <Stat label="CARGA" value={data.load_w} unit="W" />
        <Stat label="BALANCE" value={net > 0 ? '+' : ''}{net} unit="W" color={net < 0 ? 'var(--danger)' : 'var(--success)'} />
        <Stat label="VOLTAJE" value={data.grid_v} unit="V" />
      </div>
    );
  }
  return null;
}
