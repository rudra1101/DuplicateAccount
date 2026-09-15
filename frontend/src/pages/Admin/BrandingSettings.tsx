import { useEffect, useMemo, useState } from "react";
import CloudUploadOutlinedIcon from "@mui/icons-material/CloudUploadOutlined";
import RestartAltIcon from "@mui/icons-material/RestartAlt";
import SaveOutlinedIcon from "@mui/icons-material/SaveOutlined";
import {
  Alert,
  Box,
  Button,
  Card,
  CardActionArea,
  CardContent,
  CircularProgress,
  Divider,
  Stack,
  TextField,
  Typography,
} from "@mui/material";

import {
  customLogoUrl,
  getBrandingSettings,
  resetBrandingPalette,
  resetLogo,
  saveBrandingPalette,
  uploadLogo,
  type BrandingPalette,
  type BrandingSettings as BrandingSettingsType,
} from "../../services/settingsService";

const PRESETS: Array<{ name: string; palette: BrandingPalette }> = [
  {
    name: "IdentityAI Blue",
    palette: {
      primaryColor: "#1565C0",
      secondaryColor: "#1976D2",
      navigationColor: "#0F172A",
      backgroundColor: "#F5F7FA",
    },
  },
  {
    name: "Enterprise Indigo",
    palette: {
      primaryColor: "#4338CA",
      secondaryColor: "#6366F1",
      navigationColor: "#1E1B4B",
      backgroundColor: "#F8FAFC",
    },
  },
  {
    name: "Security Emerald",
    palette: {
      primaryColor: "#047857",
      secondaryColor: "#10B981",
      navigationColor: "#022C22",
      backgroundColor: "#F6FBF8",
    },
  },
  {
    name: "Professional Slate",
    palette: {
      primaryColor: "#334155",
      secondaryColor: "#64748B",
      navigationColor: "#0F172A",
      backgroundColor: "#F8FAFC",
    },
  },
];

const HEX_PATTERN = /^#[0-9A-Fa-f]{6}$/;

