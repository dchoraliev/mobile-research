import { View, Image, Text } from "react-native";
import { photoViewerStyles as styles } from "../styles/photoViewer.styles";

export default function PhotoViewer({ photoUrl }) {
  return (
    <View style={styles.container}>
      {photoUrl ? (
        <Image source={{ uri: photoUrl }} style={styles.image} resizeMode="contain" />
      ) : (
        <View style={styles.empty}>
          <Text style={styles.emptyIcon}>🖼</Text>
          <Text style={styles.emptyText}>No photo selected</Text>
        </View>
      )}
    </View>
  );
}
