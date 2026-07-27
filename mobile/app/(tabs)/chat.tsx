import { useState, useRef, useEffect } from 'react';
import { View, Text, TextInput, TouchableOpacity, FlatList, StyleSheet, KeyboardAvoidingView, Platform, Animated, Modal, Image } from 'react-native';
import { Audio } from 'expo-av';
import { CameraView, useCameraPermissions } from 'expo-camera';
import * as FileSystem from 'expo-file-system';
import { useChatStore } from '@/stores/chatStore';
import { Ionicons } from '@expo/vector-icons';
import { COLORS, SPACING, RADIUS } from '@/theme/colors';
import { BASE_URL } from '@/lib/api';
import { authStorage } from '@/lib/auth';
import { executeAllCommands, stripCommands, setCameraRef, captureAndAnalyze } from '@/lib/deviceControlService';
import { startSensorCollection } from '@/lib/sensorService';
import { speakText as ttsSpeak, startListening, stopListening, isVoiceActive, setContinuousMode, isContinuousMode, stopContinuousMode } from '@/lib/voiceService';

interface MessageProps {
  role: 'user' | 'assistant';
  content: string;
  mediaUrl?: string;
  mediaType?: string;
  onSpeak?: () => void;
  speaking?: boolean;
  streaming?: boolean;
}

function MessageBubble({ role, content, mediaUrl, mediaType, onSpeak, speaking, streaming }: MessageProps & { streaming?: boolean; mediaUrl?: string; mediaType?: string }) {
  const isUser = role === 'user';
  // Parse [GENERATED:TYPE:/path] from content
  const genMatch = content.match(/\[GENERATED:(\w+):(.*?)\]/);
  const parsedMediaUrl = mediaUrl || genMatch?.[2] || '';
  const parsedMediaType = mediaType || genMatch?.[1]?.toLowerCase() || '';
  // Clean text: remove generation tags
  const cleanContent = content.replace(/\[GENERATED:[^\]]+\]/g, '').trim();

  return (
    <View style={[styles.bubble, isUser ? styles.bubbleUser : styles.bubbleAssistant]}>
      {!isUser && (
        <View style={styles.botLabel}>
          <Ionicons name="hardware-chip-outline" size={10} color={COLORS.accent} />
          <Text style={styles.botName}>ZIO</Text>
        </View>
      )}
      <Text style={[styles.bubbleText, isUser && styles.bubbleTextUser]}>
        {cleanContent}
        {streaming && <Text style={styles.cursor}>▌</Text>}
      </Text>
      {/* Inline media rendering */}
      {parsedMediaUrl && !isUser && (
        <View style={styles.inlineMedia}>
          {(parsedMediaType === 'image' || /\.(png|jpg|jpeg|gif|bmp|webp)$/i.test(parsedMediaUrl)) && (
            <Image
              source={{ uri: parsedMediaUrl.startsWith('http') ? parsedMediaUrl : `${BASE_URL}${parsedMediaUrl}` }}
              style={styles.mediaImage}
              resizeMode="contain"
            />
          )}
          {(parsedMediaType === 'audio' || /\.(mp3|wav|ogg|flac|m4a|aac)$/i.test(parsedMediaUrl)) && (
            <AudioPlayer url={parsedMediaUrl.startsWith('http') ? parsedMediaUrl : `${BASE_URL}${parsedMediaUrl}`} />
          )}
          {(parsedMediaType === 'video' || /\.(mp4|avi|mkv|mov|webm)$/i.test(parsedMediaUrl)) && (
            <Text style={styles.mediaLink}>▶ Video: {parsedMediaUrl.split('/').pop()}</Text>
          )}
          {(parsedMediaType === '3d' || /\.(stl|obj|glb|gltf)$/i.test(parsedMediaUrl)) && (
            <Text style={styles.mediaLink}>📦 3D Model: {parsedMediaUrl.split('/').pop()}</Text>
          )}
        </View>
      )}
      {!isUser && onSpeak && (
        <TouchableOpacity style={styles.speakBtn} onPress={onSpeak}>
          <Ionicons name={speaking ? "volume-high" : "volume-medium-outline"} size={14} color={COLORS.primary} />
        </TouchableOpacity>
      )}
    </View>
  );
}

