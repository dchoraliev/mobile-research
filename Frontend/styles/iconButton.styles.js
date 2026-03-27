import { StyleSheet } from "react-native";
import { colors, radius, spacing } from "./colors";

export const iconButtonStyles = StyleSheet.create({
  button: {
    flex: 1,
    paddingVertical: spacing.sm + 2,
    paddingHorizontal: spacing.md,
    borderRadius: radius.full,
    alignItems: "center",
    justifyContent: "center",
    borderWidth: 1,
  },
  primary: {
    backgroundColor: colors.accent,
    borderColor: colors.accent,
  },
  secondary: {
    backgroundColor: colors.btnSecondary,
    borderColor: colors.btnBorder,
  },
  label: {
    fontSize: 14,
    fontWeight: "600",
    letterSpacing: 0.3,
  },
  labelPrimary: {
    color: "#fff",
  },
  labelSecondary: {
    color: colors.textPrimary,
  },
});
