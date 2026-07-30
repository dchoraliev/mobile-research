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
import { SCENARIO, SHOW_DEBUG_CHUNKS, SCENARIOS_WITH_IMAGE, SCENARIOS_WITH_CAPTION } from "./scenarios";

export default function App() {
  const socketRef = useRef(null);
  const [messages, setMessages] = useState([]);
  const [inputText, setInputText] = useState("");
  const [author] = useState("Device");
  const [currentPhotoUrl, setCurrentPhotoUrl] = useState(null);
  const [cameraModalVisible, setCameraModalVisible] = useState(false);
  const [browseModalVisible, setBrowseModalVisible] = useState(false);
  const [, requestCameraPermission] = useCameraPermissions();

  const [pendingCapture, setPendingCapture] = useState(null);
  const [querying, setQuerying] = useState(false);

  // ── WebSocket ──────────────────────────────────────────────────────────────
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
    socket.onclose = (e)   => console.log("WebSocket closed:", e.code, e.reason);

    return () => socket.close();
  }, []);

  // ── Helpers ────────────────────────────────────────────────────────────────
  const addMessage = (msg) =>
    setMessages((prev) => [
      ...prev,
      { ...msg, timestamp: msg.timestamp ?? new Date().toISOString() },
    ]);

  const broadcastPhotoSelection = (fullUrl) => {
    if (socketRef.current?.readyState !== 1) return;
    socketRef.current.send(
      JSON.stringify({
        type: "photo_select",
        author,
        url: fullUrl,
        timestamp: new Date().toISOString(),
      }),
    );
  };

  // ── Shared fetch — attaches X-Scenario header to every request ────────────
  const scenarioFetch = (url, options = {}) =>
    fetch(url, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        "X-Scenario": SCENARIO,
        ...(options.headers ?? {}),
      },
    });

  // ── Send message ───────────────────────────────────────────────────────────
  const sendTextMessage = async () => {
    const trimmed = inputText.trim();
    if (!trimmed) return;
    const capture = pendingCapture ?? {
      photoUrl: null, ocrText: "", captionText: "", imageBase64: null, ocrMs: null, captionMs: null,
    };
    await sendRagQuery(trimmed, capture);
  };

  // ── RAG query ──────────────────────────────────────────────────────────────
  const sendRagQuery = async (userQuery, capture) => {
    setQuerying(true);
    setInputText("");

    addMessage({ type: "text", author, text: userQuery });

    if (capture.ocrText) {
      addMessage({
        type: "system",
        text: `OCR: "${capture.ocrText.slice(0, 100)}${capture.ocrText.length > 100 ? "…" : ""}"`,
      });
    }

    if (capture.captionText) {
      addMessage({
        type: "system",
        text: `Caption (BLIP): "${capture.captionText}"`,
      });
    }

    addMessage({ type: "system", text: `Thinking... [${SCENARIO}]` });

    try {
      const headers = {};
      if (capture.ocrMs != null) headers["X-OCR-Ms"] = String(capture.ocrMs);
      if (capture.captionMs != null) headers["X-Caption-Ms"] = String(capture.captionMs);

      const sendImage = SCENARIOS_WITH_IMAGE.includes(SCENARIO);
      const res = await scenarioFetch(`${BACKEND_HTTP}/search`, {
        method: "POST",
        headers,
        body: JSON.stringify({
          query:        userQuery,
          ocr_text:     capture.ocrText ?? "",
          caption_text: capture.captionText ?? "",
          image_base64: sendImage ? (capture.imageBase64 ?? null) : null,
        }),
      });

      if (!res.ok) {
        addMessage({ type: "system", text: "Search failed. Check that the backend is running." });
        return;
      }

      const json = await res.json();

      // Show sources only when retrieval found something
      if (json.context_status === "found" && json.sources?.length > 0) {
        addMessage({
          type: "system",
          text: `Sources: ${json.sources.join(", ")}`,
        });
      }

      // Always show the answer — grounded or conversational
      if (json.answer) {
        addMessage({ type: "text", author: "Assistant", text: json.answer });
      }

      // Debug chunks — flip SHOW_DEBUG_CHUNKS to true during scenario testing
      if (SHOW_DEBUG_CHUNKS && json.results?.length > 0) {
        json.results.forEach((chunk) => {
          addMessage({
            type: "text",
            author: `📄 ${chunk.source} (${chunk.score})`,
            text: chunk.content,
          });
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

  // ── Camera ─────────────────────────────────────────────────────────────────
  const openCamera = async () => {
    const permission = await requestCameraPermission();
    if (!permission.granted) {
      Alert.alert("Permission required", "Camera permission is needed to take photos.");
      return;
    }
    setCameraModalVisible(true);
  };

  const handlePhotoCaptured = ({ photoUrl, ocrText, captionText, imageBase64, ocrMs, captionMs }) => {
    setCurrentPhotoUrl(photoUrl);
    broadcastPhotoSelection(photoUrl);
    setPendingCapture({ photoUrl, ocrText, captionText, imageBase64, ocrMs, captionMs });
    addMessage({
      type: "system",
      text: captionText
        ? `Photo captured · Caption (BLIP): "${captionText}" · Type your question`
        : ocrText
          ? `Photo captured · OCR found text (${ocrText.length} chars) · Type your question`
          : "Photo captured · No text detected · Type your question to search the knowledge base",
    });
  };

  const handlePhotoSelected = async ({ fullUrl, filename }) => {
    setCurrentPhotoUrl(fullUrl);
    broadcastPhotoSelection(fullUrl);

    const useCaption = SCENARIOS_WITH_CAPTION.includes(SCENARIO);
    addMessage({
      type: "system",
      text: useCaption ? "Photo selected · Generating caption (BLIP)..." : "Photo selected · Running OCR...",
    });

    let ocrText = "";
    let captionText = "";
    let ocrMs = null;
    let captionMs = null;
    const start = Date.now();
    try {
      const endpoint = useCaption ? "/caption-from-stored" : "/ocr-from-stored";
      const res = await scenarioFetch(`${BACKEND_HTTP}${endpoint}`, {
        method: "POST",
        body: JSON.stringify({ filename }),
      });
      const json = await res.json();
      if (useCaption) captionText = json.caption ?? "";
      else ocrText = json.text ?? "";
    } catch (err) {
      console.log(`${useCaption ? "Caption" : "OCR"} from stored failed (non-fatal):`, err);
    } finally {
      if (useCaption) captionMs = Date.now() - start;
      else ocrMs = Date.now() - start;
    }

    setPendingCapture({ photoUrl: fullUrl, ocrText, captionText, imageBase64: null, ocrMs, captionMs });
    addMessage({
      type: "system",
      text: useCaption
        ? (captionText
            ? `Caption (BLIP): "${captionText}" · Type your question`
            : "No caption generated · Type your question to search the knowledge base")
        : (ocrText
            ? `OCR found text (${ocrText.length} chars) · Type your question`
            : "No text detected · Type your question to search the knowledge base"),
    });
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
              <IconButton
                label="🖼  Browse"
                onPress={() => setBrowseModalVisible(true)}
              />
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
              placeholder={
                pendingCapture
                  ? `Ask a question about the photo... [${SCENARIO}]`
                  : `Type a message... [${SCENARIO}]`
              }
              disabled={querying}
            />
          </View>

          <CameraModal
            visible={cameraModalVisible}
            onClose={() => setCameraModalVisible(false)}
            onPhotoCaptured={handlePhotoCaptured}
            scenario={SCENARIO}
            useCaption={SCENARIOS_WITH_CAPTION.includes(SCENARIO)}
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