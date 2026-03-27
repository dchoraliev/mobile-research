import { StyleSheet, Dimensions } from "react-native";
import { colors, radius, spacing } from "./colors";

const { width } = Dimensions.get("window");

export const cameraStyles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#000",
  },
  cameraView: {
    flex: 1,
  },

  // ── Top bar ──
  topBar: {
    position: "absolute",
    top: 0,
    left: 0,
    right: 0,
    paddingTop: spacing.xl * 2,
    paddingHorizontal: spacing.lg,
    flexDirection: "row",
    justifyContent: "flex-end",
    zIndex: 10,
  },
  closeButton: {
    width: 40,
    height: 40,
    borderRadius: radius.full,
    backgroundColor: "rgba(0,0,0,0.5)",
    justifyContent: "center",
    alignItems: "center",
  },
  closeButtonText: {
    color: "#fff",
    fontSize: 18,
    fontWeight: "600",
  },

  // ── Bottom controls ──
  controls: {
    position: "absolute",
    bottom: 0,
    left: 0,
    right: 0,
    paddingBottom: spacing.xl * 2,
    paddingHorizontal: spacing.xl,
    alignItems: "center",
    gap: spacing.lg,
  },
  hint: {
    color: "rgba(255,255,255,0.6)",
    fontSize: 13,
    letterSpacing: 0.3,
  },

  // ── Shutter button ──
  shutterOuter: {
    width: 80,
    height: 80,
    borderRadius: radius.full,
    borderWidth: 4,
    borderColor: "#fff",
    justifyContent: "center",
    alignItems: "center",
  },
  shutterInner: {
    width: 64,
    height: 64,
    borderRadius: radius.full,
    backgroundColor: colors.captureBtn,
  },
  shutterActive: {
    backgroundColor: "rgba(255,255,255,0.6)",
  },
});
