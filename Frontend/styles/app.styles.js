import { StyleSheet } from "react-native";
import { colors, radius, spacing } from "./colors";

export const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: colors.bgPrimary,
  },
  container: {
    flex: 1,
    backgroundColor: colors.bgPrimary,
  },

  // ── Photo viewer ──
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
    gap: spacing.sm,
  },
  noPhotoText: {
    color: colors.textMuted,
    fontSize: 14,
    letterSpacing: 0.4,
  },

  // ── Chat ──
  chatContainer: {
    flex: 3,
    borderTopWidth: 1,
    borderTopColor: colors.btnBorder,
  },

  // ── Bottom bar ──
  bottomBar: {
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    borderTopWidth: 1,
    borderTopColor: colors.btnBorder,
    backgroundColor: colors.bgSecondary,
    gap: spacing.sm,
  },
  buttonRow: {
    flexDirection: "row",
    gap: spacing.sm,
  },

  // ── Input row ──
  inputRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.sm,
  },
  input: {
    flex: 1,
    backgroundColor: colors.bgInput,
    color: colors.textPrimary,
    borderRadius: radius.full,
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.sm,
    fontSize: 15,
    borderWidth: 1,
    borderColor: colors.btnBorder,
  },
  sendButton: {
    backgroundColor: colors.accent,
    borderRadius: radius.full,
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.sm,
    justifyContent: "center",
    alignItems: "center",
  },
  sendButtonText: {
    color: "#fff",
    fontWeight: "700",
    fontSize: 14,
  },
});
