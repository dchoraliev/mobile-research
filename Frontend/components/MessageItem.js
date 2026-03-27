import { View, Text } from "react-native";
import { messageItemStyles as styles } from "../styles/messageItem.styles";

export default function MessageItem({ item }) {
  if (item.type === "system") {
    return (
      <View style={styles.systemRow}>
        <Text style={styles.systemText}>{item.text}</Text>
      </View>
    );
  }

  if (item.type === "text") {
    return (
      <View style={styles.messageRow}>
        <Text style={styles.author}>{item.author ?? "User"}</Text>
        <Text style={styles.text}>{item.text}</Text>
      </View>
    );
  }

  return null;
}
