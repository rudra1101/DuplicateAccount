import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Checkbox,
  Chip,
  CircularProgress,
  Divider,
  FormControlLabel,
  Grid,
  List,
  ListItemButton,
  ListItemText,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";
import SaveOutlinedIcon from "@mui/icons-material/SaveOutlined";
import { useEffect, useMemo, useState } from "react";

import { useAuth } from "../../auth/AuthContext";
import {
  createReportEmailTemplate,
  deleteReportEmailTemplate,
  getReportEmailTemplates,
  updateReportEmailTemplate,
  type ReportEmailTemplate,
  type ReportEmailTemplatePayload,
} from "../../services/reportEmailTemplateService";

const EMPTY_TEMPLATE: ReportEmailTemplatePayload = {
  name: "",
  subjectTemplate: "{{test_prefix}}IdentityAI Duplicate Risk Report",
  textBodyTemplate:
    "{{report_name}}\n\nPending review: {{pending_review}}\nConfirmed duplicates: {{confirmed_duplicates}}\nAwaiting remediation: {{awaiting_remediation}}\nHigh-confidence unresolved: {{high_confidence_unresolved}}\n\nThe current unresolved duplicate report is attached.",
  htmlBodyTemplate:
    "<h2>{{report_name}}</h2><p>Generated: {{generated_at}}</p><ul><li>Pending review: <strong>{{pending_review}}</strong></li><li>Confirmed duplicates: <strong>{{confirmed_duplicates}}</strong></li><li>Awaiting remediation: <strong>{{awaiting_remediation}}</strong></li><li>High-confidence unresolved: <strong>{{high_confidence_unresolved}}</strong></li></ul><p>The current unresolved duplicate report is attached.</p>",
  isActive: true,
};

function sampleRender(value: string): string {
  const values: Record<string, string> = {
    report_name: "Executive Duplicate Risk Report",
    generated_at: new Date().toLocaleString(),
    duplicate_groups: "42",
    duplicate_candidates: "118",
    pending_review: "31",
    confirmed_duplicates: "19",
    awaiting_remediation: "8",
    high_confidence_unresolved: "12",
    unresolved_rows: "31",
    recipient_count: "3",
    test_prefix: "TEST - ",
  };
  return value.replace(/{{\s*([a-zA-Z0-9_]+)\s*}}/g, (_, key: string) => values[key] ?? "");
}

