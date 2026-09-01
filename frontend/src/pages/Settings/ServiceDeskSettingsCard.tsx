import {
  Alert,
  Button,
  Card,
  CardContent,
  FormControl,
  FormControlLabel,
  Grid,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  Switch,
  TextField,
  Typography,
} from "@mui/material";
import SaveOutlinedIcon from "@mui/icons-material/SaveOutlined";
import { useEffect, useState } from "react";

import {
  getServiceDeskSettings,
  saveServiceDeskSettings,
  type ServiceDeskSettings,
} from "../../services/settingsService";

function ServiceDeskSettingsCard() {
  const [config, setConfig] = useState<ServiceDeskSettings | null>(null);
  const [secret, setSecret] = useState("");
  const [clearSecret, setClearSecret] = useState(false);
  const [completedStatuses, setCompletedStatuses] = useState("");
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    void (async () => {
      try {
        const value = await getServiceDeskSettings();
        setConfig(value);
        setCompletedStatuses(value.completedStatuses.join(", "));
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unable to load Service Desk settings.");
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  if (loading) {
    return <Typography color="text.secondary">Loading Service Desk configuration…</Typography>;
  }

  if (!config) {
    return <Alert severity="error">{error || "Service Desk configuration is unavailable."}</Alert>;
  }

  const update = <K extends keyof ServiceDeskSettings>(key: K, value: ServiceDeskSettings[K]) => {
    setConfig((current) => current ? { ...current, [key]: value } : current);
    setMessage("");
    setError("");
  };

  const save = async () => {
    try {
      setSaving(true);
      setMessage("");
      setError("");
      const saved = await saveServiceDeskSettings({
        enabled: config.enabled,
        name: config.name,
        baseUrl: config.baseUrl,
        authType: config.authType,
        username: config.username,
        secret: secret || undefined,
        clearSecret,
        createPath: config.createPath,
        statusPath: config.statusPath,
        ticketIdField: config.ticketIdField,
        ticketStatusField: config.ticketStatusField,
        ticketUrlField: config.ticketUrlField,
        completedStatuses: completedStatuses.split(/[;,\n]/).map((item) => item.trim()).filter(Boolean),
        payloadTemplate: config.payloadTemplate,
        verifyTls: config.verifyTls,
      });
      setConfig(saved);
      setCompletedStatuses(saved.completedStatuses.join(", "));
      setSecret("");
      setClearSecret(false);
      setMessage("Service Desk integration settings saved.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to save Service Desk settings.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Card variant="outlined">
      <CardContent>
        <Stack spacing={2.5}>
          <div>
            <Typography variant="h6" fontWeight={800}>Service Desk Integration</Typography>
            <Typography variant="body2" color="text.secondary">
              Configure the REST service used to create disable/delete tickets and synchronize ticket completion back into remediation.
            </Typography>
          </div>

          {message && <Alert severity="success">{message}</Alert>}
          {error && <Alert severity="error">{error}</Alert>}

          <FormControlLabel
            control={<Switch checked={config.enabled} onChange={(event) => update("enabled", event.target.checked)} />}
            label="Enable Service Desk remediation"
          />

          <Grid container spacing={2}>
            <Grid size={{ xs: 12, md: 6 }}>
              <TextField fullWidth label="Integration name" value={config.name} onChange={(event) => update("name", event.target.value)} placeholder="Corporate Service Desk" />
            </Grid>
            <Grid size={{ xs: 12, md: 6 }}>
              <TextField fullWidth label="Base URL" value={config.baseUrl} onChange={(event) => update("baseUrl", event.target.value)} placeholder="https://servicedesk.example.com" />
            </Grid>
            <Grid size={{ xs: 12, md: 4 }}>
              <FormControl fullWidth>
                <InputLabel>Authentication</InputLabel>
                <Select value={config.authType} label="Authentication" onChange={(event) => update("authType", event.target.value as ServiceDeskSettings["authType"])}>
                  <MenuItem value="BEARER">Bearer token</MenuItem>
                  <MenuItem value="BASIC">Basic authentication</MenuItem>
                  <MenuItem value="NONE">No authentication</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            <Grid size={{ xs: 12, md: 4 }}>
              <TextField fullWidth label="Username" disabled={config.authType !== "BASIC"} value={config.username} onChange={(event) => update("username", event.target.value)} />
            </Grid>
            <Grid size={{ xs: 12, md: 4 }}>
              <TextField
                fullWidth
                type="password"
                label={config.secretConfigured ? "Token / password (leave blank to keep)" : "Token / password"}
                disabled={config.authType === "NONE"}
                value={secret}
                onChange={(event) => {
                  setSecret(event.target.value);
                  if (event.target.value) setClearSecret(false);
                }}
                autoComplete="new-password"
              />
            </Grid>
            <Grid size={{ xs: 12, md: 6 }}>
              <TextField fullWidth label="Create ticket path" value={config.createPath} onChange={(event) => update("createPath", event.target.value)} placeholder="/api/tickets" />
            </Grid>
            <Grid size={{ xs: 12, md: 6 }}>
              <TextField fullWidth label="Ticket status path" value={config.statusPath} onChange={(event) => update("statusPath", event.target.value)} helperText="Must contain {ticket_id}, for example /api/tickets/{ticket_id}." />
            </Grid>
            <Grid size={{ xs: 12, md: 4 }}>
              <TextField fullWidth label="Ticket ID field" value={config.ticketIdField} onChange={(event) => update("ticketIdField", event.target.value)} helperText="Dot notation supported, e.g. result.number" />
            </Grid>
            <Grid size={{ xs: 12, md: 4 }}>
              <TextField fullWidth label="Ticket status field" value={config.ticketStatusField} onChange={(event) => update("ticketStatusField", event.target.value)} helperText="Dot notation supported, e.g. result.state" />
            </Grid>
            <Grid size={{ xs: 12, md: 4 }}>
              <TextField fullWidth label="Ticket URL field" value={config.ticketUrlField} onChange={(event) => update("ticketUrlField", event.target.value)} helperText="Optional response field containing a ticket link." />
            </Grid>
            <Grid size={{ xs: 12 }}>
              <TextField fullWidth label="Completed ticket statuses" value={completedStatuses} onChange={(event) => setCompletedStatuses(event.target.value)} helperText="Comma-separated values. Matching is case-insensitive." />
            </Grid>
            <Grid size={{ xs: 12 }}>
              <TextField
                fullWidth
                multiline
                minRows={7}
                label="Create-ticket JSON payload template"
                value={config.payloadTemplate}
                onChange={(event) => update("payloadTemplate", event.target.value)}
                helperText="Available variables: {{summary}}, {{description}}, {{action}}, {{account_key}}, {{application}}, {{integration_id}}, {{username}}, {{email}}"
              />
            </Grid>
          </Grid>

          {config.secretConfigured && config.authType !== "NONE" && (
            <FormControlLabel
              control={<Switch checked={clearSecret} onChange={(event) => {
                setClearSecret(event.target.checked);
                if (event.target.checked) setSecret("");
              }} />}
              label="Clear stored Service Desk credential"
            />
          )}

          <FormControlLabel
            control={<Switch checked={config.verifyTls} onChange={(event) => update("verifyTls", event.target.checked)} />}
            label="Verify TLS certificates"
          />

          <Button variant="contained" startIcon={<SaveOutlinedIcon />} onClick={() => void save()} disabled={saving} sx={{ alignSelf: "flex-start" }}>
            {saving ? "Saving…" : "Save Service Desk settings"}
          </Button>
        </Stack>
      </CardContent>
    </Card>
  );
}

export default ServiceDeskSettingsCard;
