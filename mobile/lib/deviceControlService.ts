import { Platform, Alert, Vibration } from 'react-native';
import * as Haptics from 'expo-haptics';
import * as Clipboard from 'expo-clipboard';
import * as Brightness from 'expo-brightness';
import * as Linking from 'expo-linking';
import * as Notifications from 'expo-notifications';
import * as FileSystem from 'expo-file-system';
import { Audio } from 'expo-av';
import { CameraView, useCameraPermissions } from 'expo-camera';
import { BASE_URL } from './api';
import { authStorage } from './auth';

let currentSound: Audio.Sound | null = null;

export interface DeviceCommand {
  command: string;
  params: Record<string, string>;
  raw: string;
}

const COMMAND_REGEX = /\[([A-Z_]+)(?::([^\]]*))?\]/g;

export function parseCommandsFromResponse(text: string): DeviceCommand[] {
  const commands: DeviceCommand[] = [];
  let match;
  while ((match = COMMAND_REGEX.exec(text)) !== null) {
    const cmd = match[1];
    const param = match[2] || '';
    const params: Record<string, string> = {};
    if (param.includes(':')) {
      param.split(',').forEach(p => {
        const [k, v] = p.split(':');
        params[k.trim()] = v.trim();
      });
    } else if (param) {
      params['value'] = param;
    }
    commands.push({ command: cmd, params, raw: match[0] });
  }
  return commands;
}

export function stripCommands(text: string): string {
  return text.replace(COMMAND_REGEX, '').replace(/\s{2,}/g, ' ').trim();
}

export async function executeCommand(cmd: DeviceCommand): Promise<string> {
  switch (cmd.command) {
    case 'VIBRATE': {
      const pattern = cmd.params.value;
      if (pattern) {
        const ms = pattern.split(',').map(Number);
        Vibration.vibrate(ms);
      } else {
        await Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Heavy);
      }
      return 'Vibrated device';
    }

    case 'VIBRATE_PATTERN': {
      const ms = (cmd.params.value || '200,100,200').split(',').map(Number);
      Vibration.vibrate(ms);
      return 'Pattern vibration executed';
    }

    case 'HAPTIC_LIGHT': {
      await Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
      return 'Light haptic';
    }

    case 'HAPTIC_MEDIUM': {
      await Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
      return 'Medium haptic';
    }

    case 'HAPTIC_HEAVY': {
      await Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Heavy);
      return 'Heavy haptic';
    }

    case 'NOTIFICATION': {
      await Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
      return 'Notification haptic';
    }

    case 'WARNING': {
      await Haptics.notificationAsync(Haptics.NotificationFeedbackType.Warning);
      return 'Warning haptic';
    }

    case 'ERROR': {
      await Haptics.notificationAsync(Haptics.NotificationFeedbackType.Error);
      return 'Error haptic';
    }

    case 'BRIGHTNESS': {
      const level = parseInt(cmd.params.value || '50', 10);
      const clamped = Math.max(0, Math.min(100, level));
      await Brightness.setBrightnessAsync(clamped / 100);
      return `Brightness set to ${clamped}%`;
    }

    case 'BRIGHTNESS_UP': {
      const current = await Brightness.getBrightnessAsync();
      const next = Math.min(1, current + 0.1);
      await Brightness.setBrightnessAsync(next);
      return `Brightness increased to ${Math.round(next * 100)}%`;
    }

    case 'BRIGHTNESS_DOWN': {
      const curr = await Brightness.getBrightnessAsync();
      const next2 = Math.max(0, curr - 0.1);
      await Brightness.setBrightnessAsync(next2);
      return `Brightness decreased to ${Math.round(next2 * 100)}%`;
    }

    case 'CLIPBOARD': {
      await Clipboard.setStringAsync(cmd.params.value || '');
      return `Copied to clipboard: ${(cmd.params.value || '').substring(0, 50)}`;
    }

    case 'OPEN': {
      const url = cmd.params.value;
      if (url) {
        const canOpen = await Linking.canOpenURL(url);
        if (canOpen) {
          await Linking.openURL(url);
          return `Opened: ${url}`;
        }
        return `Cannot open: ${url}`;
      }
      return 'No URL specified';
    }

    case 'TELL': {
      return cmd.params.value || '';
    }

    case 'SCREENSHOT': {
      try {
        const uri = await FileSystem.takeSnapshotAsStringAsync({
          result: FileSystem.FileSystemSavePhotoResult.PHOTO,
        } as any);
        return `Screenshot saved: ${uri}`;
      } catch {
        return 'Screenshot not available on this device';
      }
    }

    case 'CAMERA_CAPTURE': {
      return `[CAMERA_CAPTURE]`;
    }

    case 'CAMERA_FRONT': {
      return `[CAMERA_FRONT]`;
    }

    case 'CAMERA_BACK': {
      return `[CAMERA_BACK]`;
    }

    case 'CAMERA_CLOSE': {
      return `[CAMERA_CLOSE]`;
    }

    case 'VISION_ANALYZE': {
      return `[VISION_ANALYZE:${cmd.params.value || ''}]`;
    }

    case 'SPEAK': {
      const text = cmd.params.value || '';
      if (!text) return 'No text to speak';
      try {
        await Audio.setAudioModeAsync({ playsInSilentModeIOS: true });
        const response = await fetch(`${BASE_URL}/api/tts`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ text, voice: 'alloy' }),
        });
        if (!response.ok) throw new Error(`TTS HTTP ${response.status}`);
        const blob = await response.blob();
        const reader = new FileReader();
        return new Promise((resolve) => {
          reader.onloadend = async () => {
            const base64 = (reader.result as string).split(',')[1];
            const uri = `${FileSystem.cacheDirectory}tts_speak.mp3`;
            await FileSystem.writeAsStringAsync(uri, base64, { encoding: FileSystem.EncodingType.Base64 });
            const { sound } = await Audio.Sound.createAsync({ uri }, { shouldPlay: true });
            currentSound = sound;
            resolve(`Speaking: ${text.substring(0, 50)}`);
          };
          reader.readAsDataURL(blob);
        });
      } catch (e: any) {
        return `Speak error: ${e.message}`;
      }
    }

    case 'MEDIA_PLAY': {
      const query = cmd.params.value || 'music';
      try {
        await Audio.setAudioModeAsync({ playsInSilentModeIOS: true });
        const { sound } = await Audio.Sound.createAsync(
          { uri: `${BASE_URL}/api/tts?text=${encodeURIComponent(`Playing ${query}`)}` },
          { shouldPlay: true }
        );
        currentSound = sound;
        return `Playing: ${query}`;
      } catch (e: any) {
        return `Media play error: ${e.message}`;
      }
    }

    case 'MEDIA_STOP': {
      try {
        if (currentSound) {
          await currentSound.stopAsync();
          await currentSound.unloadAsync();
          currentSound = null;
        }
        return 'Media stopped';
      } catch (e: any) {
        return `Media stop error: ${e.message}`;
      }
    }

    case 'ALERT': {
      const msg = cmd.params.value || 'ZIO Alert';
      Alert.alert('ZIO Alert', msg);
      return `Alert shown: ${msg}`;
    }

    default:
      return `Unknown command: ${cmd.command}`;
  }
}

