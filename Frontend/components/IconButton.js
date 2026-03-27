import { TouchableOpacity, Text } from "react-native";
import { iconButtonStyles as styles } from "../styles/iconButton.styles";

/**
 * A pill-shaped button used in the bottom action bar.
 * Props: label, onPress, variant ("primary" | "secondary")
 */
export default function IconButton({ label, onPress, variant = "secondary" }) {
  const isPrimary = variant === "primary";
  return (
    <TouchableOpacity
      style={[styles.button, isPrimary ? styles.primary : styles.secondary]}
      onPress={onPress}
      activeOpacity={0.75}
    >
      <Text style={[styles.label, isPrimary ? styles.labelPrimary : styles.labelSecondary]}>
        {label}
      </Text>
    </TouchableOpacity>
  );
}