const BrandingSettings = () => {
  const [branding, setBranding] = useState<BrandingSettingsType | null>(null);
  const [palette, setPalette] = useState<BrandingPalette | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [paletteBusy, setPaletteBusy] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  useEffect(() => {
    void (async () => {
      try {
        const value = await getBrandingSettings();
        setBranding(value);
        setPalette({
          primaryColor: value.primaryColor,
          secondaryColor: value.secondaryColor,
          navigationColor: value.navigationColor,
          backgroundColor: value.backgroundColor,
        });
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : "Unable to load branding settings.");
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const logoSrc = useMemo(
    () => branding?.customLogo ? customLogoUrl(branding.updatedAt) : "/nusummit-logo.svg",
    [branding],
  );

  const notifyBrandingChanged = () => {
    window.dispatchEvent(new Event("identityai-branding-updated"));
  };

  const syncPalette = (value: BrandingSettingsType) => {
    setBranding(value);
    setPalette({
      primaryColor: value.primaryColor,
      secondaryColor: value.secondaryColor,
      navigationColor: value.navigationColor,
      backgroundColor: value.backgroundColor,
    });
    notifyBrandingChanged();
  };

  const handleLogoUpload = async (file: File | undefined) => {
    if (!file) return;
    setBusy(true);
    setError("");
    setSuccess("");
    try {
      const updated = await uploadLogo(file);
      setBranding(updated);
      notifyBrandingChanged();
      setSuccess("IdentityAI header logo updated successfully.");
    } catch (uploadError) {
      setError(uploadError instanceof Error ? uploadError.message : "Unable to upload logo.");
    } finally {
      setBusy(false);
    }
  };

  const handleResetLogo = async () => {
    setBusy(true);
    setError("");
    setSuccess("");
    try {
      const updated = await resetLogo();
      setBranding(updated);
      notifyBrandingChanged();
      setSuccess("IdentityAI header logo reset to the default logo.");
    } catch (resetError) {
      setError(resetError instanceof Error ? resetError.message : "Unable to reset logo.");
    } finally {
      setBusy(false);
    }
  };

  const setColor = (key: keyof BrandingPalette, value: string) => {
    setPalette((current) => current ? { ...current, [key]: value.toUpperCase() } : current);
  };

  const paletteValid = palette
    ? Object.values(palette).every((value) => HEX_PATTERN.test(value))
    : false;

  const handleSavePalette = async () => {
    if (!palette || !paletteValid) return;
    setPaletteBusy(true);
    setError("");
    setSuccess("");
    try {
      syncPalette(await saveBrandingPalette(palette));
      setSuccess("Global IdentityAI color palette updated successfully.");
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Unable to save color palette.");
    } finally {
      setPaletteBusy(false);
    }
  };

  const handleResetPalette = async () => {
    setPaletteBusy(true);
    setError("");
    setSuccess("");
    try {
      syncPalette(await resetBrandingPalette());
      setSuccess("Color palette reset to the IdentityAI default.");
    } catch (resetError) {
      setError(resetError instanceof Error ? resetError.message : "Unable to reset color palette.");
    } finally {
      setPaletteBusy(false);
    }
  };

  if (loading) {
    return <Box sx={{ display: "flex", justifyContent: "center", py: 8 }}><CircularProgress /></Box>;
  }

  return (
    <Stack spacing={3}>
      {error && <Alert severity="error" onClose={() => setError("")}>{error}</Alert>}
      {success && <Alert severity="success" onClose={() => setSuccess("")}>{success}</Alert>}

      <Card variant="outlined">
        <CardContent>
          <Stack spacing={2.5}>
            <Box>
              <Typography variant="h6" fontWeight={800}>Global Logo</Typography>
              <Typography variant="body2" color="text.secondary">
                Manage the logo used across the IdentityAI platform. PNG, JPEG, and WebP are supported up to 2 MB.
              </Typography>
            </Box>
            <Divider />
            <Box
              sx={{
                minHeight: 110,
                border: "1px dashed",
                borderColor: "divider",
                borderRadius: 2,
                bgcolor: "var(--identityai-navigation, #0F172A)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                px: 3,
                py: 2,
              }}
            >
              <Box component="img" src={logoSrc} alt="IdentityAI logo preview" sx={{ maxHeight: 64, maxWidth: "100%", objectFit: "contain" }} />
            </Box>
            <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5} alignItems={{ sm: "center" }}>
              <Button component="label" variant="contained" startIcon={<CloudUploadOutlinedIcon />} disabled={busy}>
                {busy ? "Updating…" : "Upload logo"}
                <input hidden type="file" accept="image/png,image/jpeg,image/webp" onChange={(event) => { void handleLogoUpload(event.target.files?.[0]); event.target.value = ""; }} />
              </Button>
              <Button variant="outlined" startIcon={<RestartAltIcon />} onClick={handleResetLogo} disabled={busy || !branding?.customLogo}>
                Reset logo
              </Button>
              {branding?.customLogo && (
                <Typography variant="body2" color="text.secondary">Current file: {branding.filename || "custom logo"}</Typography>
              )}
            </Stack>
          </Stack>
        </CardContent>
      </Card>

      <Card variant="outlined">
        <CardContent>
          <Stack spacing={3}>
            <Box>
              <Typography variant="h6" fontWeight={800}>Global Color Palette</Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                Choose a preset or define your own colors. The palette is applied across IdentityAI, including navigation, buttons, links, highlights, and page backgrounds.
              </Typography>
            </Box>
            <Divider />

            <Box>
              <Typography variant="subtitle2" fontWeight={800} sx={{ mb: 1.5 }}>Palette presets</Typography>
              <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", sm: "repeat(2, 1fr)", lg: "repeat(4, 1fr)" }, gap: 1.5 }}>
                {PRESETS.map((preset) => (
                  <Card key={preset.name} variant="outlined">
                    <CardActionArea onClick={() => setPalette(preset.palette)} sx={{ p: 1.5 }}>
                      <Stack spacing={1.25}>
                        <Typography variant="body2" fontWeight={700}>{preset.name}</Typography>
                        <Stack direction="row" spacing={0.75}>
                          {Object.values(preset.palette).map((color) => (
                            <Box key={color} sx={{ width: 28, height: 28, borderRadius: 1, bgcolor: color, border: "1px solid", borderColor: "divider" }} />
                          ))}
                        </Stack>
                      </Stack>
                    </CardActionArea>
                  </Card>
                ))}
              </Box>
            </Box>

            {palette && (
              <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", md: "repeat(2, 1fr)" }, gap: 2 }}>
                {([
                  ["primaryColor", "Primary color", "Buttons, active states, links and primary actions"],
                  ["secondaryColor", "Secondary / accent color", "Secondary actions and accents"],
                  ["navigationColor", "Navigation color", "Global header and Account Intelligence sidebar"],
                  ["backgroundColor", "Page background", "Default background across the application"],
                ] as Array<[keyof BrandingPalette, string, string]>).map(([key, label, helper]) => (
                  <Stack key={key} direction="row" spacing={1.5} alignItems="flex-start">
                    <Box
                      component="input"
                      type="color"
                      value={palette[key]}
                      onChange={(event) => setColor(key, event.target.value)}
                      aria-label={`${label} color picker`}
                      sx={{ width: 52, height: 52, p: 0.25, border: "1px solid", borderColor: "divider", borderRadius: 1.5, bgcolor: "background.paper", cursor: "pointer" }}
                    />
                    <TextField
                      fullWidth
                      label={label}
                      value={palette[key]}
                      onChange={(event) => setColor(key, event.target.value)}
                      error={palette[key].length > 0 && !HEX_PATTERN.test(palette[key])}
                      helperText={HEX_PATTERN.test(palette[key]) ? helper : "Use a six-digit hex color, for example #1565C0"}
                      inputProps={{ maxLength: 7 }}
                    />
                  </Stack>
                ))}
              </Box>
            )}

            {palette && (
              <Box sx={{ borderRadius: 2.5, overflow: "hidden", border: "1px solid", borderColor: "divider" }}>
                <Box sx={{ bgcolor: palette.navigationColor, color: "white", px: 2.5, py: 1.5 }}>
                  <Typography fontWeight={800}>Live palette preview</Typography>
                </Box>
                <Box sx={{ bgcolor: palette.backgroundColor, p: 2.5 }}>
                  <Stack direction="row" spacing={1.5} alignItems="center" flexWrap="wrap" useFlexGap>
                    <Button variant="contained" sx={{ bgcolor: palette.primaryColor, "&:hover": { bgcolor: palette.primaryColor } }}>Primary action</Button>
                    <Button variant="contained" sx={{ bgcolor: palette.secondaryColor, "&:hover": { bgcolor: palette.secondaryColor } }}>Secondary action</Button>
                    <Typography color="text.primary">Page background preview</Typography>
                  </Stack>
                </Box>
              </Box>
            )}

            <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5}>
              <Button variant="contained" startIcon={<SaveOutlinedIcon />} onClick={handleSavePalette} disabled={paletteBusy || !paletteValid}>
                {paletteBusy ? "Saving…" : "Save palette"}
              </Button>
              <Button variant="outlined" startIcon={<RestartAltIcon />} onClick={handleResetPalette} disabled={paletteBusy}>
                Reset colors to default
              </Button>
            </Stack>
          </Stack>
        </CardContent>
      </Card>
    </Stack>
  );
};

export default BrandingSettings;
