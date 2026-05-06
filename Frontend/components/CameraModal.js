import { useRef, useState } from "react";
import { View, TouchableOpacity, Text, Alert, ActivityIndicator } from "react-native";
import { CameraView, useCameraPermissions } from "expo-camera";
import * as FileSystem from "expo-file-system/legacy";
import { cameraStyles as styles } from "../styles/camera.styles";
import { BACKEND_HTTP } from "../config";

export default function CameraModal({ visible, onClose, onPhotoCaptured }) {
  const cameraRef = useRef(null);
  const [capturing, setCapturing] = useState(false);
  const [status, setStatus] = useState("");
  const [cameraReady, setCameraReady] = useState(false);
  const [permission, requestPermission] = useCameraPermissions();

  // Not visible — unmount entirely so AVCaptureSession releases cleanly
  if (!visible) return null;

  if (!permission) return null;

  if (!permission.granted) {
    return (
      <View style={styles.overlay}>
        <View style={{ flex: 1, backgroundColor: "#000", justifyContent: "center", alignItems: "center", gap: 16 }}>
          <Text style={{ color: "#fff", fontSize: 16, textAlign: "center", paddingHorizontal: 32 }}>
            Camera permission is required to take photos.
          </Text>
          <TouchableOpacity
            onPress={requestPermission}
            style={{ backgroundColor: "#fff", paddingHorizontal: 24, paddingVertical: 12, borderRadius: 8 }}
          >
            <Text style={{ color: "#000", fontWeight: "600" }}>Grant Permission</Text>
          </TouchableOpacity>
          <TouchableOpacity onPress={onClose}>
            <Text style={{ color: "rgba(255,255,255,0.6)", marginTop: 8 }}>Cancel</Text>
          </TouchableOpacity>
        </View>
      </View>
    );
  }

  const takePictureAndProcess = async () => {
    if (!cameraRef.current || capturing || !cameraReady) return;
    setCapturing(true);

    await new Promise((resolve) => setTimeout(resolve, 300));

    try {
      setStatus("Capturing...");
      const photo = await cameraRef.current.takePictureAsync({ base64: false });

      let imageBase64 = "";
      try {
        imageBase64 = await FileSystem.readAsStringAsync(photo.uri, {
          encoding: "base64",
        });
      } catch (fsErr) {
        console.log("Could not read base64:", fsErr);
      }

      setStatus("Reading text...");
      let ocrText = "";
      try {
        const ocrRes = await fetch(`${BACKEND_HTTP}/ocr`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ image_base64: imageBase64 }),
        });
        const ocrJson = await ocrRes.json();
        ocrText = ocrJson.text ?? "";
        console.log("OCR result:", ocrText);
      } catch (ocrErr) {
        console.log("OCR failed (non-fatal):", ocrErr);
      }

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

      onPhotoCaptured({ photoUrl: fullUrl, ocrText, imageBase64 });
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
    <View style={styles.overlay}>
      <View style={styles.container}>
        <CameraView
          ref={cameraRef}
          style={styles.cameraView}
          facing="back"
          mode="picture"
          onCameraReady={() => {
            console.log("Camera ready");
            setCameraReady(true);
          }}
          onMountError={(e) => console.error("Camera mount error:", e)}
        />

        {/* Close button */}
        <View style={styles.topBar}>
          <TouchableOpacity
            style={styles.closeButton}
            onPress={() => {
              setCameraReady(false);
              onClose();
            }}
            disabled={capturing}
          >
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
            <Text style={styles.hint}>
              {cameraReady ? "Tap to capture · OCR runs automatically" : "Starting camera..."}
            </Text>
          )}
          <TouchableOpacity
            onPress={takePictureAndProcess}
            activeOpacity={0.8}
            disabled={capturing || !cameraReady}
          >
            <View style={styles.shutterOuter}>
              <View style={[styles.shutterInner, capturing && styles.shutterActive]} />
            </View>
          </TouchableOpacity>
        </View>
      </View>
    </View>
  );
}
