import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Checkbox,
  Chip,
  CircularProgress,
  FormControl,
  FormControlLabel,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import EmailOutlinedIcon from "@mui/icons-material/EmailOutlined";
import SendOutlinedIcon from "@mui/icons-material/SendOutlined";
import SaveOutlinedIcon from "@mui/icons-material/SaveOutlined";
import { useEffect, useMemo, useState } from "react";

import { useAuth } from "../../auth/AuthContext";
import { getReportEmailTemplates, type ReportEmailTemplate } from "../../services/reportEmailTemplateService";
import {
  getScheduledReport,
  sendScheduledReportTest,
  updateScheduledReport,
  type ExecutiveDuplicateSnapshot,
  type ScheduledFrequency,
  type ScheduledReportConfig,
} from "../../services/scheduledReportService";


function formatDate(value: string | null): string {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

function ScheduledExecutiveReportCard() {
  const { hasPermission } = useAuth();
  const canManage = hasPermission("report.manage_schedule");
  const canManageTemplates = hasPermission("report.manage_templates");

  const [config, setConfig] = useState<ScheduledReportConfig | null>(null);
  const [snapshot, setSnapshot] = useState<ExecutiveDuplicateSnapshot | null>(null);
  const [templates, setTemplates] = useState<ReportEmailTemplate[]>([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [recipientText, setRecipientText] = useState("");

  useEffect(() => {
    if (!canManage) return;

    let active = true;
    const load = async () => {
      try {
        setLoading(true);
        const result = await getScheduledReport();
        if (!active) return;
        setConfig(result.config);
        setSnapshot(result.snapshot);
        setRecipientText(result.config.recipientEmails.join(", "));

        if (canManageTemplates) {
          const templateResult = await getReportEmailTemplates();
          if (active) setTemplates(templateResult.templates.filter((item) => item.isActive));
        }
      } catch (err) {
        if (active) {
          setError(err instanceof Error ? err.message : "Unable to load scheduled report settings.");
        }
      } finally {
        if (active) setLoading(false);
      }
    };

    void load();
    const refreshTemplates = () => void load();
    window.addEventListener("report-email-templates-changed", refreshTemplates);
    return () => {
      active = false;
      window.removeEventListener("report-email-templates-changed", refreshTemplates);
    };
  }, [canManage, canManageTemplates]);

  const recipients = useMemo(
    () => recipientText
      .split(/[;,\n]/)
      .map((item) => item.trim())
      .filter(Boolean),
    [recipientText],
  );

  if (!canManage) return null;

  if (loading && !config) {
    return (
      <Card variant="outlined">
        <CardContent sx={{ display: "flex", justifyContent: "center", py: 5 }}>
          <CircularProgress size={28} />
        </CardContent>
      </Card>
    );
  }

  if (!config) {
    return error ? <Alert severity="error">{error}</Alert> : null;
  }

  const updateConfig = <K extends keyof ScheduledReportConfig>(
    key: K,
    value: ScheduledReportConfig[K],
  ) => {
    setConfig((current) => current ? { ...current, [key]: value } : current);
    setMessage("");
    setError("");
  };

  const toggleColumn = (key: string) => {
    const selected = new Set(config.selectedColumns);
    if (selected.has(key)) selected.delete(key);
    else selected.add(key);
    updateConfig("selectedColumns", Array.from(selected));
  };

  const saveSchedule = async (): Promise<ScheduledReportConfig> => {
    const saved = await updateScheduledReport({
      enabled: config.enabled,
      frequency: config.frequency,
      includeAdmins: config.includeAdmins,
      recipientEmails: recipients,
      selectedColumns: config.selectedColumns,
      emailTemplateId: config.emailTemplateId,
    });
    setConfig(saved);
    setRecipientText(saved.recipientEmails.join(", "));
    return saved;
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      setMessage("");
      setError("");
      await saveSchedule();
      setMessage("Scheduled report settings saved.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to save scheduled report settings.");
    } finally {
      setSaving(false);
    }
  };

  const handleTest = async () => {
    try {
      setTesting(true);
      setMessage("");
      setError("");
      await saveSchedule();
      await sendScheduledReportTest();
      window.dispatchEvent(new Event("scheduled-report-generated"));
      setMessage("Test report sent successfully and added to report history.");
    } catch (err) {
      window.dispatchEvent(new Event("scheduled-report-generated"));
      setError(err instanceof Error ? err.message : "Unable to send test report.");
    } finally {
      setTesting(false);
    }
  };

  return (
    <Card variant="outlined">
      <CardContent>
        <Stack spacing={2.5}>
          <Stack direction={{ xs: "column", md: "row" }} justifyContent="space-between" spacing={2}>
            <Box>
              <Stack direction="row" spacing={1} alignItems="center">
                <EmailOutlinedIcon />
                <Typography variant="h6" fontWeight={700}>
                  Scheduled Executive Duplicate Report
                </Typography>
              </Stack>
              <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                Configure delivery frequency, recipients, email template, and CSV detail columns.
              </Typography>
            </Box>
            <Chip
              label={config.enabled ? "Enabled" : "Disabled"}
              color={config.enabled ? "success" : "default"}
              variant="outlined"
            />
          </Stack>

          {snapshot && (
            <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap">
              <Chip label={`Pending review: ${snapshot.pendingReview}`} />
              <Chip label={`Awaiting remediation: ${snapshot.awaitingRemediation}`} />
              <Chip label={`Confirmed duplicates: ${snapshot.confirmedDuplicates}`} />
              <Chip label={`High confidence unresolved: ${snapshot.highConfidenceUnresolved}`} />
              <Chip label={`Detected groups: ${snapshot.duplicateGroups}`} variant="outlined" />
            </Stack>
          )}

          {message && <Alert severity="success">{message}</Alert>}
          {error && <Alert severity="error">{error}</Alert>}

          <FormControlLabel
            control={(
              <Checkbox
                checked={config.enabled}
                onChange={(event) => updateConfig("enabled", event.target.checked)}
              />
            )}
            label="Enable scheduled delivery"
          />

          <FormControl fullWidth>
            <InputLabel>Frequency</InputLabel>
            <Select
              value={config.frequency}
              label="Frequency"
              onChange={(event) => updateConfig("frequency", event.target.value as ScheduledFrequency)}
            >
              <MenuItem value="WEEKLY">Weekly</MenuItem>
              <MenuItem value="MONTHLY">Monthly</MenuItem>
              <MenuItem value="QUARTERLY">Quarterly</MenuItem>
            </Select>
          </FormControl>

          <FormControl fullWidth>
            <InputLabel>Email Template</InputLabel>
            <Select
              value={config.emailTemplateId ?? ""}
              label="Email Template"
              onChange={(event) =>
                updateConfig(
                  "emailTemplateId",
                  event.target.value === "" ? null : Number(event.target.value),
                )
              }
            >
              <MenuItem value="">System default template</MenuItem>
              {templates.map((template) => (
                <MenuItem key={template.id} value={template.id}>
                  {template.name}
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          <FormControlLabel
            control={(
              <Checkbox
                checked={config.includeAdmins}
                onChange={(event) => updateConfig("includeAdmins", event.target.checked)}
              />
            )}
            label="Automatically send to all active Admins and Owners"
          />

          <TextField
            fullWidth
            label="Additional recipients"
            value={recipientText}
            onChange={(event) => setRecipientText(event.target.value)}
            placeholder="security@example.com, governance@example.com"
            helperText="Separate email addresses with commas or semicolons."
          />

          <Box>
            <Typography variant="subtitle2" fontWeight={700} sx={{ mb: 1 }}>
              CSV detail columns
            </Typography>
            <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap">
              {config.availableColumns.map((column) => (
                <FormControlLabel
                  key={column.key}
                  control={(
                    <Checkbox
                      size="small"
                      checked={config.selectedColumns.includes(column.key)}
                      onChange={() => toggleColumn(column.key)}
                    />
                  )}
                  label={column.label}
                />
              ))}
            </Stack>
          </Box>

          <Stack direction={{ xs: "column", md: "row" }} spacing={3}>
            <Typography variant="body2" color="text.secondary">
              Next run: <strong>{formatDate(config.nextRunAt)}</strong>
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Last sent: <strong>{formatDate(config.lastSentAt)}</strong>
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Last status: <strong>{config.lastStatus ?? "—"}</strong>
            </Typography>
          </Stack>

          {config.lastError && (
            <Alert severity="warning">Last delivery error: {config.lastError}</Alert>
          )}

          <Stack direction="row" spacing={1.5}>
            <Button
              variant="contained"
              startIcon={<SaveOutlinedIcon />}
              disabled={saving || testing}
              onClick={() => void handleSave()}
            >
              {saving ? "Saving..." : "Save Schedule"}
            </Button>
            <Button
              variant="outlined"
              startIcon={<SendOutlinedIcon />}
              disabled={saving || testing}
              onClick={() => void handleTest()}
            >
              {testing ? "Sending..." : "Send Test Email"}
            </Button>
          </Stack>

          <Typography variant="caption" color="text.secondary">
            Delivery time is fixed at 09:00 {config.timezone}. Weekly runs on Monday;
            monthly runs on the 1st; quarterly runs on Jan/Apr/Jul/Oct 1st.
          </Typography>
        </Stack>
      </CardContent>
    </Card>
  );
}

export default ScheduledExecutiveReportCard;
