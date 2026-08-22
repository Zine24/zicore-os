import { Platform } from 'react-native';
import { BASE_URL } from './api';
import { authStorage } from './auth';

interface SensorData {
  battery_level?: number;
  battery_state?: string;
  ambient_light?: number;
  device_name?: string;
  os_version?: string;
  accelerometer?: { x: number; y: number; z: number };
  gyroscope?: { x: number; y: number; z: number };
  magnetometer?: { x: number; y: number; z: number };
}

let sensorInterval: ReturnType<typeof setInterval> | null = null;
let latestSensors: SensorData = {};

async function collectSensors(): Promise<SensorData> {
  const data: SensorData = {};

  try {
    const Battery = require('expo-battery');
    data.battery_level = Math.round((await Battery.getBatteryLevelAsync()) * 100);
    const state = await Battery.getBatteryStateAsync();
    data.battery_state = state === 2 ? 'charging' : state === 3 ? 'full' : 'discharging';
  } catch {}

  try {
    const Device = require('expo-device');
    data.device_name = Device.modelName || Device.deviceName || 'Unknown';
    data.os_version = `${Device.osName} ${Device.osVersion}`;
  } catch {}

  try {
    const { LightSensor } = require('expo-sensors');
    const lux = await new Promise<number>((resolve) => {
      const sub = LightSensor.addListener(({ illuminance }: any) => {
        resolve(illuminance);
        sub.remove();
      });
      setTimeout(() => resolve(-1), 2000);
    });
    if (lux >= 0) data.ambient_light = Math.round(lux);
  } catch {}

  try {
    const { Accelerometer } = require('expo-sensors');
    const acc = await new Promise<{ x: number; y: number; z: number }>((resolve) => {
      const sub = Accelerometer.addListener(({ x, y, z }: any) => {
        resolve({ x, y, z });
        sub.remove();
      });
      setTimeout(() => resolve({ x: 0, y: 0, z: 0 }), 2000);
    });
    data.accelerometer = acc;
  } catch {}

  try {
    const { Gyroscope } = require('expo-sensors');
    const gyro = await new Promise<{ x: number; y: number; z: number }>((resolve) => {
      const sub = Gyroscope.addListener(({ x, y, z }: any) => {
        resolve({ x, y, z });
        sub.remove();
      });
      setTimeout(() => resolve({ x: 0, y: 0, z: 0 }), 2000);
    });
    data.gyroscope = gyro;
  } catch {}

  return data;
}

export function startSensorCollection(intervalMs: number = 30000) {
  if (sensorInterval) return;
  sensorInterval = setInterval(async () => {
    try {
      latestSensors = await collectSensors();
      const token = await authStorage.getToken();
      await fetch(`${BASE_URL}/api/mobile/sensors`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ session_id: 'mobile', ...latestSensors }),
      });
    } catch {}
  }, intervalMs);
}

export function stopSensorCollection() {
  if (sensorInterval) {
    clearInterval(sensorInterval);
    sensorInterval = null;
  }
}

export async function getLatestSensors(): Promise<SensorData> {
  if (Object.keys(latestSensors).length === 0) {
    latestSensors = await collectSensors();
  }
  return latestSensors;
}

export async function collectAndReturn(): Promise<SensorData> {
  latestSensors = await collectSensors();
  return latestSensors;
}
