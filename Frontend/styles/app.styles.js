import { StyleSheet } from "react-native";

export const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: "#101010",
  },
  container: {
    flex: 1,
    backgroundColor: "#101010",
  },
  photoContainer: {
    flex: 3,
    backgroundColor: "#000",
    justifyContent: "center",
    alignItems: "center",
  },
  sharedPhoto: {
    width: "100%",
    height: "100%",
  },
  noPhoto: {
    justifyContent: "center",
    alignItems: "center",
  },
  noPhotoText: {
    color: "#888",
    fontSize: 16,
  },
  chatContainer: {
    flex: 3,
    padding: 8,
  },
  messageRow: {
    flexDirection: "row",
    marginBottom: 4,
  },
  messageAuthor: {
    fontWeight: "bold",
    color: "#fff",
    marginRight: 4,
  },
  messageText: {
    color: "#eee",
  },
  systemMessage: {
    fontStyle: "italic",
    color: "#9acd32",
    marginBottom: 4,
  },
  bottomBar: {
    paddingHorizontal: 8,
    paddingBottom: 8,
  },
  buttonRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    marginBottom: 8,
  },
  button: {
    flex: 1,
    backgroundColor: "#444",
    padding: 10,
    marginHorizontal: 4,
    borderRadius: 8,
    alignItems: "center",
  },
  buttonText: {
    color: "#fff",
    fontWeight: "600",
  },
  inputRow: {
    flexDirection: "row",
    alignItems: "center",
  },
  input: {
    flex: 1,
    backgroundColor: "#222",
    color: "#fff",
    borderRadius: 8,
    paddingHorizontal: 10,
    paddingVertical: 6,
    marginRight: 8,
  },
  sendButton: {
    backgroundColor: "#1e90ff",
    borderRadius: 8,
    paddingHorizontal: 16,
    paddingVertical: 8,
  },
  sendButtonText: {
    color: "#fff",
    fontWeight: "600",
  },
  cameraModal: {
    flex: 1,
    backgroundColor: "#000",
  },
  cameraView: {
    flex: 1,
  },
  cameraControls: {
    padding: 16,
    flexDirection: "row",
    justifyContent: "space-around",
    backgroundColor: "#000",
  },
  cameraButton: {
    backgroundColor: "#1e90ff",
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderRadius: 8,
  },
  cameraCancel: {
    backgroundColor: "#555",
  },
  cameraButtonText: {
    color: "#fff",
    fontWeight: "600",
  },
  browseModal: {
    flex: 1,
    backgroundColor: "#101010",
  },
  modalTitle: {
    fontSize: 18,
    fontWeight: "600",
    color: "#fff",
    textAlign: "center",
    marginVertical: 10,
  },
  photosGrid: {
    paddingHorizontal: 8,
  },
  photoItem: {
    flex: 1,
    margin: 6,
    alignItems: "center",
  },
  photoThumbnail: {
    width: 140,
    height: 140,
    borderRadius: 8,
    marginBottom: 4,
  },
  photoName: {
    color: "#ddd",
    fontSize: 12,
    textAlign: "center",
  },
  closeModalButton: {
    backgroundColor: "#444",
    padding: 12,
    margin: 12,
    borderRadius: 8,
    alignItems: "center",
  },
  closeModalText: {
    color: "#fff",
    fontWeight: "600",
  },
});
