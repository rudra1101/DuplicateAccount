import { useEffect, useMemo, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Chip,
  FormControl,
  IconButton,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";
import SaveIcon from "@mui/icons-material/Save";

import PageContainer from "../../components/common/PageContainer";
import {
  createCorrelationPolicy,
  deleteCorrelationPolicy,
  getCorrelationIntegrations,
  getCorrelationPolicies,
  getSourceApplications,
  setIntegrationPurpose,
  type CorrelationIntegration,
  type CorrelationMatchType,
  type CorrelationPolicy,
  type CorrelationRule,
  type SourcePurpose,
} from "../../services/correlationPolicyService";

const newRule = (priority: number): CorrelationRule => ({
  priority,
  accountAttribute: "",
  identityAttribute: "",
  matchType: "EXACT",
  enabled: true,
});

const CorrelationPolicies = () => {
  const [integrations, setIntegrations] = useState<CorrelationIntegration[]>([]);
  const [policies, setPolicies] = useState<CorrelationPolicy[]>([]);
  const [accountIntegrationId, setAccountIntegrationId] = useState<number | "">("");
  const [authoritativeIntegrationId, setAuthoritativeIntegrationId] = useState<number | "">("");
  const [policyName, setPolicyName] = useState("");
  const [rules, setRules] = useState<CorrelationRule[]>([newRule(1)]);
  const [accountAttributes, setAccountAttributes] = useState<string[]>([]);
  const [identityAttributes, setIdentityAttributes] = useState<string[]>([]);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [saving, setSaving] = useState(false);

  const accountSources = useMemo(
    () => integrations.filter((item) => item.sourcePurpose === "ACCOUNT"),
    [integrations],
  );
  const authoritativeSources = useMemo(
    () => integrations.filter((item) => item.sourcePurpose === "AUTHORITATIVE"),
    [integrations],
  );

  const load = async () => {
    const [integrationData, policyData] = await Promise.all([
      getCorrelationIntegrations(),
      getCorrelationPolicies(),
    ]);
    setIntegrations(integrationData);
    setPolicies(policyData);
  };

  useEffect(() => {
    void load().catch((loadError) => {
      setError(loadError instanceof Error ? loadError.message : "Unable to load correlation configuration.");
    });
  }, []);

  const loadAttributes = async (integrationId: number, identitySide: boolean) => {
    const applications = await getSourceApplications(integrationId);
    const attributes = Array.from(
      new Set(
        applications.flatMap((application) =>
          application.schema?.attributes.map((attribute) => attribute.name) ?? [],
        ),
      ),
    ).sort((a, b) => a.localeCompare(b));
    if (identitySide) setIdentityAttributes(attributes);
    else setAccountAttributes(attributes);
  };

  const changePurpose = async (integrationId: number, sourcePurpose: SourcePurpose) => {
    try {
      setError("");
      await setIntegrationPurpose(integrationId, sourcePurpose);
      setIntegrations((current) =>
        current.map((item) => item.id === integrationId ? { ...item, sourcePurpose } : item),
      );
      setMessage("Source purpose updated.");
    } catch (changeError) {
      setError(changeError instanceof Error ? changeError.message : "Unable to update source purpose.");
    }
  };

  const updateRule = (index: number, patch: Partial<CorrelationRule>) => {
    setRules((current) => current.map((rule, ruleIndex) =>
      ruleIndex === index ? { ...rule, ...patch } : rule,
    ));
  };

  const removeRule = (index: number) => {
    setRules((current) =>
      current
        .filter((_, ruleIndex) => ruleIndex !== index)
        .map((rule, ruleIndex) => ({ ...rule, priority: ruleIndex + 1 })),
    );
  };

  const savePolicy = async () => {
    if (!accountIntegrationId || !authoritativeIntegrationId) {
      setError("Select both the account source and authoritative source.");
      return;
    }
    if (!policyName.trim()) {
      setError("Policy name is required.");
      return;
    }
    if (rules.some((rule) => !rule.accountAttribute || !rule.identityAttribute)) {
      setError("Every rule requires an account attribute and identity attribute.");
      return;
    }

    try {
      setSaving(true);
      setError("");
      const created = await createCorrelationPolicy({
        name: policyName.trim(),
        accountIntegrationId,
        authoritativeIntegrationId,
        strategy: "FIRST_MATCH_WINS",
        enabled: true,
        rules: rules.map((rule, index) => ({ ...rule, priority: index + 1 })),
      });
      setPolicies((current) => [...current, created]);
      setPolicyName("");
      setRules([newRule(1)]);
      setMessage("Correlation policy saved. Orphan detection will now use these rules in priority order.");
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Unable to save correlation policy.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <PageContainer title="Correlation Policies">
      <Stack spacing={3}>
        <Box>
          <Typography variant="h5" fontWeight={700}>Identity Correlation Policies</Typography>
          <Typography color="text.secondary" sx={{ mt: 0.5 }}>
            You decide how account records are correlated to authoritative identities. Rules run in priority order and the first unique match wins.
          </Typography>
        </Box>

        {error && <Alert severity="error">{error}</Alert>}
        {message && <Alert severity="success" onClose={() => setMessage("")}>{message}</Alert>}

        <Paper variant="outlined" sx={{ p: 3, borderRadius: 3 }}>
          <Typography variant="h6" fontWeight={700} sx={{ mb: 2 }}>1. Classify Sources</Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Mark HR/Workday-style feeds as Authoritative. AD, Entra, SAP and other target systems normally remain Account sources.
          </Typography>
          <Table size="small">
            <TableHead><TableRow><TableCell>Integration</TableCell><TableCell>Connector</TableCell><TableCell>Purpose</TableCell></TableRow></TableHead>
            <TableBody>
              {integrations.map((integration) => (
                <TableRow key={integration.id}>
                  <TableCell>{integration.name}</TableCell>
                  <TableCell>{integration.connectorType}</TableCell>
                  <TableCell sx={{ width: 260 }}>
                    <Select
                      size="small"
                      fullWidth
                      value={integration.sourcePurpose}
                      onChange={(event) => void changePurpose(integration.id, event.target.value as SourcePurpose)}
                    >
                      <MenuItem value="ACCOUNT">Account Source</MenuItem>
                      <MenuItem value="AUTHORITATIVE">Authoritative Identity Source</MenuItem>
                    </Select>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Paper>

        <Paper variant="outlined" sx={{ p: 3, borderRadius: 3 }}>
          <Typography variant="h6" fontWeight={700} sx={{ mb: 2 }}>2. Create Correlation Policy</Typography>
          <Stack spacing={2.5}>
            <TextField label="Policy Name" value={policyName} onChange={(event) => setPolicyName(event.target.value)} placeholder="AD to Workday correlation" />
            <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
              <FormControl fullWidth>
                <InputLabel>Account Source</InputLabel>
                <Select
                  label="Account Source"
                  value={accountIntegrationId}
                  onChange={(event) => {
                    const id = Number(event.target.value);
                    setAccountIntegrationId(id);
                    void loadAttributes(id, false).catch((loadError) => setError(loadError instanceof Error ? loadError.message : "Unable to load account schema."));
                  }}
                >
                  {accountSources.map((source) => <MenuItem key={source.id} value={source.id}>{source.name}</MenuItem>)}
                </Select>
              </FormControl>
              <FormControl fullWidth>
                <InputLabel>Authoritative Source</InputLabel>
                <Select
                  label="Authoritative Source"
                  value={authoritativeIntegrationId}
                  onChange={(event) => {
                    const id = Number(event.target.value);
                    setAuthoritativeIntegrationId(id);
                    void loadAttributes(id, true).catch((loadError) => setError(loadError instanceof Error ? loadError.message : "Unable to load identity schema."));
                  }}
                >
                  {authoritativeSources.map((source) => <MenuItem key={source.id} value={source.id}>{source.name}</MenuItem>)}
                </Select>
              </FormControl>
            </Stack>

            <Alert severity="info">
              Strategy: First unique match wins. If a rule matches multiple identities, the account is flagged as an ambiguous correlation instead of being linked automatically.
            </Alert>

            <Table size="small">
              <TableHead><TableRow><TableCell>Priority</TableCell><TableCell>Account Attribute</TableCell><TableCell>Identity Attribute</TableCell><TableCell>Match Type</TableCell><TableCell /></TableRow></TableHead>
              <TableBody>
                {rules.map((rule, index) => (
                  <TableRow key={index}>
                    <TableCell>{index + 1}</TableCell>
                    <TableCell>
                      <Select size="small" fullWidth value={rule.accountAttribute} onChange={(event) => updateRule(index, { accountAttribute: event.target.value })}>
                        {accountAttributes.map((attribute) => <MenuItem key={attribute} value={attribute}>{attribute}</MenuItem>)}
                      </Select>
                    </TableCell>
                    <TableCell>
                      <Select size="small" fullWidth value={rule.identityAttribute} onChange={(event) => updateRule(index, { identityAttribute: event.target.value })}>
                        {identityAttributes.map((attribute) => <MenuItem key={attribute} value={attribute}>{attribute}</MenuItem>)}
                      </Select>
                    </TableCell>
                    <TableCell>
                      <Select size="small" value={rule.matchType} onChange={(event) => updateRule(index, { matchType: event.target.value as CorrelationMatchType })}>
                        <MenuItem value="EXACT">Exact</MenuItem>
                        <MenuItem value="CASE_INSENSITIVE">Case-insensitive</MenuItem>
                        <MenuItem value="NORMALIZED">Normalized</MenuItem>
                      </Select>
                    </TableCell>
                    <TableCell align="right">
                      <IconButton color="error" disabled={rules.length === 1} onClick={() => removeRule(index)}><DeleteOutlineIcon /></IconButton>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>

            <Stack direction="row" spacing={1.5}>
              <Button variant="outlined" startIcon={<AddIcon />} onClick={() => setRules((current) => [...current, newRule(current.length + 1)])}>Add Rule</Button>
              <Button variant="contained" startIcon={<SaveIcon />} disabled={saving} onClick={() => void savePolicy()}>{saving ? "Saving..." : "Save Policy"}</Button>
            </Stack>
          </Stack>
        </Paper>

        <Paper variant="outlined" sx={{ p: 3, borderRadius: 3 }}>
          <Typography variant="h6" fontWeight={700} sx={{ mb: 2 }}>Configured Policies</Typography>
          <Stack spacing={2}>
            {policies.length === 0 && <Typography color="text.secondary">No correlation policies configured yet.</Typography>}
            {policies.map((policy) => {
              const accountSource = integrations.find((item) => item.id === policy.accountIntegrationId)?.name ?? policy.accountIntegrationId;
              const identitySource = integrations.find((item) => item.id === policy.authoritativeIntegrationId)?.name ?? policy.authoritativeIntegrationId;
              return (
                <Paper key={policy.id} variant="outlined" sx={{ p: 2.5, borderRadius: 2 }}>
                  <Stack direction="row" justifyContent="space-between" alignItems="flex-start" spacing={2}>
                    <Box>
                      <Typography fontWeight={700}>{policy.name}</Typography>
                      <Typography variant="body2" color="text.secondary">{accountSource} → {identitySource}</Typography>
                      <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap" sx={{ mt: 1.5 }}>
                        {policy.rules.map((rule) => (
                          <Chip key={rule.id ?? rule.priority} size="small" label={`${rule.priority}. ${rule.accountAttribute} → ${rule.identityAttribute} (${rule.matchType})`} />
                        ))}
                      </Stack>
                    </Box>
                    <IconButton
                      color="error"
                      onClick={() => void deleteCorrelationPolicy(policy.id).then(() => setPolicies((current) => current.filter((item) => item.id !== policy.id))).catch((deleteError) => setError(deleteError instanceof Error ? deleteError.message : "Unable to delete policy."))}
                    >
                      <DeleteOutlineIcon />
                    </IconButton>
                  </Stack>
                </Paper>
              );
            })}
          </Stack>
        </Paper>
      </Stack>
    </PageContainer>
  );
};

export default CorrelationPolicies;
