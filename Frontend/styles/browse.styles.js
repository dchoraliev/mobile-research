import { StyleSheet } from "react-native";
import { colors, radius, spacing } from "./colors";

export const browseStyles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.bgPrimary,
  },

  // ── Header ──
  header: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md,
    borderBottomWidth: 1,
    borderBottomColor: colors.btnBorder,
  },
  title: {
    fontSize: 17,
    fontWeight: "700",
    color: colors.textPrimary,
    letterSpacing: 0.3,
  },
  closeButton: {
    width: 32,
    height: 32,
    borderRadius: radius.full,
    backgroundColor: colors.bgTertiary,
    justifyContent: "center",
    alignItems: "center",
  },
  closeButtonText: {
    color: colors.textSecondary,
    fontSize: 16,
    fontWeight: "600",
  },

  // ── Grid ──
  grid: {
    padding: spacing.sm,
  },
  photoItem: {
    flex: 1,
    margin: spacing.xs,
    borderRadius: radius.md,
    overflow: "hidden",
    backgroundColor: colors.bgTertiary,
  },
  thumbnail: {
    width: "100%",
    aspectRatio: 1,
  },
  photoName: {
    color: colors.textSecondary,
    fontSize: 11,
    padding: spacing.xs,
    textAlign: "center",
  },

  // ── Empty state ──
  empty: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    gap: spacing.sm,
  },
  emptyText: {
    color: colors.textMuted,
    fontSize: 14,
  },
});