function EmailTemplatesCard() {
  const { hasPermission } = useAuth();
  const canManage = hasPermission("report.manage_templates");
  const [templates, setTemplates] = useState<ReportEmailTemplate[]>([]);
  const [variables, setVariables] = useState<string[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [form, setForm] = useState<ReportEmailTemplatePayload>({ ...EMPTY_TEMPLATE });
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const loadTemplates = async () => {
    setLoading(true);
    try {
      const response = await getReportEmailTemplates();
      setTemplates(response.templates);
      setVariables(response.variables);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load templates.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (canManage) void loadTemplates();
  }, [canManage]);

  const selectedTemplate = useMemo(
    () => templates.find((item) => item.id === selectedId) ?? null,
    [templates, selectedId],
  );

  const selectTemplate = (template: ReportEmailTemplate) => {
    setSelectedId(template.id);
    setForm({
      name: template.name,
      subjectTemplate: template.subjectTemplate,
      textBodyTemplate: template.textBodyTemplate,
      htmlBodyTemplate: template.htmlBodyTemplate,
      isActive: template.isActive,
    });
    setMessage("");
    setError("");
  };

  const createNew = () => {
    setSelectedId(null);
    setForm({ ...EMPTY_TEMPLATE });
    setMessage("");
    setError("");
  };

  const save = async () => {
    try {
      setSaving(true);
      setError("");
      const saved = selectedId
        ? await updateReportEmailTemplate(selectedId, form)
        : await createReportEmailTemplate(form);
      await loadTemplates();
      setSelectedId(saved.id);
      setForm({
        name: saved.name,
        subjectTemplate: saved.subjectTemplate,
        textBodyTemplate: saved.textBodyTemplate,
        htmlBodyTemplate: saved.htmlBodyTemplate,
        isActive: saved.isActive,
      });
      setMessage(selectedId ? "Email template updated." : "Email template created.");
      window.dispatchEvent(new Event("report-email-templates-changed"));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to save template.");
    } finally {
      setSaving(false);
    }
  };

  const remove = async () => {
    if (!selectedTemplate) return;
    try {
      setSaving(true);
      setError("");
      await deleteReportEmailTemplate(selectedTemplate.id);
      createNew();
      await loadTemplates();
      setMessage("Email template deleted.");
      window.dispatchEvent(new Event("report-email-templates-changed"));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to delete template.");
    } finally {
      setSaving(false);
    }
  };

  if (!canManage) return null;

  return (
    <Card variant="outlined">
      <CardContent>
        <Stack spacing={2.5}>
          <Stack direction={{ xs: "column", md: "row" }} justifyContent="space-between" spacing={2}>
            <Box>
              <Typography variant="h6" fontWeight={700}>Report Email Templates</Typography>
              <Typography variant="body2" color="text.secondary">
                Create reusable subject, plain-text, and HTML bodies for scheduled report emails.
              </Typography>
            </Box>
            <Button startIcon={<AddIcon />} variant="outlined" onClick={createNew}>
              New Template
            </Button>
          </Stack>

          {message && <Alert severity="success">{message}</Alert>}
          {error && <Alert severity="error">{error}</Alert>}

          <Grid container spacing={2.5}>
            <Grid size={{ xs: 12, md: 4 }}>
              <Typography variant="subtitle2" fontWeight={700} sx={{ mb: 1 }}>Templates</Typography>
              {loading ? (
                <Box sx={{ py: 4, textAlign: "center" }}><CircularProgress size={24} /></Box>
              ) : (
                <List disablePadding>
                  {templates.length === 0 && (
                    <Typography variant="body2" color="text.secondary">No templates created yet.</Typography>
                  )}
                  {templates.map((template) => (
                    <ListItemButton
                      key={template.id}
                      selected={template.id === selectedId}
                      onClick={() => selectTemplate(template)}
                      sx={{ borderRadius: 2, mb: 0.5 }}
                    >
                      <ListItemText
                        primary={template.name}
                        secondary={template.isActive ? "Active" : "Inactive"}
                      />
                    </ListItemButton>
                  ))}
                </List>
              )}
            </Grid>

            <Grid size={{ xs: 12, md: 8 }}>
              <Stack spacing={2}>
                <TextField
                  label="Template name"
                  value={form.name}
                  onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))}
                  fullWidth
                />
                <TextField
                  label="Subject"
                  value={form.subjectTemplate}
                  onChange={(event) => setForm((current) => ({ ...current, subjectTemplate: event.target.value }))}
                  fullWidth
                />
                <TextField
                  label="Plain-text body"
                  value={form.textBodyTemplate}
                  onChange={(event) => setForm((current) => ({ ...current, textBodyTemplate: event.target.value }))}
                  multiline
                  minRows={7}
                  fullWidth
                />
                <TextField
                  label="HTML body"
                  value={form.htmlBodyTemplate}
                  onChange={(event) => setForm((current) => ({ ...current, htmlBodyTemplate: event.target.value }))}
                  multiline
                  minRows={9}
                  fullWidth
                  helperText="Optional. HTML is sent as the rich email alternative; scripts are not needed."
                />
                <FormControlLabel
                  control={(
                    <Checkbox
                      checked={form.isActive}
                      onChange={(event) => setForm((current) => ({ ...current, isActive: event.target.checked }))}
                    />
                  )}
                  label="Template is active and selectable for scheduled reports"
                />

                <Box>
                  <Typography variant="subtitle2" fontWeight={700} sx={{ mb: 1 }}>Available variables</Typography>
                  <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap">
                    {variables.map((variable) => (
                      <Chip key={variable} size="small" label={`{{${variable}}}`} variant="outlined" />
                    ))}
                  </Stack>
                </Box>

                <Divider />
                <Box>
                  <Typography variant="subtitle2" fontWeight={700} sx={{ mb: 1 }}>Sample preview</Typography>
                  <Typography variant="body2" sx={{ mb: 1 }}>
                    <strong>Subject:</strong> {sampleRender(form.subjectTemplate)}
                  </Typography>
                  {form.htmlBodyTemplate.trim() ? (
                    <Box
                      component="iframe"
                      title="Email template preview"
                      sandbox=""
                      srcDoc={sampleRender(form.htmlBodyTemplate)}
                      sx={{ width: "100%", minHeight: 280, border: "1px solid", borderColor: "divider", borderRadius: 1 }}
                    />
                  ) : (
                    <Box component="pre" sx={{ whiteSpace: "pre-wrap", m: 0, p: 2, bgcolor: "action.hover", borderRadius: 1 }}>
                      {sampleRender(form.textBodyTemplate)}
                    </Box>
                  )}
                </Box>

                <Stack direction="row" spacing={1.5}>
                  <Button
                    variant="contained"
                    startIcon={<SaveOutlinedIcon />}
                    onClick={() => void save()}
                    disabled={saving}
                  >
                    {saving ? "Saving..." : selectedId ? "Update Template" : "Create Template"}
                  </Button>
                  {selectedId && (
                    <Button
                      color="error"
                      variant="outlined"
                      startIcon={<DeleteOutlineIcon />}
                      onClick={() => void remove()}
                      disabled={saving}
                    >
                      Delete
                    </Button>
                  )}
                </Stack>
              </Stack>
            </Grid>
          </Grid>
        </Stack>
      </CardContent>
    </Card>
  );
}

export default EmailTemplatesCard;
