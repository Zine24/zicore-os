import { Audio } from 'expo-av';
import * as FileSystem from 'expo-file-system';
import { authStorage } from '@/lib/auth';
import { BASE_URL } from './api';
import { stripCommands } from './deviceControlService';

let isListening = false;
let recording: Audio.Recording | null = null;

export function isVoiceActive(): boolean {
  return isListening;
}

export async function startListening(onResult: (text: string) => void, onError?: (err: string) => void) {
  if (isListening) return;
  try {
    const { status } = await Audio.requestPermissionsAsync();
    if (status !== 'granted') {
      onError?.('Microphone permission denied');
      return;
    }
    await Audio.setAudioModeAsync({ allowsRecordingIOS: true, playsInSilentModeIOS: true });
    const rec = await Audio.Recording.createAsync(Audio.RecordingOptionsPresets.HIGH_QUALITY);
    recording = rec;
    isListening = true;
  } catch (e: any) {
    onError?.(e.message);
  }
}

export async function stopListening(): Promise<string | null> {
  if (!isListening || !recording) return null;
  try {
    isListening = false;
    await recording.stopAndUnloadAsync();
    const uri = recording.getURI();
    recording = null;
    if (!uri) return null;
    const text = await sendToSTT(uri);
    return text;
  } catch {
    isListening = false;
    recording = null;
    return null;
  }
}

async function sendToSTT(uri: string): Promise<string | null> {
  try {
    const token = await authStorage.getToken();
    const formData = new FormData();
    formData.append('audio', { uri, type: 'audio/m4a', name: 'recording.m4a' } as any);
    formData.append('lang', 'es');
    const response = await fetch(`${BASE_URL}/api/stt`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
      body: formData,
    });
    const data = await response.json();
    return data.text || null;
  } catch {
    return null;
  }
}

export async function speakText(text: string): Promise<boolean> {
  try {
    const cleanText = stripCommands(text).substring(0, 500);
    if (!cleanText) return false;
    const token = await authStorage.getToken();
    const response = await fetch(`${BASE_URL}/api/tts`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify({ text: cleanText, lang: 'es' }),
    });
    if (!response.ok) return false;
    const blob = await response.blob();
    const reader = new FileReader();
    return new Promise((resolve) => {
      reader.onload = async () => {
        try {
          const base64 = (reader.result as string).split(',')[1];
          const fileUri = FileSystem.cacheDirectory + 'zio_tts_output.mp3';
          await FileSystem.writeAsStringAsync(fileUri, base64, { encoding: FileSystem.EncodingType.Base64 });
          const { sound } = await Audio.Sound.createAsync({ uri: fileUri });
          await sound.playAsync();
          sound.setOnPlaybackStatusUpdate((status) => {
            if (status.isLoaded && status.didJustFinish) {
              sound.unloadAsync();
              resolve(true);
            }
          });
        } catch {
          resolve(false);
        }
      };
      reader.readAsDataURL(blob);
    });
  } catch {
    return false;
  }
}

let continuousMode = false;
let voiceLoopTimer: ReturnType<typeof setTimeout> | null = null;

export function setContinuousMode(enabled: boolean) {
  continuousMode = enabled;
}

export function isContinuousMode(): boolean {
  return continuousMode;
}

export async function voiceLoop(
  onUserText: (text: string) => void,
  onZioReply: (text: string) => void,
  onError?: (err: string) => void
) {
  if (!continuousMode) return;

  const spoken = await stopListening();
  if (spoken && spoken.trim().length > 2) {
    onUserText(spoken);
  }

  voiceLoopTimer = setTimeout(async () => {
    if (continuousMode) {
      await startListening(
        () => {},
        (err) => onError?.(err)
      );
      voiceLoopLoop(onUserText, onZioReply, onError);
    }
  }, 500);
}

async function voiceLoopLoop(
  onUserText: (text: string) => void,
  onZioReply: (text: string) => void,
  onError?: (err: string) => void
) {
  if (!continuousMode) return;

  voiceLoopTimer = setTimeout(async () => {
    if (!isListening) return voiceLoop(onUserText, onZioReply, onError);
    voiceLoopLoop(onUserText, onZioReply, onError);
  }, 1000);
}

export function stopContinuousMode() {
  continuousMode = false;
  if (voiceLoopTimer) {
    clearTimeout(voiceLoopTimer);
    voiceLoopTimer = null;
  }
  if (isListening) {
    recording?.stopAndUnloadAsync().catch(() => {});
    isListening = false;
    recording = null;
  }
}
