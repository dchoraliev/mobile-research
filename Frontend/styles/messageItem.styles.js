import { StyleSheet } from "react-native";
import { colors, radius, spacing } from "./colors";

export const messageItemStyles = StyleSheet.create({
  // ── System message ──
  systemRow: {
    alignItems: "center",
    marginVertical: spacing.xs,
  },
  systemText: {
    color: colors.systemText,
    fontSize: 12,
    fontStyle: "italic",
    backgroundColor: "rgba(111,207,151,0.08)",
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.xs,
    borderRadius: radius.full,
    overflow: "hidden",
  },

  // ── Text message ──
  messageRow: {
    marginVertical: spacing.xs,
    marginHorizontal: spacing.sm,
    backgroundColor: colors.bgTertiary,
    borderRadius: radius.md,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    borderWidth: 1,
    borderColor: colors.btnBorder,
  },
  author: {
    color: colors.authorText,
    fontSize: 11,
    fontWeight: "700",
    marginBottom: 2,
    letterSpacing: 0.3,
  },
  text: {
    color: colors.textPrimary,
    fontSize: 14,
    lineHeight: 20,
  },
});
