import { useEffect, useMemo, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Checkbox,
  CircularProgress,
  FormControl,
  FormControlLabel,
  IconButton,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  Stack,
  Step,
  StepLabel,
  Stepper,
  Switch,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from "@mui/material";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import AddIcon from "@mui/icons-material/Add";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";
import UploadFileIcon from "@mui/icons-material/UploadFile";
import SaveIcon from "@mui/icons-material/Save";
import CableIcon from "@mui/icons-material/Cable";
import KeyIcon from "@mui/icons-material/Key";
import { useNavigate, useParams } from "react-router-dom";

import PageContainer from "../../components/common/PageContainer";
import DynamicConnectorForm from "../../components/integrations/DynamicConnectorForm";
import {
  createIntegration,
  detectIntegrationSchema,
  getConnectorTypes,
  getIntegration,
  testIntegration,
  testIntegrationAuthentication,
  updateIntegration,
  type ConnectorField,
  type ConnectorType,
  type IntegrationTestResult,
  type SourcePurpose,
} from "../../services/integrationService";
import {
  getIntegrationApplications,
  saveIntegrationApplications,
  type ApplicationInput,
  type MatchType,
  type NormalizationType,
  type SchemaAttributeInput,
} from "../../services/applicationSchemaService";
import {
  createCorrelationPolicy,
  deleteCorrelationPolicy,
  getCorrelationIntegrations,
  getCorrelationPolicies,
  getSourceApplications,
  updateCorrelationPolicy,
  type CorrelationIntegration,
  type CorrelationMatchType,
  type CorrelationPolicy,
  type CorrelationRule,
} from "../../services/correlationPolicyService";

const AUTH_FIELDS = [
  "username",
  "password",
  "apiToken",
  "apiTokenHeader",
  "bearerToken",
  "oauthGrantType",
  "tokenUrl",
  "clientId",
  "clientSecret",
  "oauthUsername",
  "oauthPassword",
  "refreshToken",
  "oauthAssertion",
  "oauthScope",
  "oauthAdvanced",
  "oauthHeadersJson",
  "oauthParametersJson",
  "customAuthHeader",
  "customAuthValue",
];

const emptyAttribute = (position: number): SchemaAttributeInput => ({
  name: "",
  displayName: "",
  dataType: "string",
  required: false,
  multiValued: false,
  position,
  useForMatching: false,
  matchType: "NONE",
  matchWeight: 0,
  normalizationType: "NONE",
});

const emptyApplication = (): ApplicationInput => ({
  name: "",
  displayName: "",
  objectType: "account",
  enabled: true,
  schemaName: "",
  attributes: [],
});

const newRule = (priority: number): CorrelationRule => ({
  priority,
  accountAttribute: "",
  identityAttribute: "",
  matchType: "EXACT",
  enabled: true,
});

const SourceWizard = () => {
  const navigate = useNavigate();
  const { integrationId } = useParams<{ integrationId: string }>();
  const editing = Boolean(integrationId);

  const [activeStep, setActiveStep] = useState(0);
  const [connectorTypes, setConnectorTypes] = useState<ConnectorType[]>([]);
  const [connectorType, setConnectorType] = useState("");
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [enabled, setEnabled] = useState(true);
  const [sourcePurpose, setSourcePurpose] = useState<SourcePurpose>("ACCOUNT");
  const [configuration, setConfiguration] = useState<Record<string, unknown>>({});
  const [applications, setApplications] = useState<ApplicationInput[]>([emptyApplication()]);
  const [selectedApplicationIndex, setSelectedApplicationIndex] = useState(0);

  const [connectionId, setConnectionId] = useState<number | null>(integrationId ? Number(integrationId) : null);
  const [connectionDirty, setConnectionDirty] = useState(!editing);
  const [connectionMessage, setConnectionMessage] = useState("");
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [savingConnection, setSavingConnection] = useState(false);
  const [testingAuthentication, setTestingAuthentication] = useState(false);
  const [testingConnection, setTestingConnection] = useState(false);
  const [authResult, setAuthResult] = useState<IntegrationTestResult | null>(null);
  const [testResult, setTestResult] = useState<IntegrationTestResult | null>(null);
  const [detectingSchema, setDetectingSchema] = useState(false);
  const [schemaDetectionMessage, setSchemaDetectionMessage] = useState("");
  const [error, setError] = useState("");

  const [allIntegrations, setAllIntegrations] = useState<CorrelationIntegration[]>([]);
  const [existingPolicy, setExistingPolicy] = useState<CorrelationPolicy | null>(null);
  const [authoritativeIntegrationId, setAuthoritativeIntegrationId] = useState<number | "">("");
  const [identityAttributes, setIdentityAttributes] = useState<string[]>([]);
  const [rules, setRules] = useState<CorrelationRule[]>([newRule(1)]);

  const steps = useMemo(
    () => sourcePurpose === "AUTHORITATIVE"
      ? ["Connection", "Applications", "Schema", "Review & Save"]
      : ["Connection", "Applications", "Schema", "Account Correlation", "Review & Save"],
    [sourcePurpose],
  );

  const selectedConnector = useMemo(
    () => connectorTypes.find((item) => item.type === connectorType) ?? null,
    [connectorTypes, connectorType],
  );
  const selectedApplication = applications[selectedApplicationIndex] ?? null;
  const isWebService = connectorType === "WEB_SERVICE";

  const authoritativeSources = useMemo(
    () => allIntegrations.filter((item) => item.sourcePurpose === "AUTHORITATIVE" && item.id !== connectionId),
    [allIntegrations, connectionId],
  );

  const accountAttributes = useMemo(
    () => Array.from(new Set(applications.flatMap((application) => application.attributes.map((attribute) => attribute.name).filter(Boolean)))).sort((a, b) => a.localeCompare(b)),
    [applications],
  );

  const loadIdentityAttributes = async (sourceId: number) => {
    const sourceApplications = await getSourceApplications(sourceId);
    const attributes = Array.from(new Set(
      sourceApplications.flatMap((application) => application.schema?.attributes.map((attribute) => attribute.name) ?? []),
    )).sort((a, b) => a.localeCompare(b));
    setIdentityAttributes(attributes);
  };

  useEffect(() => {
    const loadPage = async () => {
      try {
        setLoading(true);
        setError("");
        const [types, integrations, policies] = await Promise.all([
          getConnectorTypes(),
          getCorrelationIntegrations(),
          getCorrelationPolicies(),
        ]);
        setConnectorTypes(types);
        setAllIntegrations(integrations);

        if (editing && integrationId) {
          const id = Number(integrationId);
          const integration = await getIntegration(id);
          setName(integration.name);
          setDescription(integration.description ?? "");
          setConnectorType(integration.connectorType);
          setSourcePurpose(integration.sourcePurpose ?? "ACCOUNT");
          setConfiguration(integration.configuration);
          setEnabled(integration.enabled);
          setConnectionId(integration.id);
          setConnectionDirty(false);
          setConnectionMessage("Connection configuration is saved.");

          const existingApplications = await getIntegrationApplications(id);
          if (existingApplications.length > 0) {
            setApplications(existingApplications.map((item) => ({
              name: item.name,
              displayName: item.displayName,
              objectType: item.objectType,
              enabled: item.enabled,
              schemaName: item.schema?.name ?? "",
              attributes: item.schema?.attributes.map((attribute, index) => ({
                name: attribute.name,
                displayName: attribute.displayName,
                dataType: attribute.dataType,
                required: attribute.required,
                multiValued: attribute.multiValued,
                position: index,
                useForMatching: false,
                matchType: "NONE" as MatchType,
                matchWeight: 0,
                normalizationType: "NONE" as NormalizationType,
              })) ?? [],
            })));
          }

          const policy = policies.find((item) => item.accountIntegrationId === id) ?? null;
          if (policy) {
            setExistingPolicy(policy);
            setAuthoritativeIntegrationId(policy.authoritativeIntegrationId);
            setRules(policy.rules.length > 0 ? policy.rules : [newRule(1)]);
            await loadIdentityAttributes(policy.authoritativeIntegrationId);
          }
        } else if (types.length > 0) {
          const firstConnector = types[0];
          setConnectorType(firstConnector.type);
          const defaults = firstConnector.configurationSchema.fields.reduce<Record<string, unknown>>((result, field) => {
            if (field.default !== undefined) result[field.name] = field.default;
            return result;
          }, {});
          setConfiguration(defaults);
        }
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : "Unable to load integration wizard.");
      } finally {
        setLoading(false);
      }
    };
    void loadPage();
  }, [editing, integrationId]);

  const markConnectionDirty = () => {
    setConnectionDirty(true);
    setConnectionMessage("");
    setAuthResult(null);
    setTestResult(null);
  };

  const handlePurposeChange = (checked: boolean) => {
    setSourcePurpose(checked ? "AUTHORITATIVE" : "ACCOUNT");
    setActiveStep(0);
    markConnectionDirty();
  };

  const handleConnectorTypeChange = (nextConnectorType: string) => {
    setConnectorType(nextConnectorType);
    const connector = connectorTypes.find((item) => item.type === nextConnectorType);
    const defaults = connector?.configurationSchema.fields.reduce<Record<string, unknown>>((result, field) => {
      if (field.default !== undefined) result[field.name] = field.default;
      return result;
    }, {}) ?? {};
    setConfiguration(defaults);
    setFieldErrors({});
    setSchemaDetectionMessage("");
    markConnectionDirty();
  };

  const handleConnectorFieldChange = (fieldName: string, value: unknown) => {
    setConfiguration((current) => {
      const next = { ...current };
      if (fieldName === "authType") {
        AUTH_FIELDS.forEach((key) => delete next[key]);
        next.authType = value;
        if (value === "OAUTH2") {
          next.oauthGrantType = "CLIENT_CREDENTIALS";
          next.oauthAdvanced = false;
        }
        if (value === "API_TOKEN") next.apiTokenHeader = "Authorization";
      } else if (fieldName === "oauthGrantType") {
        ["oauthUsername", "oauthPassword", "refreshToken", "oauthAssertion"].forEach((key) => delete next[key]);
        next.oauthGrantType = value;
      } else {
        next[fieldName] = value;
      }
      return next;
    });
    markConnectionDirty();
  };

  const isFieldVisible = (field: ConnectorField): boolean => {
    if (!field.visibleWhen) return true;
    return Object.entries(field.visibleWhen).every(([dependency, allowedValues]) => {
      const dependencyField = selectedConnector?.configurationSchema.fields.find((item) => item.name === dependency);
      const currentValue = configuration[dependency] ?? dependencyField?.default ?? "";
      return allowedValues.map(String).includes(String(currentValue));
    });
  };

  const validateConnection = () => {
    const errors: Record<string, string> = {};
    if (!name.trim()) errors.name = "Integration name is required.";
    if (!connectorType) errors.connectorType = "Connector type is required.";
    selectedConnector?.configurationSchema.fields.forEach((field) => {
      if (!isFieldVisible(field)) return;
      const value = configuration[field.name] ?? field.default;
      if (field.required && (value === undefined || value === null || value === "")) errors[field.name] = `${field.label} is required.`;
    });
    setFieldErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const saveConnection = async (): Promise<number | null> => {
    if (!validateConnection()) return null;
    try {
      setSavingConnection(true);
      setError("");
      const payload = {
        name: name.trim(),
        sourcePurpose,
        description: description.trim() || null,
        configuration,
        enabled,
      };
      let savedId: number;
      if (connectionId) {
        const updated = await updateIntegration(connectionId, payload);
        savedId = updated.id;
      } else {
        const created = await createIntegration({ ...payload, connectorType });
        savedId = created.id;
        setConnectionId(savedId);
      }
      setConnectionDirty(false);
      setConnectionMessage("Source configuration saved successfully.");
      const integrations = await getCorrelationIntegrations();
      setAllIntegrations(integrations);
      return savedId;
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Unable to save source configuration.");
      return null;
    } finally {
      setSavingConnection(false);
    }
  };

  const handleTestAuthentication = async () => {
    if (!connectionId || connectionDirty) return setError("Save the latest source configuration before testing authentication.");
    try {
      setTestingAuthentication(true);
      setAuthResult(await testIntegrationAuthentication(connectionId));
    } catch (testError) {
      setError(testError instanceof Error ? testError.message : "Authentication test failed.");
    } finally {
      setTestingAuthentication(false);
    }
  };

  const handleTestConnection = async () => {
    if (!connectionId || connectionDirty) return setError("Save the latest source configuration before testing it.");
    try {
      setTestingConnection(true);
      setTestResult(await testIntegration(connectionId));
    } catch (testError) {
      setError(testError instanceof Error ? testError.message : "Connection test failed.");
    } finally {
      setTestingConnection(false);
    }
  };

  const updateApplication = (index: number, patch: Partial<ApplicationInput>) => {
    setApplications((current) => current.map((item, itemIndex) => itemIndex === index ? { ...item, ...patch } : item));
  };

  const updateAttribute = (applicationIndex: number, attributeIndex: number, patch: Partial<SchemaAttributeInput>) => {
    setApplications((current) => current.map((applicationItem, itemIndex) => itemIndex !== applicationIndex ? applicationItem : {
      ...applicationItem,
      attributes: applicationItem.attributes.map((attribute, index) => index === attributeIndex ? { ...attribute, ...patch } : attribute),
    }));
  };

  const detectSchemaFromSource = async () => {
    if (!selectedApplication || !connectionId || connectionDirty) return setError("Save the source connection before detecting schema.");
    try {
      setDetectingSchema(true);
      setError("");
      const result = await detectIntegrationSchema(connectorType, configuration);
      updateApplication(selectedApplicationIndex, {
        attributes: result.attributes.map((attribute, index) => ({ ...emptyAttribute(index), ...attribute, position: index })),
      });
      setSchemaDetectionMessage(`Detected ${result.attributes.length} attributes from ${result.filename}.`);
    } catch (detectError) {
      setError(detectError instanceof Error ? detectError.message : "Unable to detect source schema.");
    } finally {
      setDetectingSchema(false);
    }
  };

  const uploadSchema = async (file: File) => {
    try {
      const parsed = JSON.parse(await file.text()) as { attributes?: Array<Partial<SchemaAttributeInput> & { name?: string }> };
      if (!Array.isArray(parsed.attributes)) throw new Error("Schema JSON must contain an attributes array.");
      const mapped = parsed.attributes.map((attribute, index): SchemaAttributeInput => ({ ...emptyAttribute(index), ...attribute, name: String(attribute.name ?? "").trim(), position: index }));
      if (mapped.some((attribute) => !attribute.name)) throw new Error("Every uploaded schema attribute requires a name.");
      updateApplication(selectedApplicationIndex, { attributes: mapped });
      setSchemaDetectionMessage(`Loaded ${mapped.length} attributes from JSON schema.`);
    } catch (uploadError) {
      setError(uploadError instanceof Error ? uploadError.message : "Unable to read schema file.");
    }
  };

  const validateApplications = () => applications.length > 0 && applications.every((item) => item.name.trim());
  const validateSchemas = () => applications.every((item) => item.attributes.length > 0 && item.attributes.every((attribute) => attribute.name.trim()));
  const validateCorrelation = () => {
    if (sourcePurpose === "AUTHORITATIVE") return true;
    if (!authoritativeIntegrationId) {
      setError("Select an authoritative identity source for account correlation.");
      return false;
    }
    if (rules.length === 0 || rules.some((rule) => !rule.accountAttribute || !rule.identityAttribute)) {
      setError("Configure at least one complete account correlation rule.");
      return false;
    }
    return true;
  };

  const goNext = async () => {
    setError("");
    if (activeStep === 0) {
      if (!validateConnection()) return;
      if (!connectionId || connectionDirty) return setError("Save the source configuration before continuing.");
    }
    if (activeStep === 1 && !validateApplications()) return setError("Every application requires a name.");
    if (activeStep === 2) {
      if (!validateSchemas()) return setError("Every application requires a valid schema.");
      if (connectionId) {
        await saveIntegrationApplications(connectionId, applications.map((application) => ({
          ...application,
          name: application.name.trim(),
          schemaName: application.schemaName?.trim() || `${application.name.trim()} schema`,
        })));
      }
    }
    if (sourcePurpose === "ACCOUNT" && activeStep === 3 && !validateCorrelation()) return;
    setActiveStep((current) => Math.min(current + 1, steps.length - 1));
  };

  const savePolicy = async (accountIntegrationId: number) => {
    if (sourcePurpose === "AUTHORITATIVE") {
      if (existingPolicy) {
        await deleteCorrelationPolicy(existingPolicy.id);
        setExistingPolicy(null);
      }
      return;
    }
    if (!validateCorrelation()) throw new Error("Account correlation configuration is incomplete.");
    const payload = {
      name: `${name.trim()} account correlation`,
      authoritativeIntegrationId: Number(authoritativeIntegrationId),
      strategy: "FIRST_MATCH_WINS" as const,
      enabled: true,
      rules: rules.map((rule, index) => ({ ...rule, priority: index + 1, enabled: true })),
    };
    if (existingPolicy) {
      const updated = await updateCorrelationPolicy(existingPolicy.id, payload);
      setExistingPolicy(updated);
    } else {
      const created = await createCorrelationPolicy({ ...payload, accountIntegrationId });
      setExistingPolicy(created);
    }
  };

  const handleSave = async () => {
    if (!connectionId || connectionDirty) {
      setActiveStep(0);
      return setError("Save the source configuration before finishing setup.");
    }
    if (!validateApplications() || !validateSchemas()) return setError("Applications and schema must be complete.");
    try {
      setSaving(true);
      setError("");
      await saveIntegrationApplications(connectionId, applications.map((application) => ({
        ...application,
        name: application.name.trim(),
        schemaName: application.schemaName?.trim() || `${application.name.trim()} schema`,
      })));
      await savePolicy(connectionId);
      navigate("/integrations");
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Unable to finish source setup.");
    } finally {
      setSaving(false);
    }
  };

  const updateRule = (index: number, patch: Partial<CorrelationRule>) => setRules((current) => current.map((rule, ruleIndex) => ruleIndex === index ? { ...rule, ...patch } : rule));
  const removeRule = (index: number) => setRules((current) => current.filter((_, ruleIndex) => ruleIndex !== index).map((rule, ruleIndex) => ({ ...rule, priority: ruleIndex + 1 })));

  if (loading) return <PageContainer title="Integration"><Box sx={{ minHeight: 400, display: "flex", alignItems: "center", justifyContent: "center" }}><CircularProgress /></Box></PageContainer>;

  const busy = savingConnection || testingAuthentication || testingConnection;
  const reviewStep = steps.length - 1;

  return (
    <PageContainer title={editing ? "Edit Integration" : "Add Integration"}>
      <Stack spacing={3}>
        <Box sx={{ display: "flex", justifyContent: "space-between", gap: 2 }}>
          <Box>
            <Typography variant="h5" fontWeight={700}>{editing ? "Edit Source" : "Create Source"}</Typography>
            <Typography color="text.secondary">Configure the connection, schema, and account correlation as one source-onboarding workflow.</Typography>
          </Box>
          <Button variant="outlined" startIcon={<ArrowBackIcon />} onClick={() => navigate("/integrations")}>Back</Button>
        </Box>

        <Paper variant="outlined" sx={{ p: 3, borderRadius: 3 }}>
          <Stepper activeStep={activeStep} alternativeLabel>{steps.map((label) => <Step key={label}><StepLabel>{label}</StepLabel></Step>)}</Stepper>
        </Paper>
        {error && <Alert severity="error">{error}</Alert>}

        <Paper variant="outlined" sx={{ p: { xs: 2, md: 4 }, borderRadius: 3 }}>
          {activeStep === 0 && (
            <Stack spacing={3}>
              <TextField label="Integration Name" value={name} required error={Boolean(fieldErrors.name)} helperText={fieldErrors.name} onChange={(event) => { setName(event.target.value); markConnectionDirty(); }} />
              <TextField multiline minRows={2} label="Description" value={description} onChange={(event) => { setDescription(event.target.value); markConnectionDirty(); }} />
              <FormControl disabled={Boolean(connectionId)} error={Boolean(fieldErrors.connectorType)}>
                <InputLabel>Connector Type</InputLabel>
                <Select label="Connector Type" value={connectorType} onChange={(event) => handleConnectorTypeChange(event.target.value)}>
                  {connectorTypes.map((connector) => <MenuItem key={connector.type} value={connector.type}>{connector.displayName}</MenuItem>)}
                </Select>
              </FormControl>

              <Paper variant="outlined" sx={{ p: 2.5, borderRadius: 2 }}>
                <FormControlLabel
                  control={<Checkbox checked={sourcePurpose === "AUTHORITATIVE"} onChange={(event) => handlePurposeChange(event.target.checked)} />}
                  label={<Box><Typography fontWeight={700}>Authoritative Source</Typography><Typography variant="body2" color="text.secondary">Use this source as the authoritative identity population, such as Workday, SuccessFactors, or an HR feed.</Typography></Box>}
                />
              </Paper>

              {selectedConnector && <><Alert severity="info">{selectedConnector.description}</Alert><DynamicConnectorForm connector={selectedConnector} values={configuration} errors={fieldErrors} onChange={handleConnectorFieldChange} /></>}
              <FormControlLabel control={<Switch checked={enabled} onChange={(event) => { setEnabled(event.target.checked); markConnectionDirty(); }} />} label="Enable integration" />
              {connectionMessage && <Alert severity="success">{connectionMessage}</Alert>}
              {connectionDirty && connectionId && <Alert severity="warning">Source settings changed. Save them before continuing.</Alert>}
              {authResult && <Alert severity={authResult.success ? "success" : "error"}>{authResult.message}</Alert>}
              {testResult && <Alert severity={testResult.success ? "success" : "error"}>{testResult.message}</Alert>}
              <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5}>
                <Button variant="contained" startIcon={savingConnection ? <CircularProgress size={17} /> : <SaveIcon />} disabled={busy} onClick={() => void saveConnection()}>{savingConnection ? "Saving..." : "Save Source"}</Button>
                {isWebService && <Button variant="outlined" startIcon={<KeyIcon />} disabled={!connectionId || connectionDirty || busy} onClick={() => void handleTestAuthentication()}>Test Authentication</Button>}
                <Button variant="outlined" startIcon={<CableIcon />} disabled={!connectionId || connectionDirty || busy} onClick={() => void handleTestConnection()}>Test Connection</Button>
              </Stack>
            </Stack>
          )}

          {activeStep === 1 && (
            <Stack spacing={2.5}>
              <Box><Typography variant="h6" fontWeight={700}>Applications</Typography><Typography variant="body2" color="text.secondary">Define the object populations exposed by this source.</Typography></Box>
              {applications.map((application, index) => <Paper key={index} variant="outlined" sx={{ p: 2.5 }}><Stack direction={{ xs: "column", md: "row" }} spacing={2}><TextField fullWidth label="Application Name" value={application.name} onChange={(event) => updateApplication(index, { name: event.target.value })} /><TextField fullWidth label="Display Name" value={application.displayName ?? ""} onChange={(event) => updateApplication(index, { displayName: event.target.value })} /><TextField label="Object Type" value={application.objectType ?? (sourcePurpose === "AUTHORITATIVE" ? "identity" : "account")} onChange={(event) => updateApplication(index, { objectType: event.target.value })} /><IconButton color="error" disabled={applications.length === 1} onClick={() => setApplications((current) => current.filter((_, itemIndex) => itemIndex !== index))}><DeleteOutlineIcon /></IconButton></Stack></Paper>)}
              <Button variant="outlined" startIcon={<AddIcon />} sx={{ alignSelf: "flex-start" }} onClick={() => setApplications((current) => [...current, emptyApplication()])}>Add Application</Button>
            </Stack>
          )}

          {activeStep === 2 && (
            <Stack spacing={2.5}>
              <Box><Typography variant="h6" fontWeight={700}>Schema</Typography><Typography variant="body2" color="text.secondary">Detect or define the attributes available for ingestion and correlation.</Typography></Box>
              <FormControl sx={{ maxWidth: 360 }}><InputLabel>Application</InputLabel><Select label="Application" value={selectedApplicationIndex} onChange={(event) => setSelectedApplicationIndex(Number(event.target.value))}>{applications.map((item, index) => <MenuItem key={index} value={index}>{item.name || `Application ${index + 1}`}</MenuItem>)}</Select></FormControl>
              {schemaDetectionMessage && <Alert severity="success">{schemaDetectionMessage}</Alert>}
              <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5}>
                <Button variant="outlined" disabled={detectingSchema} onClick={() => void detectSchemaFromSource()}>{detectingSchema ? "Detecting..." : "Detect Schema"}</Button>
                <Button component="label" variant="outlined" startIcon={<UploadFileIcon />}>Upload JSON Schema<input hidden type="file" accept="application/json,.json" onChange={(event) => { const file = event.target.files?.[0]; if (file) void uploadSchema(file); }} /></Button>
                <Button variant="contained" startIcon={<AddIcon />} onClick={() => selectedApplication && updateApplication(selectedApplicationIndex, { attributes: [...selectedApplication.attributes, emptyAttribute(selectedApplication.attributes.length)] })}>Add Attribute</Button>
              </Stack>
              {selectedApplication && <TableContainer component={Paper} variant="outlined"><Table size="small"><TableHead><TableRow><TableCell>Attribute</TableCell><TableCell>Display Name</TableCell><TableCell>Type</TableCell><TableCell>Required</TableCell><TableCell /></TableRow></TableHead><TableBody>{selectedApplication.attributes.map((attribute, index) => <TableRow key={index}><TableCell><TextField size="small" value={attribute.name} onChange={(event) => updateAttribute(selectedApplicationIndex, index, { name: event.target.value })} /></TableCell><TableCell><TextField size="small" value={attribute.displayName ?? ""} onChange={(event) => updateAttribute(selectedApplicationIndex, index, { displayName: event.target.value })} /></TableCell><TableCell><Select size="small" value={attribute.dataType} onChange={(event) => updateAttribute(selectedApplicationIndex, index, { dataType: event.target.value })}>{["string", "number", "boolean", "date", "datetime", "array", "object"].map((type) => <MenuItem key={type} value={type}>{type}</MenuItem>)}</Select></TableCell><TableCell><Checkbox checked={attribute.required} onChange={(event) => updateAttribute(selectedApplicationIndex, index, { required: event.target.checked })} /></TableCell><TableCell><IconButton color="error" onClick={() => updateApplication(selectedApplicationIndex, { attributes: selectedApplication.attributes.filter((_, itemIndex) => itemIndex !== index) })}><DeleteOutlineIcon /></IconButton></TableCell></TableRow>)}</TableBody></Table></TableContainer>}
            </Stack>
          )}

          {sourcePurpose === "ACCOUNT" && activeStep === 3 && (
            <Stack spacing={3}>
              <Box><Typography variant="h6" fontWeight={700}>Account Correlation</Typography><Typography variant="body2" color="text.secondary">Choose the authoritative source and define how this source's accounts correlate to identities.</Typography></Box>
              {authoritativeSources.length === 0 && <Alert severity="warning">No authoritative sources are configured yet. Create an HR/Workday-style source and mark it as Authoritative Source first.</Alert>}
              <FormControl fullWidth><InputLabel>Authoritative Identity Source</InputLabel><Select label="Authoritative Identity Source" value={authoritativeIntegrationId} onChange={(event) => { const id = Number(event.target.value); setAuthoritativeIntegrationId(id); void loadIdentityAttributes(id); }}>{authoritativeSources.map((source) => <MenuItem key={source.id} value={source.id}>{source.name}</MenuItem>)}</Select></FormControl>
              <Alert severity="info">Rules are evaluated in priority order. The first rule producing one unique identity wins; multiple matches are flagged as ambiguous rather than linked automatically.</Alert>
              <TableContainer component={Paper} variant="outlined"><Table size="small"><TableHead><TableRow><TableCell>Priority</TableCell><TableCell>Account Attribute</TableCell><TableCell>Identity Attribute</TableCell><TableCell>Match Type</TableCell><TableCell /></TableRow></TableHead><TableBody>{rules.map((rule, index) => <TableRow key={index}><TableCell>{index + 1}</TableCell><TableCell><Select size="small" fullWidth value={rule.accountAttribute} onChange={(event) => updateRule(index, { accountAttribute: event.target.value })}>{accountAttributes.map((attribute) => <MenuItem key={attribute} value={attribute}>{attribute}</MenuItem>)}</Select></TableCell><TableCell><Select size="small" fullWidth value={rule.identityAttribute} onChange={(event) => updateRule(index, { identityAttribute: event.target.value })}>{identityAttributes.map((attribute) => <MenuItem key={attribute} value={attribute}>{attribute}</MenuItem>)}</Select></TableCell><TableCell><Select size="small" value={rule.matchType} onChange={(event) => updateRule(index, { matchType: event.target.value as CorrelationMatchType })}><MenuItem value="EXACT">Exact</MenuItem><MenuItem value="CASE_INSENSITIVE">Case-insensitive</MenuItem><MenuItem value="NORMALIZED">Normalized</MenuItem></Select></TableCell><TableCell><IconButton color="error" disabled={rules.length === 1} onClick={() => removeRule(index)}><DeleteOutlineIcon /></IconButton></TableCell></TableRow>)}</TableBody></Table></TableContainer>
              <Button variant="outlined" startIcon={<AddIcon />} sx={{ alignSelf: "flex-start" }} onClick={() => setRules((current) => [...current, newRule(current.length + 1)])}>Add Correlation Rule</Button>
            </Stack>
          )}

          {activeStep === reviewStep && (
            <Stack spacing={3}>
              <Box><Typography variant="h6" fontWeight={700}>Review Configuration</Typography><Typography variant="body2" color="text.secondary">Confirm the source purpose, schema, and correlation behavior before finishing.</Typography></Box>
              <Paper variant="outlined" sx={{ p: 2.5 }}><Typography fontWeight={700}>{name}</Typography><Typography variant="body2" color="text.secondary">{selectedConnector?.displayName ?? connectorType} · {sourcePurpose === "AUTHORITATIVE" ? "Authoritative Source" : "Account Source"} · {enabled ? "Enabled" : "Disabled"}</Typography></Paper>
              {applications.map((application, index) => <Paper key={index} variant="outlined" sx={{ p: 2.5 }}><Typography fontWeight={700}>{application.name}</Typography><Typography variant="body2" color="text.secondary">{application.attributes.length} schema attributes</Typography></Paper>)}
              {sourcePurpose === "ACCOUNT" && <Paper variant="outlined" sx={{ p: 2.5 }}><Typography fontWeight={700}>Account Correlation</Typography><Typography variant="body2" color="text.secondary">Authoritative source: {authoritativeSources.find((item) => item.id === Number(authoritativeIntegrationId))?.name ?? "Not selected"}</Typography><Stack spacing={0.5} sx={{ mt: 1 }}>{rules.map((rule, index) => <Typography key={index} variant="body2">{index + 1}. {rule.accountAttribute} → {rule.identityAttribute} ({rule.matchType})</Typography>)}</Stack></Paper>}
            </Stack>
          )}

          <Box sx={{ display: "flex", justifyContent: "space-between", mt: 4, pt: 3, borderTop: 1, borderColor: "divider" }}>
            <Button disabled={activeStep === 0 || saving || busy} onClick={() => setActiveStep((current) => Math.max(0, current - 1))}>Back</Button>
            <Stack direction="row" spacing={1.5}><Button variant="outlined" onClick={() => navigate("/integrations")}>Cancel</Button>{activeStep < reviewStep ? <Button variant="contained" disabled={busy || detectingSchema} onClick={() => void goNext()}>Next</Button> : <Button variant="contained" startIcon={<SaveIcon />} disabled={saving} onClick={() => void handleSave()}>{saving ? "Saving..." : editing ? "Update Source" : "Finish Source"}</Button>}</Stack>
          </Box>
        </Paper>
      </Stack>
    </PageContainer>
  );
};

export default SourceWizard;
