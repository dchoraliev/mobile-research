import { StyleSheet } from "react-native";

export const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: 16,
    backgroundColor: "#f0f4ff",
  },
  title: {
    fontSize: 20,
    fontWeight: "800",
    marginBottom: 4,
    textAlign: "center",
  },
  status: {
    fontSize: 14,
    textAlign: "center",
    marginBottom: 12,
  },
  messagesContainer: {
    flex: 1,
    borderWidth: 1,
    borderColor: "#ddd",
    borderRadius: 8,
    padding: 8,
    backgroundColor: "#ffffff",
  },
  messageBubble: {
    marginVertical: 4,
    padding: 6,
    borderRadius: 6,
  },
  myMessage: {
    alignSelf: "flex-end",
    backgroundColor: "#d4f8d4",
  },
  serverMessage: {
    alignSelf: "flex-start",
    backgroundColor: "#d4e4ff",
  },
  systemMessage: {
    alignSelf: "center",
    backgroundColor: "#fce5cd",
  },
  messageFrom: {
    fontSize: 10,
    opacity: 0.6,
  },
  messageText: {
    fontSize: 14,
  },
  inputRow: {
    flexDirection: "row",
    marginTop: 8,
    alignItems: "center",
    gap: 8,
  },
  input: {
    flex: 1,
    borderWidth: 1,
    borderColor: "#aaa",
    borderRadius: 6,
    paddingHorizontal: 8,
    paddingVertical: 6,
    backgroundColor: "#ffffff",
  },
  buttonRow: {
    marginTop: 8,
  },
});
