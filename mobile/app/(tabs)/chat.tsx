import { useState, useRef, useEffect } from 'react';
import { View, Text, TextInput, TouchableOpacity, FlatList, StyleSheet, KeyboardAvoidingView, Platform } from 'react-native';
import { useChatStore } from '@/stores/chatStore';
import { Ionicons } from '@expo/vector-icons';
import { COLORS, SPACING, RADIUS } from '@/theme/colors';

interface MessageProps {
  role: 'user' | 'assistant';
  content: string;
}

function MessageBubble({ role, content }: MessageProps) {
  const isUser = role === 'user';
  return (
    <View style={[styles.bubble, isUser ? styles.bubbleUser : styles.bubbleAssistant]}>
      {!isUser && <Text style={styles.botName}>ZIO</Text>}
      <Text style={[styles.bubbleText, isUser && styles.bubbleTextUser]}>{content}</Text>
    </View>
  );
}

export default function ChatScreen() {
  const { messages, isLoading, sendMessage, clearMessages } = useChatStore();
  const [input, setInput] = useState('');
  const flatListRef = useRef<FlatList>(null);

  useEffect(() => {
    flatListRef.current?.scrollToEnd({ animated: true });
  }, [messages]);

  const handleSend = async () => {
    const text = input.trim();
    if (!text || isLoading) return;
    setInput('');
    await sendMessage(text);
  };

  return (
    <KeyboardAvoidingView style={styles.container} behavior={Platform.OS === 'ios' ? 'padding' : undefined} keyboardVerticalOffset={90}>
      {/* Header */}
      <View style={styles.header}>
        <View style={styles.headerLeft}>
          <View style={styles.avatar}>
            <Text style={styles.avatarText}>Z</Text>
          </View>
          <View>
            <Text style={styles.headerTitle}>ZIO AI</Text>
            <Text style={styles.headerSub}>{isLoading ? 'Thinking...' : 'Online'}</Text>
          </View>
        </View>
        <TouchableOpacity onPress={clearMessages} style={styles.clearBtn}>
          <Ionicons name="trash-outline" size={18} color={COLORS.textMuted} />
        </TouchableOpacity>
      </View>

      {/* Messages */}
      <FlatList
        ref={flatListRef}
        data={messages}
        keyExtractor={(item) => item.id}
        renderItem={({ item }) => <MessageBubble role={item.role} content={item.content} />}
        contentContainerStyle={styles.messageList}
        ListEmptyComponent={
          <View style={styles.empty}>
            <Text style={styles.emptyIcon}>🤖</Text>
            <Text style={styles.emptyText}>Ask ZIO anything</Text>
            <Text style={styles.emptySub}>Aerospace engineering, coding, missions...</Text>
          </View>
        }
      />

      {/* Input */}
      <View style={styles.inputRow}>
        <TextInput
          style={styles.input}
          placeholder="Message ZIO..."
          placeholderTextColor={COLORS.textMuted}
          value={input}
          onChangeText={setInput}
          multiline
          maxLength={2000}
        />
        <TouchableOpacity style={[styles.sendBtn, (!input.trim() || isLoading) && styles.sendBtnDisabled]} onPress={handleSend} disabled={!input.trim() || isLoading}>
          <Ionicons name="arrow-up" size={20} color={COLORS.background} />
        </TouchableOpacity>
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: COLORS.background },
  header: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between',
    padding: SPACING.md, borderBottomWidth: 1, borderBottomColor: COLORS.border,
    backgroundColor: COLORS.surface,
  },
  headerLeft: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  avatar: {
    width: 36, height: 36, borderRadius: 18, backgroundColor: COLORS.primaryDim,
    borderWidth: 1, borderColor: COLORS.primary, justifyContent: 'center', alignItems: 'center',
  },
  avatarText: { fontSize: 16, fontWeight: '800', color: COLORS.primary },
  headerTitle: { fontSize: 14, fontWeight: '700', color: COLORS.text },
  headerSub: { fontSize: 10, color: COLORS.textSecondary },
  clearBtn: { padding: 8 },
  messageList: { padding: SPACING.md, paddingBottom: 8 },
  bubble: { maxWidth: '80%', marginBottom: SPACING.sm, padding: 12, borderRadius: RADIUS.md },
  bubbleUser: { alignSelf: 'flex-end', backgroundColor: COLORS.primaryDim, borderWidth: 1, borderColor: 'rgba(0,229,255,0.2)' },
  bubbleAssistant: { alignSelf: 'flex-start', backgroundColor: COLORS.surface, borderWidth: 1, borderColor: COLORS.border },
  botName: { fontSize: 9, fontWeight: '700', color: COLORS.accent, letterSpacing: 1, marginBottom: 4 },
  bubbleText: { fontSize: 13, color: COLORS.text, lineHeight: 18 },
  bubbleTextUser: { color: COLORS.primary },
  empty: { alignItems: 'center', paddingTop: 100 },
  emptyIcon: { fontSize: 48, marginBottom: 12 },
  emptyText: { fontSize: 16, fontWeight: '600', color: COLORS.textSecondary },
  emptySub: { fontSize: 11, color: COLORS.textMuted, marginTop: 4 },
  inputRow: {
    flexDirection: 'row', alignItems: 'flex-end', gap: 8,
    padding: SPACING.md, borderTopWidth: 1, borderTopColor: COLORS.border,
    backgroundColor: COLORS.surface,
  },
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
