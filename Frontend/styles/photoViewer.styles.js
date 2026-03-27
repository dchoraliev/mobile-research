import { StyleSheet } from "react-native";
import { colors, spacing } from "./colors";

export const photoViewerStyles = StyleSheet.create({
  container: {
    flex: 3,
    backgroundColor: "#000",
    justifyContent: "center",
    alignItems: "center",
  },
  image: {
    width: "100%",
    height: "100%",
  },
  empty: {
    justifyContent: "center",
    alignItems: "center",
    gap: spacing.sm,
  },
  emptyIcon: {
    fontSize: 36,
    opacity: 0.3,
  },
  emptyText: {
    color: colors.textMuted,
    fontSize: 14,
    letterSpacing: 0.4,
  },
});
