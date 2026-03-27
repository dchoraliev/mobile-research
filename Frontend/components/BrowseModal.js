import { useState } from "react";
import { Modal, View, FlatList, Image, TouchableOpacity, Text, Alert } from "react-native";
import { SafeAreaView, SafeAreaProvider } from "react-native-safe-area-context";
import { browseStyles as styles } from "../styles/browse.styles";
import { BACKEND_HTTP } from "../config";

export default function BrowseModal({ visible, onClose, onSelectPhoto }) {
  const [photos, setPhotos] = useState([]);

  const loadPhotos = async () => {
    try {
      const res = await fetch(`${BACKEND_HTTP}/photos`);
      if (!res.ok) {
        Alert.alert("Error", "Could not fetch photos");
        return;
      }
      const json = await res.json();
      setPhotos(json.photos ?? []);
    } catch (err) {
      console.error("Error fetching photos:", err);
      Alert.alert("Error", "Could not fetch photos");
    }
  };

  const handleSelect = (photo) => {
    const fullUrl = `${BACKEND_HTTP}${photo.url}`;
    onSelectPhoto(fullUrl);
    onClose();
  };

  return (
    <Modal visible={visible} animationType="slide" onShow={loadPhotos}>
      <SafeAreaProvider>
      <SafeAreaView style={styles.container}>
        {/* Header */}
        <View style={styles.header}>
          <Text style={styles.title}>Select a photo</Text>
          <TouchableOpacity style={styles.closeButton} onPress={onClose}>
            <Text style={styles.closeButtonText}>✕</Text>
          </TouchableOpacity>
        </View>

        {/* Grid */}
        {photos.length === 0 ? (
          <View style={styles.empty}>
            <Text style={styles.emptyText}>No photos uploaded yet</Text>
          </View>
        ) : (
          <FlatList
            data={photos}
            keyExtractor={(item) => item.filename}
            numColumns={2}
            contentContainerStyle={styles.grid}
            renderItem={({ item }) => {
              const fullUrl = `${BACKEND_HTTP}${item.url}`;
              return (
                <TouchableOpacity style={styles.photoItem} onPress={() => handleSelect(item)}>
                  <Image source={{ uri: fullUrl }} style={styles.thumbnail} resizeMode="cover" />
                  <Text style={styles.photoName} numberOfLines={1}>{item.filename}</Text>
                </TouchableOpacity>
              );
            }}
          />
        )}
      </SafeAreaView>
      </SafeAreaProvider>
    </Modal>
  );
}
