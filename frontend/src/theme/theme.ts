import { createTheme } from "@mui/material/styles";
import type { BrandingPalette } from "../services/settingsService";

export const DEFAULT_BRANDING_PALETTE: BrandingPalette = {
  primaryColor: "#1565C0",
  secondaryColor: "#1976D2",
  navigationColor: "#0F172A",
  backgroundColor: "#F5F7FA",
};

export function createIdentityAiTheme(palette: BrandingPalette = DEFAULT_BRANDING_PALETTE) {
  return createTheme({
    palette: {
      primary: { main: palette.primaryColor },
      secondary: { main: palette.secondaryColor },
      background: { default: palette.backgroundColor },
    },
    shape: { borderRadius: 10 },
    typography: { fontFamily: "Roboto, sans-serif" },
  });
}

export default createIdentityAiTheme();
