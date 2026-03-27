import { FlatList } from "react-native";
import { messageListStyles as styles } from "../styles/messageList.styles";
import MessageItem from "./MessageItem";

export default function MessageList({ messages }) {
  return (
    <FlatList
      data={messages}
      keyExtractor={(_, index) => index.toString()}
      renderItem={({ item }) => <MessageItem item={item} />}
      contentContainerStyle={styles.list}
    />
  );
}
