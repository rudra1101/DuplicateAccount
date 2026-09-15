import { useEffect, useMemo, useState } from "react";
import CloudUploadOutlinedIcon from "@mui/icons-material/CloudUploadOutlined";
import RestartAltIcon from "@mui/icons-material/RestartAlt";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  CircularProgress,
  Divider,
  Stack,
  Typography,
} from "@mui/material";

import {
  customLogoUrl,
  getBrandingSettings,
  resetLogo,
  uploadLogo,
  type BrandingSettings as BrandingSettingsType,
} from "../../services/settingsService";

const BrandingSettings = () => {
  const [branding, setBranding] = useState<BrandingSettingsType | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  useEffect(() => {
    void (async () => {
      try {
        setBranding(await getBrandingSettings());
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

  if (loading) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", py: 8 }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Stack spacing={3}>
      {error && <Alert severity="error" onClose={() => setError("")}>{error}</Alert>}
      {success && <Alert severity="success" onClose={() => setSuccess("")}>{success}</Alert>}

      <Card variant="outlined">
        <CardContent>
          <Stack spacing={2.5}>
            <Box>
              <Typography variant="h6" fontWeight={800}>Global Branding</Typography>
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
                bgcolor: "#0f172a",
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
                <input
                  hidden
                  type="file"
                  accept="image/png,image/jpeg,image/webp"
                  onChange={(event) => {
                    void handleLogoUpload(event.target.files?.[0]);
                    event.target.value = "";
                  }}
                />
              </Button>
              <Button
                variant="outlined"
                startIcon={<RestartAltIcon />}
                onClick={handleResetLogo}
                disabled={busy || !branding?.customLogo}
              >
                Reset to default
              </Button>
              {branding?.customLogo && (
                <Typography variant="body2" color="text.secondary">
                  Current file: {branding.filename || "custom logo"}
                </Typography>
              )}
            </Stack>
          </Stack>
        </CardContent>
      </Card>
    </Stack>
  );
};

export default BrandingSettings;
