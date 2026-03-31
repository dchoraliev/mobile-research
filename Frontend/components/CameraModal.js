import { useRef, useState } from "react";
import { Modal, View, TouchableOpacity, Text, Alert, ActivityIndicator } from "react-native";
import { CameraView } from "expo-camera";
import { createWorker } from "tesseract.js";
import { cameraStyles as styles } from "../styles/camera.styles";
import { BACKEND_HTTP } from "../config";

export default function CameraModal({ visible, onClose, onPhotoCaptured }) {
  const cameraRef = useRef(null);
  const [capturing, setCapturing] = useState(false);
  const [status, setStatus] = useState("");

  const takePictureAndProcess = async () => {
    if (!cameraRef.current || capturing) return;
    setCapturing(true);

    try {
      // Step 1: Take photo
      setStatus("Capturing...");
      const photo = await cameraRef.current.takePictureAsync({ base64: true });

      // Step 2: OCR using tesseract.js (pure JS, works in Expo Go)
      setStatus("Reading text...");
      let ocrText = "";
      try {
        const worker = await createWorker("eng");
        const { data } = await worker.recognize(photo.uri);
        ocrText = data.text.trim();
        await worker.terminate();
        console.log("OCR result:", ocrText);
      } catch (ocrErr) {
        console.log("OCR failed (non-fatal):", ocrErr);
      }

      // Step 3: Upload photo to backend
      setStatus("Uploading...");
      const formData = new FormData();
      formData.append("file", {
        uri: photo.uri,
        name: `photo-${Date.now()}.jpg`,
        type: "image/jpeg",
      });

      const res = await fetch(`${BACKEND_HTTP}/upload-photo`, {
        method: "POST",
        body: formData,
      });

      const textBody = await res.text();

      if (!res.ok) {
        Alert.alert("Upload failed", `Status: ${res.status}`);
        return;
      }

      let json;
      try {
        json = JSON.parse(textBody);
      } catch {
        Alert.alert("Error", "Could not parse server response.");
        return;
      }

      if (!json.url) {
        Alert.alert("Error", "Server did not return a URL.");
        return;
      }

      const fullUrl = `${BACKEND_HTTP}${json.url}`;

      // Step 4: Return photo URL, OCR text, and base64 to App
      onPhotoCaptured({
        photoUrl: fullUrl,
        ocrText,
        imageBase64: photo.base64,
      });

      onClose();
    } catch (err) {
      console.error("Error capturing photo:", err);
      Alert.alert("Error", "Could not capture or process photo.");
    } finally {
      setCapturing(false);
      setStatus("");
    }
  };

  return (
    <Modal visible={visible} animationType="slide" statusBarTranslucent>
      <View style={styles.container}>
        <CameraView ref={cameraRef} style={styles.cameraView} facing="back" />

        {/* Close button */}
        <View style={styles.topBar}>
          <TouchableOpacity style={styles.closeButton} onPress={onClose} disabled={capturing}>
            <Text style={styles.closeButtonText}>✕</Text>
          </TouchableOpacity>
        </View>

        {/* Shutter controls */}
        <View style={styles.controls}>
          {capturing ? (
            <>
              <ActivityIndicator color="#fff" size="small" />
              <Text style={styles.hint}>{status}</Text>
            </>
          ) : (
            <Text style={styles.hint}>Tap to capture · OCR runs automatically</Text>
          )}
          <TouchableOpacity
            onPress={takePictureAndProcess}
            activeOpacity={0.8}
            disabled={capturing}
          >
            <View style={styles.shutterOuter}>
              <View style={[styles.shutterInner, capturing && styles.shutterActive]} />
            </View>
          </TouchableOpacity>
        </View>
      </View>
    </Modal>
  );
}