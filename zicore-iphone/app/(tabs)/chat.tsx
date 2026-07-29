import { useState, useRef, useEffect } from 'react';
import {
  View, Text, TextInput, TouchableOpacity, FlatList, StyleSheet,
  KeyboardAvoidingView, Platform, Animated,
} from 'react-native';
import { Audio } from 'expo-av';
import * as FileSystem from 'expo-file-system';
import { useChatStore } from '@/stores/chatStore';
import { Ionicons } from '@expo/vector-icons';
import { COLORS, SPACING, RADIUS, haptic } from '@/theme/colors';
import { BASE_URL } from '@/lib/api';
import { authStorage } from '@/lib/auth';
import { SafeAreaView } from 'react-native-safe-area-context';

interface MessageProps {
  role: 'user' | 'assistant';
  content: string;
  onSpeak?: () => void;
  speaking?: boolean;
  streaming?: boolean;
}

function MessageBubble({ role, content, onSpeak, speaking, streaming }: MessageProps & { streaming?: boolean }) {
  const isUser = role === 'user';
  return (
    <View style={[styles.bubble, isUser ? styles.bubbleUser : styles.bubbleAssistant]}>
      {!isUser && (
        <View style={styles.botLabel}>
          <Ionicons name="hardware-chip-outline" size={10} color={COLORS.accent} />
          <Text style={styles.botName}>ZIO</Text>
        </View>
      )}
      <Text style={[styles.bubbleText, isUser && styles.bubbleTextUser]}>
        {content}
        {streaming && <Text style={styles.cursor}>|</Text>}
      </Text>
      {!isUser && onSpeak && (
        <TouchableOpacity style={styles.speakBtn} onPress={() => { haptic.light(); onSpeak(); }}>
          <Ionicons name={speaking ? "volume-high" : "volume-medium-outline"} size={14} color={COLORS.primary} />
        </TouchableOpacity>
      )}
    </View>
  );
}

export default function ChatScreen() {
  const { messages, isLoading, sendMessage, clearMessages } = useChatStore();
  const [input, setInput] = useState('');
  const [recording, setRecording] = useState(false);
  const [sttLoading, setSttLoading] = useState(false);
  const [speakingId, setSpeakingId] = useState<string | null>(null);
  const flatListRef = useRef<FlatList>(null);
  const pulseAnim = useRef(new Animated.Value(1)).current;

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

  const handleSend = async () => {
    const text = input.trim();
    if (!text || isLoading) return;
    haptic.light();
    setInput('');
    await sendMessage(text);
  };

  const startRecording = async () => {
    try {
      const { status } = await Audio.requestPermissionsAsync();
      if (status !== 'granted') return;
      await Audio.setAudioModeAsync({ allowsRecordingIOS: true, playsInSilentModeIOS: true });
      const rec = await Audio.Recording.createAsync(
        Audio.RecordingOptionsPresets.HIGH_QUALITY
      );
      haptic.medium();
      setRecording(true);
      (global as any).__zicoreIphoneRecording = rec;
    } catch (e) {
      console.log('Recording error:', e);
    }
  };

  const stopRecording = async () => {
    try {
      setRecording(false);
      haptic.light();
      const rec = (global as any).__zicoreIphoneRecording;
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
      }
    } catch (e) {
      setSttLoading(false);
      console.log('STT error:', e);
    }
  };

  const speakText = async (text: string, msgId: string) => {
    try {
      setSpeakingId(msgId);
      const token = await authStorage.getToken();
      const response = await fetch(`${BASE_URL}/api/tts`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ text: text.substring(0, 500), lang: 'es' }),
      });
      if (!response.ok) throw new Error('TTS failed');
      const blob = await response.blob();
      const reader = new FileReader();
      reader.onload = async () => {
        const base64 = (reader.result as string).split(',')[1];
        const fileUri = FileSystem.cacheDirectory + 'zio_tts_iphone.mp3';
        await FileSystem.writeAsStringAsync(fileUri, base64, { encoding: FileSystem.EncodingType.Base64 });
        const { sound } = await Audio.Sound.createAsync({ uri: fileUri });
        await sound.playAsync();
        sound.setOnPlaybackStatusUpdate((status) => {
          if (status.isLoaded && status.didJustFinish) {
            setSpeakingId(null);
            sound.unloadAsync();
          }
        });
      };
      reader.readAsDataURL(blob);
    } catch (e) {
      setSpeakingId(null);
      console.log('TTS error:', e);
    }
  };

  return (
    <SafeAreaView style={styles.safeContainer} edges={['top']}>
      <KeyboardAvoidingView
        style={styles.container}
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
        keyboardVerticalOffset={Platform.OS === 'ios' ? 0 : 90}
      >
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
                <Text style={styles.headerSub}>{isLoading ? 'Thinking...' : 'Online'}</Text>
              </View>
            </View>
          </View>
          <TouchableOpacity onPress={() => { haptic.selection(); clearMessages(); }} style={styles.clearBtn}>
            <Ionicons name="trash-outline" size={18} color={COLORS.textMuted} />
          </TouchableOpacity>
        </View>

        <FlatList
          ref={flatListRef}
          data={messages}
          keyExtractor={(item) => item.id}
          renderItem={({ item }) => (
            <MessageBubble
              role={item.role}
              content={item.content}
              onSpeak={item.role === 'assistant' ? () => speakText(item.content, item.id) : undefined}
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
              <Text style={styles.emptySub}>Aerospace engineering, coding, missions...</Text>
              <View style={styles.chips}>
                {['Calculate delta-v', 'Mission planning', 'Explain orbits'].map((q) => (
                  <TouchableOpacity key={q} style={styles.chip} onPress={() => { haptic.selection(); setInput(q); }}>
                    <Text style={styles.chipText}>{q}</Text>
                  </TouchableOpacity>
                ))}
              </View>
            </View>
          }
        />

        {sttLoading && (
          <View style={styles.sttBanner}>
            <Ionicons name="mic" size={14} color={COLORS.primary} />
            <Text style={styles.sttText}>Transcribing audio...</Text>
          </View>
        )}

        <View style={styles.inputRow}>
          <Animated.View style={recording ? { transform: [{ scale: pulseAnim }] } : undefined}>
            <TouchableOpacity
              style={[styles.micBtn, recording && styles.micBtnActive]}
              onPress={recording ? stopRecording : startRecording}
            >
              <Ionicons name={recording ? "stop" : "mic"} size={18} color={recording ? '#ff5555' : COLORS.primary} />
            </TouchableOpacity>
          </Animated.View>
          <TextInput
            style={styles.input}
            placeholder="Message ZIO..."
            placeholderTextColor={COLORS.textMuted}
            value={input}
            onChangeText={setInput}
            multiline
            maxLength={2000}
          />
          <TouchableOpacity
            style={[styles.sendBtn, (!input.trim() || isLoading) && styles.sendBtnDisabled]}
            onPress={handleSend}
            disabled={!input.trim() || isLoading}
          >
            <Ionicons name={isLoading ? "sync" : "arrow-up"} size={20} color={COLORS.background} />
          </TouchableOpacity>
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeContainer: { flex: 1, backgroundColor: COLORS.background },
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
  clearBtn: { padding: 8 },
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
});
