import React, { useEffect, useRef, useState } from "react";
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  FlatList,
  Image,
  Modal,
  Alert,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { CameraView, useCameraPermissions } from "expo-camera";
import { BACKEND_HTTP, BACKEND_WS } from "./config";
import { styles } from "./styles/app.styles";

export default function App() {
  // --- WebSocket & Chat state ---
  const socketRef = useRef(null);
  const [messages, setMessages] = useState([]);
  const [inputText, setInputText] = useState("");
  const [author] = useState("Device");

  // --- Shared photo state ---
  const [currentPhotoUrl, setCurrentPhotoUrl] = useState(null);

  // --- Photo list (for browsing from backend) ---
  const [photos, setPhotos] = useState([]);
  const [browseModalVisible, setBrowseModalVisible] = useState(false);

  // --- Camera state ---
  const [cameraPermission, requestCameraPermission] = useCameraPermissions();
  const [cameraModalVisible, setCameraModalVisible] = useState(false);
  const cameraRef = useRef(null);

  // =============================
  //      LOAD HISTORY ON MOUNT
  // =============================
  useEffect(() => {
    const loadHistory = async () => {
      try {
        const res = await fetch(`${BACKEND_HTTP}/history`);
        if (res.ok) {
          const json = await res.json();
          if (json.messages?.length) {
            setMessages(json.messages);
          }
        }
      } catch (err) {
        console.log("Could not load history:", err);
      }
    };
    loadHistory();
  }, []);

  // =============================
  //      WEBSOCKET HANDLING
  // =============================
  useEffect(() => {
    console.log("Connecting to WS:", BACKEND_WS);
    const socket = new WebSocket(BACKEND_WS);
    socketRef.current = socket;

    socket.onopen = () => {
      console.log("WebSocket connected");
    };

    socket.onmessage = (event) => {
      console.log("WebSocket message:", event.data);
      try {
        const msg = JSON.parse(event.data);

        if (msg.type === "photo_select") {
          if (msg.url) {
            setCurrentPhotoUrl(msg.url);
          }
          setMessages((prev) => [
            ...prev,
            {
              type: "system",
              text: `${msg.author ?? "Someone"} selected a new photo`,
              timestamp: msg.timestamp,
            },
          ]);
        } else if (msg.type === "text") {
          setMessages((prev) => [...prev, msg]);
        } else {
          setMessages((prev) => [...prev, msg]);
        }
      } catch (err) {
        console.log("Error parsing incoming message:", err);
      }
    };

    socket.onerror = (err) => {
      console.log("WebSocket error:", err.message || err);
    };

    socket.onclose = (event) => {
      console.log("WebSocket closed:", event.code, event.reason);
    };

    return () => {
      socket.close();
    };
  }, []);

  const sendTextMessage = () => {
    const trimmed = inputText.trim();
    if (!trimmed || socketRef.current?.readyState !== 1) {
      return;
    }

    const msg = {
      type: "text",
      author,
      text: trimmed,
      timestamp: new Date().toISOString(),
    };

    socketRef.current.send(JSON.stringify(msg));
    setInputText("");
  };

  const broadcastPhotoSelection = (fullUrl) => {
    if (socketRef.current?.readyState !== 1) return;

    const msg = {
      type: "photo_select",
      author,
      url: fullUrl,
      timestamp: new Date().toISOString(),
    };

    socketRef.current.send(JSON.stringify(msg));
  };

  // =============================
  //         CAMERA LOGIC
  // =============================
  const openCamera = async () => {
    if (!cameraPermission) {
      await requestCameraPermission();
      return;
    }

    if (!cameraPermission.granted) {
      const status = await requestCameraPermission();
      if (!status.granted) {
        Alert.alert(
          "Permission required",
          "Camera permission is needed to take photos."
        );
        return;
      }
    }

    setCameraModalVisible(true);
  };

  const takePictureAndUpload = async () => {
    if (!cameraRef.current) return;

    try {
      const photo = await cameraRef.current.takePictureAsync();
      console.log("Photo taken:", photo.uri);

      const formData = new FormData();
      formData.append("file", {
        uri: photo.uri,
        name: `photo-${Date.now()}.jpg`,
        type: "image/jpeg",
      });

      console.log("Uploading to:", `${BACKEND_HTTP}/upload-photo`);

      const res = await fetch(`${BACKEND_HTTP}/upload-photo`, {
        method: "POST",
        body: formData,
      });

      console.log("Upload response status:", res.status);
      const textBody = await res.text();
      console.log("Raw response body:", textBody);

      if (!res.ok) {
        Alert.alert("Upload failed", `Status: ${res.status}`);
        return;
      }

      let json;
      try {
        json = JSON.parse(textBody);
      } catch (e) {
        console.log("Error parsing JSON:", e);
        Alert.alert("Error", "Could not parse server response.");
        return;
      }

      if (!json.url) {
        Alert.alert("Error", "Server did not return a URL.");
        return;
      }

      const fullUrl = `${BACKEND_HTTP}${json.url}`;
      console.log("Full photo URL:", fullUrl);

      broadcastPhotoSelection(fullUrl);
      setCurrentPhotoUrl(fullUrl);
      setCameraModalVisible(false);
    } catch (err) {
      console.error("Error taking/uploading photo:", err);
      Alert.alert("Error", "Could not take or upload photo.");
    }
  };

  // =============================
  //        BROWSE PHOTOS
  // =============================
  const openBrowsePhotos = async () => {
    try {
      const res = await fetch(`${BACKEND_HTTP}/photos`);
      if (!res.ok) {
        Alert.alert("Error", "Could not fetch photos");
        return;
      }

      const json = await res.json();
      setPhotos(json.photos ?? []);
      setBrowseModalVisible(true);
    } catch (err) {
      console.error("Error fetching photos:", err);
      Alert.alert("Error", "Could not fetch photos");
    }
  };

  const handleSelectPhotoFromList = (photo) => {
    const fullUrl = `${BACKEND_HTTP}${photo.url}`;
    setCurrentPhotoUrl(fullUrl);
    broadcastPhotoSelection(fullUrl);
    setBrowseModalVisible(false);
  };

  // =============================
  //           RENDER
  // =============================
  const renderMessageItem = ({ item }) => {
    if (item.type === "system") {
      return <Text style={styles.systemMessage}>{item.text}</Text>;
    }

    if (item.type === "text") {
      return (
        <View style={styles.messageRow}>
          <Text style={styles.messageAuthor}>{item.author ?? "User"}:</Text>
          <Text style={styles.messageText}>{item.text}</Text>
        </View>
      );
    }

    return <Text style={styles.messageText}>{JSON.stringify(item)}</Text>;
  };

  const renderPhotoItem = ({ item }) => {
    const fullUrl = `${BACKEND_HTTP}${item.url}`;
    return (
      <TouchableOpacity
        style={styles.photoItem}
        onPress={() => handleSelectPhotoFromList(item)}
      >
        <Image
          source={{ uri: fullUrl }}
          style={styles.photoThumbnail}
          resizeMode="cover"
        />
        <Text style={styles.photoName}>{item.filename}</Text>
      </TouchableOpacity>
    );
  };

  return (
    <SafeAreaView style={styles.safeArea}>
      <View style={styles.container}>
        {/* TOP: Shared photo */}
        <View style={styles.photoContainer}>
          {currentPhotoUrl ? (
            <Image
              source={{ uri: currentPhotoUrl }}
              style={styles.sharedPhoto}
              resizeMode="contain"
            />
          ) : (
            <View style={styles.noPhoto}>
              <Text style={styles.noPhotoText}>No photo selected</Text>
            </View>
          )}
        </View>

        {/* MIDDLE: Chat messages */}
        <View style={styles.chatContainer}>
          <FlatList
            data={messages}
            keyExtractor={(_, index) => index.toString()}
            renderItem={renderMessageItem}
          />
        </View>

        {/* BOTTOM: Input + buttons */}
        <View style={styles.bottomBar}>
          <View style={styles.buttonRow}>
            <TouchableOpacity style={styles.button} onPress={openCamera}>
              <Text style={styles.buttonText}>Take Photo</Text>
            </TouchableOpacity>

            <TouchableOpacity style={styles.button} onPress={openBrowsePhotos}>
              <Text style={styles.buttonText}>Browse Photos</Text>
            </TouchableOpacity>
          </View>

          <View style={styles.inputRow}>
            <TextInput
              style={styles.input}
              value={inputText}
              onChangeText={setInputText}
              placeholder="Type a message..."
            />
            <TouchableOpacity
              style={styles.sendButton}
              onPress={sendTextMessage}
            >
              <Text style={styles.sendButtonText}>Send</Text>
            </TouchableOpacity>
          </View>
        </View>

        {/* CAMERA MODAL */}
        <Modal visible={cameraModalVisible} animationType="slide">
          <View style={styles.cameraModal}>
            <CameraView
              ref={cameraRef}
              style={styles.cameraView}
              facing="back"
            />
            <View style={styles.cameraControls}>
              <TouchableOpacity
                style={styles.cameraButton}
                onPress={takePictureAndUpload}
              >
                <Text style={styles.cameraButtonText}>Capture & Upload</Text>
              </TouchableOpacity>

              <TouchableOpacity
                style={[styles.cameraButton, styles.cameraCancel]}
                onPress={() => setCameraModalVisible(false)}
              >
                <Text style={styles.cameraButtonText}>Cancel</Text>
              </TouchableOpacity>
            </View>
          </View>
        </Modal>

        {/* BROWSE PHOTOS MODAL */}
        <Modal visible={browseModalVisible} animationType="slide">
          <SafeAreaView style={styles.browseModal}>
            <Text style={styles.modalTitle}>Select a photo</Text>
            <FlatList
              data={photos}
              keyExtractor={(item) => item.filename}
              renderItem={renderPhotoItem}
              numColumns={2}
              contentContainerStyle={styles.photosGrid}
            />
            <TouchableOpacity
              style={styles.closeModalButton}
              onPress={() => setBrowseModalVisible(false)}
            >
              <Text style={styles.closeModalText}>Close</Text>
            </TouchableOpacity>
          </SafeAreaView>
        </Modal>
      </View>
    </SafeAreaView>
  );
}


