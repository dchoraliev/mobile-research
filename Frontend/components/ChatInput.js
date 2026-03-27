import { View, TextInput, TouchableOpacity, Text } from "react-native";
import { chatInputStyles as styles } from "../styles/chatInput.styles";

export default function ChatInput({ value, onChangeText, onSend, placeholder, disabled }) {
  return (
    <View style={styles.row}>
      <TextInput
        style={styles.input}
        value={value}
        onChangeText={onChangeText}
        placeholder={placeholder ?? "Type a message..."}
        placeholderTextColor="#555"
        returnKeyType="send"
        onSubmitEditing={onSend}
        editable={!disabled}
      />
      <TouchableOpacity
        style={[styles.sendButton, disabled && styles.sendButtonDisabled]}
        onPress={onSend}
        activeOpacity={0.8}
        disabled={disabled}
      >
        <Text style={styles.sendText}>{disabled ? "..." : "Send"}</Text>
      </TouchableOpacity>
    </View>
  );
}