import { useEffect, useRef, useState } from "react";
import { View, Alert, KeyboardAvoidingView, Platform } from "react-native";
import { SafeAreaView, SafeAreaProvider } from "react-native-safe-area-context";
import { useCameraPermissions } from "expo-camera";

import { BACKEND_HTTP, BACKEND_WS } from "./config";
import { styles } from "./styles/app.styles";

import PhotoViewer from "./components/PhotoViewer";
import MessageList from "./components/MessageList";
import ChatInput from "./components/ChatInput";
import IconButton from "./components/IconButton";
import CameraModal from "./components/CameraModal";
import BrowseModal from "./components/BrowseModal";

export default function App() {
  const socketRef = useRef(null);
  const [messages, setMessages] = useState([]);
  const [inputText, setInputText] = useState("");
  const [author] = useState("Device");
  const [currentPhotoUrl, setCurrentPhotoUrl] = useState(null);
  const [cameraModalVisible, setCameraModalVisible] = useState(false);
  const [browseModalVisible, setBrowseModalVisible] = useState(false);
  const [, requestCameraPermission] = useCameraPermissions();

  // Pending capture — set after a photo is taken, cleared after query
  const [pendingCapture, setPendingCapture] = useState(null);
  const [querying, setQuerying] = useState(false);

  // ── Load history on mount ──
  useEffect(() => {
    const loadHistory = async () => {
      try {
        const res = await fetch(`${BACKEND_HTTP}/history`);
        if (res.ok) {
          const json = await res.json();
          if (json.messages?.length) setMessages(json.messages);
        }
      } catch (err) {
        console.log("Could not load history:", err);
      }
    };
    loadHistory();
  }, []);

  // ── WebSocket ──
  useEffect(() => {
    const socket = new WebSocket(BACKEND_WS);
    socketRef.current = socket;

    socket.onopen = () => console.log("WebSocket connected");

    socket.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        if (msg.type === "photo_select") {
          if (msg.url) setCurrentPhotoUrl(msg.url);
          addMessage({
            type: "system",
            text: `${msg.author ?? "Someone"} selected a new photo`,
            timestamp: msg.timestamp,
          });
        } else {
          setMessages((prev) => [...prev, msg]);
        }
      } catch (err) {
        console.log("Error parsing message:", err);
      }
    };

    socket.onerror = (err) => console.log("WebSocket error:", err.message || err);
    socket.onclose = (e) => console.log("WebSocket closed:", e.code, e.reason);

    return () => socket.close();
  }, []);

  // ── Helpers ──
  const addMessage = (msg) =>
    setMessages((prev) => [...prev, { ...msg, timestamp: msg.timestamp ?? new Date().toISOString() }]);

  const broadcastPhotoSelection = (fullUrl) => {
    if (socketRef.current?.readyState !== 1) return;
    socketRef.current.send(JSON.stringify({
      type: "photo_select",
      author,
      url: fullUrl,
      timestamp: new Date().toISOString(),
    }));
  };

  // ── Send message — routes to RAG query if capture is pending ──
  const sendTextMessage = async () => {
    const trimmed = inputText.trim();
    if (!trimmed) return;

    if (pendingCapture) {
      await sendRagQuery(trimmed);
      return;
    }

    if (socketRef.current?.readyState !== 1) return;
    socketRef.current.send(JSON.stringify({
      type: "text",
      author,
      text: trimmed,
      timestamp: new Date().toISOString(),
    }));
    setInputText("");
  };

  // ── RAG query — search KB, show results (no LLM yet) ──
  const sendRagQuery = async (userQuery) => {
    setQuerying(true);
    setInputText("");

    addMessage({ type: "text", author, text: userQuery });

    if (pendingCapture.ocrText) {
      addMessage({
        type: "system",
        text: `OCR: "${pendingCapture.ocrText.slice(0, 100)}${pendingCapture.ocrText.length > 100 ? "…" : ""}"`,
      });
    }

    addMessage({ type: "system", text: "Searching knowledge base..." });

    try {
      const res = await fetch(`${BACKEND_HTTP}/search`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query: userQuery,
          ocr_text: pendingCapture.ocrText ?? "",
        }),
      });

      if (!res.ok) {
        addMessage({ type: "system", text: "Search failed. Check that the backend is running." });
        return;
      }

      const json = await res.json();

      if (json.context_status === "none") {
        addMessage({
          type: "system",
          text: "No matching documents found in the knowledge base.",
        });
        addMessage({
          type: "text",
          author: "System",
          text: "⚠️ No knowledge base results — LLM integration coming in the next phase.",
        });
      } else {
        addMessage({
          type: "system",
          text: `Found ${json.result_count} result(s) from: ${json.sources.join(", ")}`,
        });

        // Show each context chunk as a message
        json.results.forEach((chunk, i) => {
          addMessage({
            type: "text",
            author: `📄 ${chunk.source}`,
            text: chunk.content,
          });
        });

        addMessage({
          type: "system",
          text: "LLM integration coming in the next phase — context retrieved successfully.",
        });
      }
    } catch (err) {
      console.error("RAG search error:", err);
      addMessage({ type: "system", text: "Could not reach the backend." });
    } finally {
      setQuerying(false);
      setPendingCapture(null);
    }
  };

  // ── Camera ──
  const openCamera = async () => {
    const permission = await requestCameraPermission();
    if (!permission.granted) {
      Alert.alert("Permission required", "Camera permission is needed to take photos.");
      return;
    }
    setCameraModalVisible(true);
  };

  const handlePhotoCaptured = ({ photoUrl, ocrText, imageBase64 }) => {
    setCurrentPhotoUrl(photoUrl);
    broadcastPhotoSelection(photoUrl);
    setPendingCapture({ photoUrl, ocrText, imageBase64 });

    addMessage({
      type: "system",
      text: ocrText
        ? `Photo captured · OCR found text (${ocrText.length} chars) · Type your question`
        : "Photo captured · No text detected · Type your question to search the knowledge base",
    });
  };

  const handlePhotoSelected = (fullUrl) => {
    setCurrentPhotoUrl(fullUrl);
    broadcastPhotoSelection(fullUrl);
  };

  return (
    <SafeAreaProvider>
      <SafeAreaView style={styles.safeArea}>
        <KeyboardAvoidingView
          style={styles.container}
          behavior={Platform.OS === "ios" ? "padding" : "height"}
          keyboardVerticalOffset={Platform.OS === "ios" ? 0 : 24}
        >
          <PhotoViewer photoUrl={currentPhotoUrl} />

          <View style={styles.chatContainer}>
            <MessageList messages={messages} />
          </View>

          <View style={styles.bottomBar}>
            <View style={styles.buttonRow}>
              <IconButton label="📷  Camera" onPress={openCamera} />
              <IconButton label="🖼  Browse" onPress={() => setBrowseModalVisible(true)} />
              {pendingCapture && (
                <IconButton
                  label="✕  Clear"
                  variant="primary"
                  onPress={() => {
                    setPendingCapture(null);
                    setInputText("");
                  }}
                />
              )}
            </View>
            <ChatInput
              value={inputText}
              onChangeText={setInputText}
              onSend={sendTextMessage}
              placeholder={pendingCapture ? "Ask a question about the photo..." : "Type a message..."}
              disabled={querying}
            />
          </View>

          <CameraModal
            visible={cameraModalVisible}
            onClose={() => setCameraModalVisible(false)}
            onPhotoCaptured={handlePhotoCaptured}
          />

          <BrowseModal
            visible={browseModalVisible}
            onClose={() => setBrowseModalVisible(false)}
            onSelectPhoto={handlePhotoSelected}
          />
        </KeyboardAvoidingView>
      </SafeAreaView>
    </SafeAreaProvider>
  );
}