function AudioPlayer({ url }: { url: string }) {
  const [playing, setPlaying] = useState(false);
  const [sound, setSound] = useState<Audio.Sound | null>(null);

  const togglePlay = async () => {
    if (playing && sound) {
      await sound.stopAsync();
      setPlaying(false);
    } else if (sound) {
      await sound.playAsync();
      setPlaying(true);
    } else {
      const { sound: newSound } = await Audio.Sound.createAsync({ uri: url });
      setSound(newSound);
      setPlaying(true);
      newSound.setOnPlaybackStatusUpdate((status) => {
        if (status.isLoaded && status.didJustFinish) setPlaying(false);
      });
    }
  };

  useEffect(() => {
    return () => { sound?.unloadAsync(); };
  }, [sound]);

  return (
    <TouchableOpacity style={styles.audioPlayer} onPress={togglePlay}>
      <Ionicons name={playing ? "pause-circle" : "play-circle"} size={28} color={COLORS.primary} />
      <Text style={styles.audioLabel}>{playing ? 'Playing...' : 'Play Audio'}</Text>
    </TouchableOpacity>
  );
}

export default function ChatScreen() {
  const { messages, isLoading, sendMessage, clearMessages } = useChatStore();
  const [input, setInput] = useState('');
  const [recording, setRecording] = useState(false);
  const [sttLoading, setSttLoading] = useState(false);
  const [speakingId, setSpeakingId] = useState<string | null>(null);
  const [showCamera, setShowCamera] = useState(false);
  const [autoSpeak, setAutoSpeak] = useState(false);
  const [voiceMode, setVoiceMode] = useState(false);
  const [cameraPermission, requestCameraPermission] = useCameraPermissions();
  const cameraRef = useRef<any>(null);
  const flatListRef = useRef<FlatList>(null);
  const pulseAnim = useRef(new Animated.Value(1)).current;

  useEffect(() => {
    startSensorCollection(30000);
  }, []);

  useEffect(() => {
    flatListRef.current?.scrollToEnd({ animated: true });
  }, [messages]);

  useEffect(() => {
    if (recording) {
      Animated.loop(
        Animated.sequence([
          Animated.timing(pulseAnim, { toValue: 1.4, duration: 600, useNativeDriver: true }),
          Animated.timing(pulseAnim, { toValue: 1, duration: 600, useNativeDriver: true }),
        ])
      ).start();
    } else {
      pulseAnim.setValue(1);
    }
  }, [recording]);

  useEffect(() => {
    if (cameraRef.current) setCameraRef(cameraRef);
  }, [showCamera]);

  const processResponse = async (text: string) => {
    const { results, cleanText } = await executeAllCommands(text);
    const needsCamera = results.some(r => r.includes('[CAMERA_CAPTURE]'));
    if (needsCamera) {
      if (!cameraPermission?.granted) {
        await requestCameraPermission();
      }
      setShowCamera(true);
      setTimeout(async () => {
        if (cameraRef.current) {
          setCameraRef(cameraRef);
          const analysis = await captureAndAnalyze();
          if (analysis.success && analysis.analysis) {
            const desc = typeof analysis.analysis === 'string'
              ? analysis.analysis
              : JSON.stringify(analysis.analysis).substring(0, 500);
            await sendMessage(`[Vision analysis result]: ${desc}`);
          }
        }
      }, 1500);
    }
    return cleanText;
  };

  const handleSend = async () => {
    const text = input.trim();
    if (!text || isLoading) return;
    setInput('');
    await sendMessage(text);
  };

  const handleSendWithVoice = async () => {
    const text = input.trim();
    if (!text || isLoading) return;
    setInput('');
    await sendMessage(text);
    if (autoSpeak) {
      setTimeout(() => {
        const lastAssistant = [...messages].reverse().find(m => m.role === 'assistant');
        if (lastAssistant) speakTextAuto(lastAssistant.content);
      }, 3000);
    }
  };

  const startRecording = async () => {
    try {
      const { status } = await Audio.requestPermissionsAsync();
      if (status !== 'granted') return;
      await Audio.setAudioModeAsync({ allowsRecordingIOS: true, playsInSilentModeIOS: true });
      const rec = await Audio.Recording.createAsync(Audio.RecordingOptionsPresets.HIGH_QUALITY);
      setRecording(true);
      (global as any).__zicoreRecording = rec;
    } catch (e) {
      console.log('Recording error:', e);
    }
  };

  const stopRecording = async () => {
    try {
      setRecording(false);
      const rec = (global as any).__zicoreRecording;
      if (!rec) return;
      await rec.stopAndUnloadAsync();
      const uri = rec.getURI();
      if (!uri) return;
      setSttLoading(true);
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
      setSttLoading(false);
      if (data.text) {
        setInput(data.text);
        if (voiceMode) {
          setTimeout(() => handleSendWithVoice(), 300);
        }
      }
    } catch (e) {
      setSttLoading(false);
    }
  };

  const speakTextAuto = async (text: string) => {
    setSpeakingId('auto');
    await ttsSpeak(text);
    setSpeakingId(null);
  };

  const handleVoiceMode = () => {
    const next = !voiceMode;
    setVoiceMode(next);
    setContinuousMode(next);
    setAutoSpeak(next);
  };

  const takeCameraSnapshot = async () => {
    if (!cameraRef.current) return;
    setCameraRef(cameraRef);
    const result = await captureAndAnalyze();
    if (result.success && result.analysis) {
      const desc = typeof result.analysis === 'string'
        ? result.analysis
        : JSON.stringify(result.analysis).substring(0, 500);
      await sendMessage(`[Vision analysis]: ${desc}`);
    }
  };

  const toggleCamera = async () => {
    if (!cameraPermission?.granted) {
      const perm = await requestCameraPermission();
      if (!perm.granted) return;
    }
    setShowCamera(!showCamera);
  };

  return (
    <KeyboardAvoidingView style={styles.container} behavior={Platform.OS === 'ios' ? 'padding' : undefined} keyboardVerticalOffset={90}>
      <View style={styles.scanlines} pointerEvents="none" />

      <View style={styles.header}>
        <View style={styles.headerLeft}>
          <View style={styles.avatar}>
            <Text style={styles.avatarText}>Z</Text>
          </View>
          <View>
            <Text style={styles.headerTitle}>ZIO AI</Text>
            <View style={styles.statusRow}>
              <View style={[styles.statusDot, isLoading ? styles.statusThinking : styles.statusOnline]} />
              <Text style={styles.headerSub}>{isLoading ? 'Thinking...' : voiceMode ? 'Voice Mode' : 'Online'}</Text>
            </View>
          </View>
        </View>
        <View style={styles.headerActions}>
          <TouchableOpacity onPress={handleVoiceMode} style={[styles.headerBtn, voiceMode && styles.headerBtnActive]}>
            <Ionicons name={voiceMode ? "mic" : "mic-outline"} size={16} color={voiceMode ? COLORS.background : COLORS.textMuted} />
          </TouchableOpacity>
          <TouchableOpacity onPress={() => setAutoSpeak(!autoSpeak)} style={[styles.headerBtn, autoSpeak && styles.headerBtnActive]}>
            <Ionicons name={autoSpeak ? "volume-high" : "volume-medium-outline"} size={16} color={autoSpeak ? COLORS.background : COLORS.textMuted} />
          </TouchableOpacity>
          <TouchableOpacity onPress={toggleCamera} style={[styles.headerBtn, showCamera && styles.headerBtnActive]}>
            <Ionicons name={showCamera ? "camera" : "camera-outline"} size={16} color={showCamera ? COLORS.background : COLORS.textMuted} />
          </TouchableOpacity>
          <TouchableOpacity onPress={clearMessages} style={styles.headerBtn}>
            <Ionicons name="trash-outline" size={16} color={COLORS.textMuted} />
          </TouchableOpacity>
        </View>
      </View>

      {showCamera && (
        <View style={styles.cameraContainer}>
          <CameraView ref={cameraRef} style={styles.cameraView} facing="back">
            <View style={styles.cameraOverlay}>
              <View style={styles.cameraCornerTL} />
              <View style={styles.cameraCornerTR} />
              <View style={styles.cameraCornerBL} />
              <View style={styles.cameraCornerBR} />
              <Text style={styles.cameraLabel}>OPENVISION LIVE</Text>
              <TouchableOpacity style={styles.captureBtn} onPress={takeCameraSnapshot}>
                <Ionicons name="scan" size={28} color={COLORS.primary} />
              </TouchableOpacity>
            </View>
          </CameraView>
        </View>
      )}

      <FlatList
        ref={flatListRef}
        data={messages}
        keyExtractor={(item) => item.id}
        renderItem={({ item }) => (
          <MessageBubble
            role={item.role}
            content={item.content}
            mediaUrl={item.mediaUrl}
            mediaType={item.mediaType}
            onSpeak={item.role === 'assistant' ? () => { setSpeakingId(item.id); ttsSpeak(item.content).then(() => setSpeakingId(null)); } : undefined}
            speaking={speakingId === item.id}
            streaming={item.streaming}
          />
        )}
        contentContainerStyle={styles.messageList}
        ListEmptyComponent={
          <View style={styles.empty}>
            <View style={styles.emptyHex}>
              <Text style={styles.emptyZ}>Z</Text>
            </View>
            <Text style={styles.emptyText}>Ask ZIO anything</Text>
            <Text style={styles.emptySub}>Aerospace, vision, voice, device control</Text>
            <View style={styles.chips}>
              {['Que hora es', 'Que ves?', 'Open camera', 'Vibrate'].map((q) => (
                <TouchableOpacity key={q} style={styles.chip} onPress={() => { setInput(q); }}>
                  <Text style={styles.chipText}>{q}</Text>
                </TouchableOpacity>
              ))}
            </View>
          </View>
        }
      />

      {(sttLoading || voiceMode) && (
        <View style={[styles.sttBanner, voiceMode && styles.sttBannerActive]}>
          <Ionicons name={voiceMode ? "mic" : "mic"} size={14} color={COLORS.primary} />
          <Text style={styles.sttText}>{voiceMode ? 'Listening... Speak now' : 'Transcribing...'}</Text>
        </View>
      )}

      <View style={styles.inputRow}>
        <Animated.View style={recording ? { transform: [{ scale: pulseAnim }] } : undefined}>
          <TouchableOpacity
            style={[styles.micBtn, recording && styles.micBtnActive, voiceMode && styles.micBtnVoice]}
            onPress={recording ? stopRecording : startRecording}
          >
            <Ionicons name={recording ? "stop" : "mic"} size={18} color={recording ? '#ff5555' : voiceMode ? COLORS.background : COLORS.primary} />
          </TouchableOpacity>
        </Animated.View>
        <TextInput
          style={styles.input}
          placeholder={voiceMode ? "Voice mode active..." : "Message ZIO..."}
          placeholderTextColor={COLORS.textMuted}
          value={input}
          onChangeText={setInput}
          multiline
          maxLength={2000}
          editable={!voiceMode}
        />
        <TouchableOpacity
          style={[styles.sendBtn, (!input.trim() || isLoading) && styles.sendBtnDisabled]}
          onPress={handleSendWithVoice}
          disabled={!input.trim() || isLoading}
        >
          <Ionicons name={isLoading ? "sync" : "arrow-up"} size={20} color={COLORS.background} />
        </TouchableOpacity>
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: COLORS.background },
  scanlines: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: 'transparent',
    opacity: 0.03,
    borderBottomWidth: 1,
    borderColor: COLORS.primary,
  },
  header: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between',
    padding: SPACING.md, borderBottomWidth: 1, borderBottomColor: COLORS.border,
    backgroundColor: COLORS.surface,
  },
  headerLeft: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  avatar: {
    width: 38, height: 38, borderRadius: 19, backgroundColor: COLORS.primaryDim,
    borderWidth: 1.5, borderColor: COLORS.primary, justifyContent: 'center', alignItems: 'center',
  },
  avatarText: { fontSize: 17, fontWeight: '800', color: COLORS.primary },
  headerTitle: { fontSize: 14, fontWeight: '700', color: COLORS.text },
  statusRow: { flexDirection: 'row', alignItems: 'center', gap: 4, marginTop: 1 },
  statusDot: { width: 6, height: 6, borderRadius: 3 },
  statusOnline: { backgroundColor: COLORS.success },
  statusThinking: { backgroundColor: COLORS.warning },
  headerSub: { fontSize: 10, color: COLORS.textSecondary },
  headerActions: { flexDirection: 'row', gap: 6 },
  headerBtn: {
    width: 32, height: 32, borderRadius: 16, justifyContent: 'center', alignItems: 'center',
    borderWidth: 1, borderColor: COLORS.border, backgroundColor: COLORS.background,
  },
  headerBtnActive: { backgroundColor: COLORS.primary, borderColor: COLORS.primary },
  cameraContainer: {
    height: 200, marginHorizontal: SPACING.md, marginTop: SPACING.sm,
    borderRadius: RADIUS.md, overflow: 'hidden', borderWidth: 1, borderColor: COLORS.primary,
  },
  cameraView: { flex: 1 },
  cameraOverlay: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  cameraCornerTL: { position: 'absolute', top: 8, left: 8, width: 20, height: 20, borderTopWidth: 2, borderLeftWidth: 2, borderColor: COLORS.primary },
  cameraCornerTR: { position: 'absolute', top: 8, right: 8, width: 20, height: 20, borderTopWidth: 2, borderRightWidth: 2, borderColor: COLORS.primary },
  cameraCornerBL: { position: 'absolute', bottom: 8, left: 8, width: 20, height: 20, borderBottomWidth: 2, borderLeftWidth: 2, borderColor: COLORS.primary },
  cameraCornerBR: { position: 'absolute', bottom: 8, right: 8, width: 20, height: 20, borderBottomWidth: 2, borderRightWidth: 2, borderColor: COLORS.primary },
  cameraLabel: {
    position: 'absolute', top: 8, alignSelf: 'center',
    fontSize: 9, fontWeight: '700', color: COLORS.primary, letterSpacing: 2,
    backgroundColor: 'rgba(0,0,0,0.6)', paddingHorizontal: 8, paddingVertical: 2, borderRadius: 4,
  },
  captureBtn: {
    width: 56, height: 56, borderRadius: 28, backgroundColor: 'rgba(0,229,255,0.15)',
    borderWidth: 2, borderColor: COLORS.primary, justifyContent: 'center', alignItems: 'center',
  },
  messageList: { padding: SPACING.md, paddingBottom: 8 },
  bubble: { maxWidth: '82%', marginBottom: SPACING.sm, padding: 12, borderRadius: RADIUS.md },
  bubbleUser: { alignSelf: 'flex-end', backgroundColor: COLORS.primaryDim, borderWidth: 1, borderColor: 'rgba(0,229,255,0.2)' },
  bubbleAssistant: { alignSelf: 'flex-start', backgroundColor: COLORS.surface, borderWidth: 1, borderColor: COLORS.border },
  botLabel: { flexDirection: 'row', alignItems: 'center', gap: 4, marginBottom: 4 },
  botName: { fontSize: 9, fontWeight: '700', color: COLORS.accent, letterSpacing: 1 },
  bubbleText: { fontSize: 13, color: COLORS.text, lineHeight: 18 },
  bubbleTextUser: { color: COLORS.primary },
  cursor: { color: COLORS.primary, fontWeight: '300' },
  speakBtn: { marginTop: 6, alignSelf: 'flex-end', padding: 4 },
  empty: { alignItems: 'center', paddingTop: 80 },
  emptyHex: {
    width: 72, height: 72, borderRadius: 16, backgroundColor: COLORS.primaryDim,
    borderWidth: 1, borderColor: COLORS.primary, justifyContent: 'center', alignItems: 'center',
    marginBottom: 16,
  },
  emptyZ: { fontSize: 32, fontWeight: '900', color: COLORS.primary },
  emptyText: { fontSize: 16, fontWeight: '600', color: COLORS.textSecondary },
  emptySub: { fontSize: 11, color: COLORS.textMuted, marginTop: 4 },
  chips: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginTop: 16, justifyContent: 'center' },
  chip: {
    paddingHorizontal: 12, paddingVertical: 6, borderRadius: 12,
    backgroundColor: COLORS.primaryDim, borderWidth: 1, borderColor: 'rgba(0,229,255,0.2)',
  },
  chipText: { fontSize: 11, color: COLORS.primary },
  sttBanner: {
    flexDirection: 'row', alignItems: 'center', gap: 6, padding: 8,
    backgroundColor: COLORS.primaryDim, marginHorizontal: SPACING.md, borderRadius: 8, marginBottom: 4,
  },
  sttBannerActive: {
    backgroundColor: 'rgba(0,229,255,0.25)',
    borderWidth: 1, borderColor: COLORS.primary,
  },
  sttText: { fontSize: 11, color: COLORS.primary },
  inputRow: {
    flexDirection: 'row', alignItems: 'flex-end', gap: 8,
    padding: SPACING.md, borderTopWidth: 1, borderTopColor: COLORS.border,
    backgroundColor: COLORS.surface,
  },
  micBtn: {
    width: 40, height: 40, borderRadius: 20, borderWidth: 1, borderColor: COLORS.border,
    backgroundColor: COLORS.background, justifyContent: 'center', alignItems: 'center',
  },
  micBtnActive: { borderColor: '#ff5555', backgroundColor: 'rgba(255,85,85,0.1)' },
  micBtnVoice: { backgroundColor: COLORS.primary, borderColor: COLORS.primary },
  input: {
    flex: 1, backgroundColor: COLORS.background, borderWidth: 1, borderColor: COLORS.border,
    borderRadius: RADIUS.lg, paddingHorizontal: 16, paddingVertical: 10, color: COLORS.text,
    fontSize: 13, maxHeight: 100,
  },
  sendBtn: {
    width: 40, height: 40, borderRadius: 20, backgroundColor: COLORS.primary,
    justifyContent: 'center', alignItems: 'center',
  },
  sendBtnDisabled: { opacity: 0.4 },
  inlineMedia: {
    marginTop: 8, borderTopWidth: 1, borderTopColor: COLORS.border, paddingTop: 8,
  },
  mediaImage: {
    width: 280, height: 200, borderRadius: 8,
  },
  audioPlayer: {
    flexDirection: 'row', alignItems: 'center', gap: 8,
    backgroundColor: COLORS.background, padding: 8, borderRadius: 8,
    borderWidth: 1, borderColor: COLORS.border,
  },
  audioLabel: { fontSize: 12, color: COLORS.text },
  mediaLink: {
    fontSize: 12, color: COLORS.accent, marginTop: 8,
    backgroundColor: COLORS.background, padding: 8, borderRadius: 8,
    borderWidth: 1, borderColor: COLORS.border, overflow: 'hidden',
  },
});
