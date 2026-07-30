import { useRef, useState } from "react";
import { Modal, View, TouchableOpacity, Text, Alert, ActivityIndicator } from "react-native";
import { CameraView, useCameraPermissions } from "expo-camera";
import * as FileSystem from "expo-file-system/legacy";
import { cameraStyles as styles } from "../styles/camera.styles";
import { BACKEND_HTTP } from "../config";

export default function CameraModal({ visible, onClose, onPhotoCaptured, scenario = "unset", useCaption = false }) {
  const cameraRef = useRef(null);
  const [capturing, setCapturing] = useState(false);
  const [status, setStatus] = useState("");
  const [cameraReady, setCameraReady] = useState(false);
  const [permission, requestPermission] = useCameraPermissions();

  if (!permission) return null;

  if (!permission.granted) {
    return (
      <Modal visible={visible} animationType="slide" statusBarTranslucent>
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
      </Modal>
    );
  }

  const takePictureAndProcess = async () => {
    if (!cameraRef.current || capturing || !cameraReady) return;
    setCapturing(true);

    // Small delay to let the sensor fully stabilise after onCameraReady
    await new Promise((resolve) => setTimeout(resolve, 300));

    try {
      // Step 1: Take photo without base64 (more reliable on iOS)
      setStatus("Capturing...");
      const photo = await cameraRef.current.takePictureAsync({ base64: false });

      // Step 2: Read base64 separately via FileSystem
      let imageBase64 = "";
      try {
        imageBase64 = await FileSystem.readAsStringAsync(photo.uri, {
          encoding: FileSystem.EncodingType.Base64,
        });
      } catch (fsErr) {
        console.log("Could not read base64:", fsErr);
      }

      console.log("imageBase64 length:", imageBase64?.length ?? "NULL");

      // Step 3: OCR or BLIP caption via backend — only if base64 was successfully read.
      // For caption scenarios, OCR is skipped entirely so it can't contribute to the answer.
      setStatus(useCaption ? "Generating caption..." : "Reading text...");
      let ocrText = "";
      let ocrMs = null;
      let captionText = "";
      let captionMs = null;

      if (imageBase64 && imageBase64.length > 100) {
        const label = useCaption ? "Caption" : "OCR";
        const endpoint = useCaption ? "/caption" : "/ocr";
        const start = Date.now();
        try {
          const res = await fetch(`${BACKEND_HTTP}${endpoint}`, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              "X-Scenario": scenario,
            },
            body: JSON.stringify({ image_base64: imageBase64 }),
          });

          if (res.ok) {
            const json = await res.json();
            if (useCaption) {
              captionText = json.caption ?? "";
            } else {
              ocrText = json.text ?? "";
            }
            console.log(`${label} result:`, (useCaption ? captionText : ocrText) || "(none)");
          } else {
            const rawText = await res.text();
            console.log(`${label} server error:`, res.status, rawText.slice(0, 200));
          }
        } catch (err) {
          console.log(`${label} failed (non-fatal):`, err);
        } finally {
          if (useCaption) captionMs = Date.now() - start;
          else ocrMs = Date.now() - start;
        }
      } else {
        console.log(`Skipping ${useCaption ? "captioning" : "OCR"} — imageBase64 empty or too short:`, imageBase64?.length);
      }

      // Step 4: Upload photo to backend
      setStatus("Uploading...");
      const formData = new FormData();
      formData.append("file", {
        uri: photo.uri,
        name: `photo-${Date.now()}.jpg`,
        type: "image/jpeg",
      });

      const res = await fetch(`${BACKEND_HTTP}/upload-photo`, {
        method: "POST",
        headers: { "X-Scenario": scenario },
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

      // Step 5: Return photo URL, OCR/caption text, base64, and timings to App
      onPhotoCaptured({ photoUrl: fullUrl, ocrText, captionText, imageBase64, ocrMs, captionMs });
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
        <CameraView
          ref={cameraRef}
          style={styles.cameraView}
          facing="back"
          isActive={visible}
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
            onPress={() => { setCameraReady(false); onClose(); }}
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
              {cameraReady
                ? `Tap to capture · ${useCaption ? "BLIP caption" : "OCR"} runs automatically`
                : "Starting camera..."}
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
    </Modal>
  );
}