export async function executeAllCommands(text: string): Promise<{ results: string[]; cleanText: string }> {
  const commands = parseCommandsFromResponse(text);
  const results: string[] = [];
  for (const cmd of commands) {
    try {
      const result = await executeCommand(cmd);
      results.push(result);
    } catch (e: any) {
      results.push(`Error: ${e.message}`);
    }
  }
  return { results, cleanText: stripCommands(text) };
}

let cameraRef: any = null;

export function setCameraRef(ref: any) {
  cameraRef = ref;
}

export async function captureAndAnalyze(): Promise<{ success: boolean; analysis?: any; error?: string }> {
  if (!cameraRef?.current) {
    return { success: false, error: 'Camera not initialized. Say "open camera" first.' };
  }
  try {
    const photo = await cameraRef.current.takePictureAsync({
      quality: 0.7,
      base64: true,
      skipProcessing: false,
    });
    if (!photo?.base64) {
      return { success: false, error: 'Failed to capture photo' };
    }
    const token = await authStorage.getToken();
    const response = await fetch(`${BASE_URL}/api/vision/analyze`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ image: `data:image/jpeg;base64,${photo.base64}` }),
    });
    const data = await response.json();
    return { success: true, analysis: data.result || data };
  } catch (e: any) {
    return { success: false, error: e.message };
  }
}

export async function analyzeImagePath(path: string): Promise<{ success: boolean; analysis?: any; error?: string }> {
  try {
    const token = await authStorage.getToken();
    const response = await fetch(`${BASE_URL}/api/openvision/analyze?path=${encodeURIComponent(path)}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    const data = await response.json();
    return { success: true, analysis: data.result || data };
  } catch (e: any) {
    return { success: false, error: e.message };
  }
}
