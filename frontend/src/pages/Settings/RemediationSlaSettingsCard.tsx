import { useEffect, useState } from "react";
import {
  Alert,
  Button,
  Card,
  CardContent,
  Divider,
  FormControlLabel,
  Grid,
  Stack,
  Switch,
  TextField,
  Typography,
} from "@mui/material";

import {
  getRemediationSlaSettings,
  saveRemediationSlaSettings,
} from "../../services/settingsService";

const RemediationSlaSettingsCard = () => {
  const [enabled, setEnabled] = useState(false);
  const [slaHours, setSlaHours] = useState(72);
  const [warningHours, setWarningHours] = useState(24);
  const [autoEscalate, setAutoEscalate] = useState(true);
  const [emails, setEmails] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  useEffect(() => {
    void (async () => {
      try {
        const value = await getRemediationSlaSettings();
        setEnabled(value.enabled);
        setSlaHours(value.slaHours);
        setWarningHours(value.warningHours);
        setAutoEscalate(value.autoEscalate);
        setEmails(value.escalationEmails.join(", "));
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : "Unable to load remediation SLA settings.");
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const save = async () => {
    try {
      setSaving(true);
      setError("");
      setSuccess("");
      const escalationEmails = emails
        .split(/[;,]/)
        .map((item) => item.trim())
        .filter(Boolean);
      const value = await saveRemediationSlaSettings({
        enabled,
        slaHours,
        warningHours,
        autoEscalate,
        escalationEmails,
      });
      setEnabled(value.enabled);
      setSlaHours(value.slaHours);
      setWarningHours(value.warningHours);
      setAutoEscalate(value.autoEscalate);
      setEmails(value.escalationEmails.join(", "));
      setSuccess("Remediation SLA settings saved successfully.");
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Unable to save remediation SLA settings.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Card variant="outlined">
      <CardContent>
        <Stack spacing={2.5}>
          <div>
            <Typography variant="h6" fontWeight={800}>Remediation SLA & Escalation</Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
              Track remediation deadlines, show warning/overdue states, and automatically notify escalation recipients after an SLA breach.
            </Typography>
          </div>
          <Divider />
          {error && <Alert severity="error" onClose={() => setError("")}>{error}</Alert>}
          {success && <Alert severity="success" onClose={() => setSuccess("")}>{success}</Alert>}
          <FormControlLabel
            control={<Switch checked={enabled} onChange={(event) => setEnabled(event.target.checked)} disabled={loading} />}
            label="Enable remediation SLA tracking"
          />
          <Grid container spacing={2}>
            <Grid size={{ xs: 12, md: 6 }}>
              <TextField
                fullWidth
                type="number"
                label="SLA duration (hours)"
                value={slaHours}
                onChange={(event) => setSlaHours(Number(event.target.value))}
                inputProps={{ min: 1, max: 8760 }}
                helperText="Example: 72 hours = 3 days."
                disabled={loading || !enabled}
              />
            </Grid>
            <Grid size={{ xs: 12, md: 6 }}>
              <TextField
                fullWidth
                type="number"
                label="Warning before due (hours)"
                value={warningHours}
                onChange={(event) => setWarningHours(Number(event.target.value))}
                inputProps={{ min: 0 }}
                helperText="Items enter SLA Warning this many hours before the deadline."
                disabled={loading || !enabled}
              />
            </Grid>
          </Grid>
          <FormControlLabel
            control={<Switch checked={autoEscalate} onChange={(event) => setAutoEscalate(event.target.checked)} disabled={loading || !enabled} />}
            label="Automatically escalate overdue remediation items"
          />
          <TextField
            fullWidth
            label="Escalation recipients"
            value={emails}
            onChange={(event) => setEmails(event.target.value)}
            placeholder="security@example.com, iam-ops@example.com"
            helperText="Comma- or semicolon-separated email addresses. SMTP must be configured for email delivery."
            disabled={loading || !enabled || !autoEscalate}
          />
          <Alert severity="info">
            SLA checks run every 15 minutes. New duplicate remediation items receive a deadline when SLA tracking is enabled. Completed and ignored items stop consuming SLA time.
          </Alert>
          <div>
            <Button variant="contained" onClick={() => void save()} disabled={loading || saving}>
              {saving ? "Saving…" : "Save SLA settings"}
            </Button>
          </div>
        </Stack>
      </CardContent>
    </Card>
  );
};

export default RemediationSlaSettingsCard;
