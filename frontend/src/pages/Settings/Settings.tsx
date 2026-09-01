import { useEffect, useMemo, useState } from "react";
import CloudUploadOutlinedIcon from "@mui/icons-material/CloudUploadOutlined";
import RestartAltIcon from "@mui/icons-material/RestartAlt";
import SendOutlinedIcon from "@mui/icons-material/SendOutlined";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Divider,
  FormControlLabel,
  Grid,
  Stack,
  Switch,
  Tab,
  Tabs,
  TextField,
  Typography,
} from "@mui/material";

import {
  customLogoUrl,
  getBrandingSettings,
  getSmtpSettings,
  resetLogo,
  saveSmtpSettings,
  sendSmtpTest,
  uploadLogo,
  type BrandingSettings,
  type SmtpSettings,
} from "../../services/settingsService";
import EmailTemplatesCard from "./EmailTemplatesCard";
import RemediationSlaSettingsCard from "./RemediationSlaSettingsCard";
import ServiceDeskSettingsCard from "./ServiceDeskSettingsCard";

type SettingsTab = "smtp" | "branding" | "emailTemplates" | "serviceDesk" | "remediationSla";

const Settings = () => {
  const [activeTab, setActiveTab] = useState<SettingsTab>("smtp");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [brandingBusy, setBrandingBusy] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const [smtp, setSmtp] = useState<SmtpSettings | null>(null);
  const [branding, setBranding] = useState<BrandingSettings | null>(null);
  const [enabled, setEnabled] = useState(false);
  const [host, setHost] = useState("");
  const [port, setPort] = useState(587);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [fromEmail, setFromEmail] = useState("");
  const [useTls, setUseTls] = useState(true);
  const [clearPassword, setClearPassword] = useState(false);
  const [testRecipient, setTestRecipient] = useState("");

  const applySmtp = (value: SmtpSettings) => {
    setSmtp(value);
    setEnabled(value.enabled);
    setHost(value.host);
    setPort(value.port);
    setUsername(value.username);
    setFromEmail(value.fromEmail);
    setUseTls(value.useTls);
    setPassword("");
    setClearPassword(false);
  };

  useEffect(() => {
    void (async () => {
      try {
        const [smtpValue, brandingValue] = await Promise.all([
          getSmtpSettings(),
          getBrandingSettings(),
        ]);
        applySmtp(smtpValue);
        setBranding(brandingValue);
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : "Unable to load settings.");
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const logoSrc = useMemo(
    () => branding?.customLogo ? customLogoUrl(branding.updatedAt) : "/nusummit-logo.svg",
    [branding],
  );

  const handleTabChange = (_event: React.SyntheticEvent, value: SettingsTab) => {
    setActiveTab(value);
    setError("");
    setSuccess("");
  };

  const handleSaveSmtp = async () => {
    setSaving(true);
    setError("");
    setSuccess("");
    try {
      const updated = await saveSmtpSettings({
        enabled,
        host,
        port,
        username,
        password: password || undefined,
        fromEmail,
        useTls,
        clearPassword,
      });
      applySmtp(updated);
      setSuccess("SMTP settings saved successfully.");
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Unable to save SMTP settings.");
    } finally {
      setSaving(false);
    }
  };

  const handleTestSmtp = async () => {
    if (!testRecipient.trim()) {
      setError("Enter a recipient email before sending a test.");
      return;
    }
    setTesting(true);
    setError("");
    setSuccess("");
    try {
      await sendSmtpTest(testRecipient.trim());
      setSuccess(`Test email sent to ${testRecipient.trim()}.`);
    } catch (testError) {
      setError(testError instanceof Error ? testError.message : "SMTP test failed.");
    } finally {
      setTesting(false);
    }
  };

  const notifyBrandingChanged = () => {
    window.dispatchEvent(new Event("identityai-branding-updated"));
  };

  const handleLogoUpload = async (file: File | undefined) => {
    if (!file) return;
    setBrandingBusy(true);
    setError("");
    setSuccess("");
    try {
      const updated = await uploadLogo(file);
      setBranding(updated);
      notifyBrandingChanged();
      setSuccess("Header logo updated successfully.");
    } catch (uploadError) {
      setError(uploadError instanceof Error ? uploadError.message : "Unable to upload logo.");
    } finally {
      setBrandingBusy(false);
    }
  };

  const handleResetLogo = async () => {
    setBrandingBusy(true);
    setError("");
    setSuccess("");
    try {
      const updated = await resetLogo();
      setBranding(updated);
      notifyBrandingChanged();
      setSuccess("Header logo reset to the default logo.");
    } catch (resetError) {
      setError(resetError instanceof Error ? resetError.message : "Unable to reset logo.");
    } finally {
      setBrandingBusy(false);
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
      <Box>
        <Typography variant="h4" fontWeight={800}>Settings</Typography>
        <Typography color="text.secondary" sx={{ mt: 0.5 }}>
          Configure administrator-managed platform settings for email, branding, notifications, and downstream remediation integrations.
        </Typography>
      </Box>

      <Card variant="outlined">
        <Tabs value={activeTab} onChange={handleTabChange} variant="scrollable" scrollButtons="auto" sx={{ px: 2 }}>
          <Tab value="smtp" label="SMTP" />
          <Tab value="branding" label="Branding" />
          <Tab value="emailTemplates" label="Email Templates" />
          <Tab value="serviceDesk" label="Service Desk" />
          <Tab value="remediationSla" label="Remediation SLA" />
        </Tabs>
      </Card>

      {error && <Alert severity="error" onClose={() => setError("")}>{error}</Alert>}
      {success && <Alert severity="success" onClose={() => setSuccess("")}>{success}</Alert>}

      {activeTab === "smtp" && (
        <Card variant="outlined">
          <CardContent>
            <Stack spacing={2.5}>
              <Stack direction={{ xs: "column", sm: "row" }} justifyContent="space-between" gap={1}>
                <Box>
                  <Typography variant="h6" fontWeight={800}>SMTP Configuration</Typography>
                  <Typography variant="body2" color="text.secondary">Used by scheduled reports and other IdentityAI email notifications.</Typography>
                </Box>
                <Chip size="small" label={smtp?.source === "database" ? "Managed in IdentityAI" : smtp?.source === "environment" ? "Using environment values" : "Not configured"} color={smtp?.source === "database" ? "primary" : "default"} variant="outlined" />
              </Stack>
              <Divider />
              <FormControlLabel control={<Switch checked={enabled} onChange={(event) => setEnabled(event.target.checked)} />} label="Enable SMTP email delivery" />
              <Grid container spacing={2}>
                <Grid size={{ xs: 12, md: 8 }}><TextField fullWidth label="SMTP host" value={host} onChange={(event) => setHost(event.target.value)} placeholder="smtp.example.com" /></Grid>
                <Grid size={{ xs: 12, md: 4 }}><TextField fullWidth label="Port" type="number" value={port} onChange={(event) => setPort(Number(event.target.value))} inputProps={{ min: 1, max: 65535 }} /></Grid>
                <Grid size={{ xs: 12, md: 6 }}><TextField fullWidth label="Username" value={username} onChange={(event) => setUsername(event.target.value)} autoComplete="off" /></Grid>
                <Grid size={{ xs: 12, md: 6 }}><TextField fullWidth label={smtp?.passwordConfigured ? "Password (leave blank to keep current)" : "Password"} type="password" value={password} onChange={(event) => { setPassword(event.target.value); if (event.target.value) setClearPassword(false); }} autoComplete="new-password" /></Grid>
                <Grid size={{ xs: 12, md: 6 }}><TextField fullWidth label="From email" type="email" value={fromEmail} onChange={(event) => setFromEmail(event.target.value)} placeholder="identityai@example.com" /></Grid>
                <Grid size={{ xs: 12, md: 6 }} sx={{ display: "flex", alignItems: "center" }}><FormControlLabel control={<Switch checked={useTls} onChange={(event) => setUseTls(event.target.checked)} />} label="Use STARTTLS" /></Grid>
              </Grid>
              {smtp?.passwordConfigured && <FormControlLabel control={<Switch checked={clearPassword} onChange={(event) => { setClearPassword(event.target.checked); if (event.target.checked) setPassword(""); }} />} label="Clear the saved SMTP password" />}
              <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5}>
                <Button variant="contained" onClick={handleSaveSmtp} disabled={saving}>{saving ? "Saving…" : "Save SMTP settings"}</Button>
                <TextField size="small" label="Test recipient" type="email" value={testRecipient} onChange={(event) => setTestRecipient(event.target.value)} sx={{ minWidth: { sm: 280 } }} />
                <Button variant="outlined" startIcon={<SendOutlinedIcon />} onClick={handleTestSmtp} disabled={testing || !enabled}>{testing ? "Sending…" : "Send test email"}</Button>
              </Stack>
            </Stack>
          </CardContent>
        </Card>
      )}

      {activeTab === "branding" && (
        <Card variant="outlined">
          <CardContent>
            <Stack spacing={2.5}>
              <Box>
                <Typography variant="h6" fontWeight={800}>Header Branding</Typography>
                <Typography variant="body2" color="text.secondary">Upload the logo displayed in the application header. PNG, JPEG, and WebP are supported up to 2 MB.</Typography>
              </Box>
              <Divider />
              <Box sx={{ minHeight: 110, border: "1px dashed", borderColor: "divider", borderRadius: 2, bgcolor: "#0f172a", display: "flex", alignItems: "center", justifyContent: "center", px: 3, py: 2 }}>
                <Box component="img" src={logoSrc} alt="Header logo preview" sx={{ maxHeight: 64, maxWidth: "100%", objectFit: "contain" }} />
              </Box>
              <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5} alignItems={{ sm: "center" }}>
                <Button component="label" variant="contained" startIcon={<CloudUploadOutlinedIcon />} disabled={brandingBusy}>
                  {brandingBusy ? "Updating…" : "Upload logo"}
                  <input hidden type="file" accept="image/png,image/jpeg,image/webp" onChange={(event) => { void handleLogoUpload(event.target.files?.[0]); event.target.value = ""; }} />
                </Button>
                <Button variant="outlined" startIcon={<RestartAltIcon />} onClick={handleResetLogo} disabled={brandingBusy || !branding?.customLogo}>Reset to default</Button>
                {branding?.customLogo && <Typography variant="body2" color="text.secondary">Current file: {branding.filename || "custom logo"}</Typography>}
              </Stack>
            </Stack>
          </CardContent>
        </Card>
      )}

      {activeTab === "emailTemplates" && <EmailTemplatesCard />}
      {activeTab === "serviceDesk" && <ServiceDeskSettingsCard />}
      {activeTab === "remediationSla" && <RemediationSlaSettingsCard />}
    </Stack>
  );
};

export default Settings;
