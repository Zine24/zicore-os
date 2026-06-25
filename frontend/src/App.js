import React, { useState, useEffect, useCallback, useRef } from 'react';
import HubSelector from './components/HubSelector';
import FlightHub from './hubs/FlightHub';
import HabitatHub from './hubs/HabitatHub';
import PowerHub from './hubs/PowerHub';
import CommsHub from './hubs/CommsHub';
import MenuBar from './components/MenuBar';
import ControlPanel from './components/ControlPanel';

const HUBS = {
  flight: { label: 'FLIGHT', icon: '🛸', component: FlightHub },
  habitat: { label: 'HABITAT', icon: '🏠', component: HabitatHub },
  power: { label: 'POWER', icon: '⚡', component: PowerHub },
  comms: { label: 'COMMS', icon: '📡', component: CommsHub },
};

export default function App() {
  const [activeHub, setActiveHub] = useState('flight');
  const [telemetry, setTelemetry] = useState({
    zihab: { o2: 20.5, co2: 0.04, temp: 22, humidity: 45, pressure: 101.3, status: 'nominal' },
    zinav: { alt_km: 400, vel_kms: 7.68, inclination_deg: 51.6, dv_remaining: 1200, fuel_pct: 65, status: 'nominal' },
    zipower: { solar_w: 1200, battery_pct: 85, load_w: 980, status: 'nominal' },
  });
  const [modalMode, setModalMode] = useState('AUTO');
  const wsRef = useRef(null);

  useEffect(() => {
    const ws = new WebSocket('ws://localhost:8080/ws/telemetry');
    ws.onmessage = (e) => {
      try { setTelemetry(JSON.parse(e.data)); } catch {}
    };
    ws.onclose = () => setTimeout(connectWS, 3000);
    wsRef.current = ws;
    return () => ws.close();
  }, []);

  const connectWS = useCallback(() => {
    const ws = new WebSocket('ws://localhost:8080/ws/telemetry');
    ws.onmessage = (e) => { try { setTelemetry(JSON.parse(e.data)); } catch {} };
    wsRef.current = ws;
  }, []);

  const HubComponent = HUBS[activeHub]?.component || FlightHub;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', padding: '8px', gap: '8px' }}>
      <HubSelector hubs={HUBS} active={activeHub} onSelect={setActiveHub} />
      
      <div style={{ flex: 1, overflow: 'hidden' }}>
        <HubComponent telemetry={telemetry} />
      </div>

      <ControlPanel mode={modalMode} onModeChange={setModalMode} />
      <MenuBar activeHub={activeHub} onHubChange={setActiveHub} />
      
      <div style={{
        height: 28, display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '0 8px', fontSize: 12, color: 'var(--text-dim)',
        borderTop: '1px solid var(--border)'
      }}>
        <span><span className={`status-dot ${telemetry.zihab.status}`} /> ZIO CORE ONLINE</span>
        <span>v0.1.0 | MODE: {modalMode}</span>
      </div>
    </div>
  );
}
