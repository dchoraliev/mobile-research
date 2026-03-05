import { useEffect, useRef, useState } from "react";
import { View, Text, TextInput, Button, FlatList } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { styles } from "./styles/echo.styles";

//  IMPORTANT: adjust this address based on how you run it
// For Android emulator: ws://10.0.2.2:8089/ws
// For same machine (web preview): ws://localhost:8089/ws
// For real device: ws://YOUR_LOCAL_IP:8089/ws
const WS_URL = "ws://10.0.2.2:8089/ws";

export default function App() {
  const ws = useRef(null);

  const [isConnected, setIsConnected] = useState(false);
  const [inputText, setInputText] = useState("");
  const [messages, setMessages] = useState([]);

  // Connect to WebSocket when component mounts
  useEffect(() => {
    connectWebSocket();

    // Cleanup on unmount
    return () => {
      if (ws.current) {
        ws.current.close();
      }
    };
  }, []);

  const connectWebSocket = () => {
    // Close previous connection if any
    ws.current?.close();

    console.log("Connecting to:", WS_URL);
    ws.current = new WebSocket(WS_URL);

    ws.current.onopen = () => {
      console.log("WebSocket connected");
      setIsConnected(true);
      addMessage("system", "Connected to server");
    };

    ws.current.onmessage = (event) => {
      console.log("Received:", event.data);
      addMessage("server", event.data);
    };

    ws.current.onerror = (error) => {
      console.log("WebSocket error:", error.message);
      addMessage("system", "WebSocket error. See console.");
    };

    ws.current.onclose = () => {
      console.log("WebSocket closed");
      setIsConnected(false);
      addMessage("system", "Disconnected from server ");
    };
  };

  const addMessage = (from, text) => {
    setMessages((prev) => [
      ...prev,
      {
        id: Date.now().toString() + Math.random().toString(),
        from,
        text,
      },
    ]);
  };

  const sendMessage = () => {
    // line 74 fix: optional chaining instead of !ws.current || ws.current.readyState
    if (ws.current?.readyState !== WebSocket.OPEN) {
      addMessage("system", "Not connected. Trying to reconnect...");
      connectWebSocket();
      return;
    }

    if (!inputText.trim()) return;

    const msg = inputText.trim();
    // Add locally
    addMessage("me", msg);
    // Send to server
    ws.current.send(msg);
    setInputText("");
  };

  // lines 107-109 fix: extract nested ternary into independent helper
  const getMessageStyle = (from) => {
    if (from === "me") return styles.myMessage;
    if (from === "server") return styles.serverMessage;
    return styles.systemMessage;
  };

  return (
    <SafeAreaView style={styles.container}>
      <Text style={styles.title}>React Native + FastAPI WebSocket</Text>
      <Text style={styles.status}>
        Status: {isConnected ? "😃 Connected" : "😔 Disconnected"}
      </Text>

      <View style={styles.messagesContainer}>
        <FlatList
          data={messages}
          keyExtractor={(item) => item.id}
          renderItem={({ item }) => (
            <View style={[styles.messageBubble, getMessageStyle(item.from)]}>
              <Text style={styles.messageFrom}>{item.from.toUpperCase()}:</Text>
              <Text style={styles.messageText}>{item.text}</Text>
            </View>
          )}
        />
      </View>

      <View style={styles.inputRow}>
        <TextInput
          style={styles.input}
          placeholder="Type a message..."
          value={inputText}
          onChangeText={setInputText}
        />
        <Button title="Send" onPress={sendMessage} />
      </View>

      <View style={styles.buttonRow}>
        <Button title="Reconnect" onPress={connectWebSocket} />
      </View>
    </SafeAreaView>
  );
}


