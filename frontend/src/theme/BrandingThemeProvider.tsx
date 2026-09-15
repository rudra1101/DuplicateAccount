import { CssBaseline, ThemeProvider } from "@mui/material";
import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";

import { getBrandingSettings, type BrandingPalette } from "../services/settingsService";
import { createIdentityAiTheme, DEFAULT_BRANDING_PALETTE } from "./theme";

interface Props {
  children: ReactNode;
}

export default function BrandingThemeProvider({ children }: Props) {
  const [palette, setPalette] = useState<BrandingPalette>(DEFAULT_BRANDING_PALETTE);

  const refresh = useCallback(async () => {
    try {
      const branding = await getBrandingSettings();
      setPalette({
        primaryColor: branding.primaryColor,
        secondaryColor: branding.secondaryColor,
        navigationColor: branding.navigationColor,
        backgroundColor: branding.backgroundColor,
      });
    } catch {
      setPalette(DEFAULT_BRANDING_PALETTE);
    }
  }, []);

  useEffect(() => {
    void refresh();
    const handleBrandingUpdated = () => void refresh();
    window.addEventListener("identityai-branding-updated", handleBrandingUpdated);
    return () => window.removeEventListener("identityai-branding-updated", handleBrandingUpdated);
  }, [refresh]);

  const theme = useMemo(() => createIdentityAiTheme(palette), [palette]);

  useEffect(() => {
    document.documentElement.style.setProperty("--identityai-navigation", palette.navigationColor);
    document.documentElement.style.setProperty(
      "--identityai-navigation-contrast",
      theme.palette.getContrastText(palette.navigationColor),
    );
  }, [palette.navigationColor, theme]);

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      {children}
    </ThemeProvider>
  );
}
