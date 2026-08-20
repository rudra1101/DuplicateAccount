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
import { useNavigate, useParams } from "react-router-dom";

import PageContainer from "../../components/common/PageContainer";
import DynamicConnectorForm from "../../components/integrations/DynamicConnectorForm";
import {
  createIntegration,
  detectIntegrationSchema,
  getConnectorTypes,
  getIntegration,
  updateIntegration,
  type ConnectorType,
} from "../../services/integrationService";
import {
  getIntegrationApplications,
  saveIntegrationApplications,
  type ApplicationInput,
  type MatchType,
  type NormalizationType,
  type SchemaAttributeInput,
} from "../../services/applicationSchemaService";

const steps = ["Connection", "Applications", "Schema", "Review & Save"];

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

const AddIntegration = () => {
  const navigate = useNavigate();
  const { integrationId } = useParams<{ integrationId: string }>();
  const editing = Boolean(integrationId);

  const [activeStep, setActiveStep] = useState(0);
  const [connectorTypes, setConnectorTypes] = useState<ConnectorType[]>([]);
  const [connectorType, setConnectorType] = useState("");
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [enabled, setEnabled] = useState(true);
  const [configuration, setConfiguration] = useState<Record<string, unknown>>({});
  const [applications, setApplications] = useState<ApplicationInput[]>([emptyApplication()]);
  const [selectedApplicationIndex, setSelectedApplicationIndex] = useState(0);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [detectingSchema, setDetectingSchema] = useState(false);
  const [schemaDetectionMessage, setSchemaDetectionMessage] = useState("");
  const [error, setError] = useState("");

  const selectedConnector = useMemo(
    () => connectorTypes.find((item) => item.type === connectorType) ?? null,
    [connectorTypes, connectorType],
  );

  const selectedApplication = applications[selectedApplicationIndex] ?? null;

  useEffect(() => {
    const loadPage = async () => {
      try {
        setLoading(true);
        setError("");
        const types = await getConnectorTypes();
        setConnectorTypes(types);

        if (editing && integrationId) {
          const integration = await getIntegration(Number(integrationId));
          setName(integration.name);
          setDescription(integration.description ?? "");
          setConnectorType(integration.connectorType);
          setConfiguration(integration.configuration);
          setEnabled(integration.enabled);

          const existingApplications = await getIntegrationApplications(Number(integrationId));
          if (existingApplications.length > 0) {
            setApplications(
              existingApplications.map((item) => ({
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
                  // These fields remain in the transport contract for backend
                  // compatibility, but are not exposed or controlled by the UI.
                  useForMatching: false,
                  matchType: "NONE" as MatchType,
                  matchWeight: 0,
                  normalizationType: "NONE" as NormalizationType,
                })) ?? [],
              })),
            );
          }
        } else if (types.length > 0) {
          const firstConnector = types[0];
          setConnectorType(firstConnector.type);
          const defaults = firstConnector.configurationSchema.fields.reduce<Record<string, unknown>>(
            (result, field) => {
              if (field.default !== undefined) result[field.name] = field.default;
              return result;
            },
            {},
          );
          setConfiguration(defaults);
        }
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : "Unable to load integration form.");
      } finally {
        setLoading(false);
      }
    };
    void loadPage();
  }, [editing, integrationId]);

  const handleConnectorTypeChange = (nextConnectorType: string) => {
    setConnectorType(nextConnectorType);
    const connector = connectorTypes.find((item) => item.type === nextConnectorType);
    const defaults = connector?.configurationSchema.fields.reduce<Record<string, unknown>>(
      (result, field) => {
        if (field.default !== undefined) result[field.name] = field.default;
        return result;
      },
      {},
    ) ?? {};
    setConfiguration(defaults);
    setFieldErrors({});
    setSchemaDetectionMessage("");
  };

  const updateApplication = (index: number, patch: Partial<ApplicationInput>) => {
    setApplications((current) => current.map((item, itemIndex) => (
      itemIndex === index ? { ...item, ...patch } : item
    )));
  };

  const updateAttribute = (
    applicationIndex: number,
    attributeIndex: number,
    patch: Partial<SchemaAttributeInput>,
  ) => {
    setApplications((current) => current.map((applicationItem, itemIndex) => {
      if (itemIndex !== applicationIndex) return applicationItem;
      return {
        ...applicationItem,
        attributes: applicationItem.attributes.map((attribute, index) => (
          index === attributeIndex ? { ...attribute, ...patch } : attribute
        )),
      };
    }));
  };

  const addAttribute = () => {
    if (!selectedApplication) return;
    updateApplication(selectedApplicationIndex, {
      attributes: [
        ...selectedApplication.attributes,
        emptyAttribute(selectedApplication.attributes.length),
      ],
    });
  };

  const removeAttribute = (attributeIndex: number) => {
    if (!selectedApplication) return;
    updateApplication(selectedApplicationIndex, {
      attributes: selectedApplication.attributes
        .filter((_, index) => index !== attributeIndex)
        .map((attribute, index) => ({ ...attribute, position: index })),
    });
  };

  const uploadSchema = async (file: File) => {
    try {
      const text = await file.text();
      const parsed = JSON.parse(text) as {
        attributes?: Array<Partial<SchemaAttributeInput> & { name?: string }>;
      };
      if (!Array.isArray(parsed.attributes)) {
        throw new Error("Schema JSON must contain an attributes array.");
      }

      const mapped = parsed.attributes.map((attribute, index): SchemaAttributeInput => ({
        ...emptyAttribute(index),
        ...attribute,
        name: String(attribute.name ?? "").trim(),
        position: index,
        useForMatching: false,
        matchType: "NONE",
        matchWeight: 0,
        normalizationType: "NONE",
      }));

      if (mapped.some((attribute) => !attribute.name)) {
        throw new Error("Every uploaded schema attribute requires a name.");
      }

      updateApplication(selectedApplicationIndex, { attributes: mapped });
      setSchemaDetectionMessage(`Loaded ${mapped.length} attributes from JSON schema.`);
      setError("");
    } catch (uploadError) {
      setError(uploadError instanceof Error ? uploadError.message : "Unable to read schema file.");
    }
  };

  const validateConnection = (): boolean => {
    const errors: Record<string, string> = {};
    if (!name.trim()) errors.name = "Integration name is required.";
    if (!connectorType) errors.connectorType = "Connector type is required.";

    selectedConnector?.configurationSchema.fields.forEach((field) => {
      const value = configuration[field.name];
      if (field.required && (value === undefined || value === null || value === "")) {
        errors[field.name] = `${field.label} is required.`;
      }
    });

    setFieldErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const detectSchemaFromCsv = async () => {
    if (!selectedApplication) return;
    if (!validateConnection()) {
      setError("Complete the connector configuration before detecting the CSV schema.");
      return;
    }

    try {
      setDetectingSchema(true);
      setError("");
      setSchemaDetectionMessage("");

      const result = await detectIntegrationSchema(connectorType, configuration);
      const attributes: SchemaAttributeInput[] = result.attributes.map((attribute, index) => ({
        ...emptyAttribute(index),
        ...attribute,
        position: index,
        useForMatching: false,
        matchType: "NONE",
        matchWeight: 0,
        normalizationType: "NONE",
      }));

      updateApplication(selectedApplicationIndex, { attributes });
      setSchemaDetectionMessage(
        `Detected ${attributes.length} attributes from ${result.filename} using ${result.sampledRows} sample row${result.sampledRows === 1 ? "" : "s"}.`,
      );
    } catch (detectError) {
      setError(
        detectError instanceof Error
          ? detectError.message
          : "Unable to detect schema from the configured CSV source.",
      );
    } finally {
      setDetectingSchema(false);
    }
  };

  const validateApplications = (): boolean => {
    if (applications.length === 0) {
      setError("At least one application is required.");
      return false;
    }

    const names = applications.map((item) => item.name.trim()).filter(Boolean);
    if (names.length !== applications.length) {
      setError("Every application requires a name.");
      return false;
    }

    if (new Set(names.map((item) => item.toLowerCase())).size !== names.length) {
      setError("Application names must be unique within the integration.");
      return false;
    }

    return true;
  };

  const validateSchemas = (): boolean => {
    for (const applicationItem of applications) {
      if (applicationItem.attributes.length === 0) {
        setError(`${applicationItem.name} requires at least one schema attribute.`);
        return false;
      }

      const names = applicationItem.attributes.map((item) => item.name.trim()).filter(Boolean);
      if (names.length !== applicationItem.attributes.length) {
        setError(`${applicationItem.name} contains an unnamed schema attribute.`);
        return false;
      }

      if (new Set(names.map((item) => item.toLowerCase())).size !== names.length) {
        setError(`${applicationItem.name} contains duplicate schema attribute names.`);
        return false;
      }
    }

    return true;
  };

  const goNext = () => {
    setError("");

    if (activeStep === 0 && !validateConnection()) return;
    if (activeStep === 1 && !validateApplications()) return;
    if (activeStep === 2 && !validateSchemas()) return;

    setActiveStep((current) => Math.min(current + 1, steps.length - 1));
  };

  const handleSave = async () => {
    if (!validateConnection() || !validateApplications() || !validateSchemas()) return;

    try {
      setSaving(true);
      setError("");
      let savedIntegrationId: number;

      if (editing && integrationId) {
        const updated = await updateIntegration(Number(integrationId), {
          name: name.trim(),
          description: description.trim() || null,
          configuration,
          enabled,
        });
        savedIntegrationId = updated.id;
      } else {
        const created = await createIntegration({
          name: name.trim(),
          connectorType,
          description: description.trim() || null,
          configuration,
          enabled,
        });
        savedIntegrationId = created.id;
      }

      await saveIntegrationApplications(
        savedIntegrationId,
        applications.map((applicationItem) => ({
          ...applicationItem,
          name: applicationItem.name.trim(),
          displayName: applicationItem.displayName?.trim() || null,
          schemaName: applicationItem.schemaName?.trim() || `${applicationItem.name.trim()} schema`,
          attributes: applicationItem.attributes.map((attribute, index) => ({
            ...attribute,
            name: attribute.name.trim(),
            displayName: attribute.displayName?.trim() || null,
            position: index,
            // Backend intentionally ignores these client-side matching fields
            // and calculates its own internal strategy.
            useForMatching: false,
            matchType: "NONE",
            matchWeight: 0,
            normalizationType: "NONE",
          })),
        })),
      );

      navigate("/integrations");
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Unable to save integration.");
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <PageContainer title="Integration">
        <Box sx={{ minHeight: 400, display: "flex", justifyContent: "center", alignItems: "center" }}>
          <CircularProgress />
        </Box>
      </PageContainer>
    );
  }

  return (
    <PageContainer title={editing ? "Edit Integration" : "Add Integration"}>
      <Box sx={{ display: "flex", justifyContent: "space-between", gap: 2, flexWrap: "wrap", mb: 3 }}>
        <Box>
          <Typography variant="h5" fontWeight={700}>
            {editing ? "Edit Integration" : "Create Integration"}
          </Typography>
          <Typography color="text.secondary" sx={{ mt: 0.5 }}>
            Configure the source and application schema. Duplicate scoring is handled automatically by the backend.
          </Typography>
        </Box>
        <Button variant="outlined" startIcon={<ArrowBackIcon />} onClick={() => navigate("/integrations")}>
          Back
        </Button>
      </Box>

      <Paper variant="outlined" sx={{ p: { xs: 2, md: 3 }, borderRadius: 3, mb: 3 }}>
        <Stepper activeStep={activeStep} alternativeLabel>
          {steps.map((label) => (
            <Step key={label}><StepLabel>{label}</StepLabel></Step>
          ))}
        </Stepper>
      </Paper>

      {error && <Alert severity="error" sx={{ mb: 3 }}>{error}</Alert>}

      <Paper variant="outlined" sx={{ p: { xs: 2, md: 4 }, borderRadius: 3 }}>
        {activeStep === 0 && (
          <Stack spacing={3}>
            <TextField label="Integration Name" value={name} required error={Boolean(fieldErrors.name)} helperText={fieldErrors.name} onChange={(event) => setName(event.target.value)} />
            <TextField multiline minRows={2} label="Description" value={description} onChange={(event) => setDescription(event.target.value)} />
            <FormControl disabled={editing} error={Boolean(fieldErrors.connectorType)}>
              <InputLabel>Connector Type</InputLabel>
              <Select label="Connector Type" value={connectorType} onChange={(event) => handleConnectorTypeChange(event.target.value)}>
                {connectorTypes.map((connector) => (
                  <MenuItem key={connector.type} value={connector.type}>{connector.displayName}</MenuItem>
                ))}
              </Select>
            </FormControl>
            {selectedConnector && (
              <>
                <Alert severity="info">{selectedConnector.description}</Alert>
                <DynamicConnectorForm
                  connector={selectedConnector}
                  values={configuration}
                  errors={fieldErrors}
                  onChange={(fieldName, value) => setConfiguration((current) => ({ ...current, [fieldName]: value }))}
                />
              </>
            )}
            <FormControlLabel control={<Switch checked={enabled} onChange={(event) => setEnabled(event.target.checked)} />} label="Enable integration" />
          </Stack>
        )}

        {activeStep === 1 && (
          <Stack spacing={2.5}>
            <Box>
              <Typography variant="h6" fontWeight={700}>Applications</Typography>
              <Typography color="text.secondary" variant="body2">
                Define each account population independently. Accounts are compared only within the same application.
              </Typography>
            </Box>
            {applications.map((applicationItem, index) => (
              <Paper key={index} variant="outlined" sx={{ p: 2.5, borderRadius: 2 }}>
                <Stack direction={{ xs: "column", md: "row" }} spacing={2} alignItems={{ md: "center" }}>
                  <TextField label="Application Name" value={applicationItem.name} required sx={{ flex: 1 }} onChange={(event) => updateApplication(index, { name: event.target.value })} placeholder="e.g. AD US" />
                  <TextField label="Display Name" value={applicationItem.displayName ?? ""} sx={{ flex: 1 }} onChange={(event) => updateApplication(index, { displayName: event.target.value })} />
                  <TextField label="Object Type" value={applicationItem.objectType ?? "account"} sx={{ width: 180 }} onChange={(event) => updateApplication(index, { objectType: event.target.value })} />
                  <FormControlLabel control={<Switch checked={applicationItem.enabled} onChange={(event) => updateApplication(index, { enabled: event.target.checked })} />} label="Enabled" />
                  <IconButton disabled={applications.length === 1} color="error" onClick={() => {
                    setApplications((current) => current.filter((_, itemIndex) => itemIndex !== index));
                    setSelectedApplicationIndex(0);
                  }}>
                    <DeleteOutlineIcon />
                  </IconButton>
                </Stack>
              </Paper>
            ))}
            <Button startIcon={<AddIcon />} variant="outlined" onClick={() => setApplications((current) => [...current, emptyApplication()])} sx={{ alignSelf: "flex-start" }}>
              Add Application
            </Button>
          </Stack>
        )}

        {activeStep === 2 && (
          <Stack spacing={2.5}>
            <Box>
              <Typography variant="h6" fontWeight={700}>Application Schema</Typography>
              <Typography color="text.secondary" variant="body2">
                Detect attributes from the configured CSV source, upload a JSON schema, or define attributes manually.
              </Typography>
            </Box>

            <FormControl sx={{ maxWidth: 360 }}>
              <InputLabel>Application</InputLabel>
              <Select label="Application" value={selectedApplicationIndex} onChange={(event) => {
                setSelectedApplicationIndex(Number(event.target.value));
                setSchemaDetectionMessage("");
              }}>
                {applications.map((item, index) => (
                  <MenuItem key={`${item.name}-${index}`} value={index}>{item.name || `Application ${index + 1}`}</MenuItem>
                ))}
              </Select>
            </FormControl>

            {schemaDetectionMessage && <Alert severity="success">{schemaDetectionMessage}</Alert>}

            {selectedApplication && (
              <>
                <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5} alignItems={{ sm: "center" }}>
                  <TextField label="Schema Name" value={selectedApplication.schemaName ?? ""} onChange={(event) => updateApplication(selectedApplicationIndex, { schemaName: event.target.value })} sx={{ minWidth: 260 }} />
                  <Button
                    variant="outlined"
                    disabled={detectingSchema}
                    onClick={() => void detectSchemaFromCsv()}
                  >
                    {detectingSchema ? "Detecting..." : "Detect CSV Schema"}
                  </Button>
                  <Button component="label" variant="outlined" startIcon={<UploadFileIcon />}>
                    Upload JSON Schema
                    <input hidden type="file" accept="application/json,.json" onChange={(event) => {
                      const file = event.target.files?.[0];
                      if (file) void uploadSchema(file);
                      event.target.value = "";
                    }} />
                  </Button>
                  <Button variant="contained" startIcon={<AddIcon />} onClick={addAttribute}>Add Attribute</Button>
                </Stack>

                <TableContainer variant="outlined" component={Paper}>
                  <Table size="small">
                    <TableHead>
                      <TableRow sx={{ backgroundColor: "#f8fafc" }}>
                        <TableCell>Attribute</TableCell>
                        <TableCell>Display Name</TableCell>
                        <TableCell>Type</TableCell>
                        <TableCell align="center">Required</TableCell>
                        <TableCell align="center">Multi-valued</TableCell>
                        <TableCell />
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {selectedApplication.attributes.length === 0 ? (
                        <TableRow>
                          <TableCell colSpan={6} align="center" sx={{ py: 5 }}>
                            <Typography color="text.secondary">No attributes yet. Detect the CSV schema, upload JSON, or add attributes manually.</Typography>
                          </TableCell>
                        </TableRow>
                      ) : selectedApplication.attributes.map((attribute, index) => (
                        <TableRow key={index}>
                          <TableCell><TextField size="small" value={attribute.name} onChange={(event) => updateAttribute(selectedApplicationIndex, index, { name: event.target.value })} /></TableCell>
                          <TableCell><TextField size="small" value={attribute.displayName ?? ""} onChange={(event) => updateAttribute(selectedApplicationIndex, index, { displayName: event.target.value })} /></TableCell>
                          <TableCell>
                            <Select size="small" value={attribute.dataType} onChange={(event) => updateAttribute(selectedApplicationIndex, index, { dataType: event.target.value })}>
                              {['string', 'number', 'boolean', 'date', 'datetime', 'array', 'object'].map((type) => (
                                <MenuItem key={type} value={type}>{type}</MenuItem>
                              ))}
                            </Select>
                          </TableCell>
                          <TableCell align="center"><Checkbox checked={attribute.required} onChange={(event) => updateAttribute(selectedApplicationIndex, index, { required: event.target.checked })} /></TableCell>
                          <TableCell align="center"><Checkbox checked={attribute.multiValued} onChange={(event) => updateAttribute(selectedApplicationIndex, index, { multiValued: event.target.checked })} /></TableCell>
                          <TableCell align="right"><IconButton color="error" onClick={() => removeAttribute(index)}><DeleteOutlineIcon /></IconButton></TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              </>
            )}
          </Stack>
        )}

        {activeStep === 3 && (
          <Stack spacing={3}>
            <Box>
              <Typography variant="h6" fontWeight={700}>Review Configuration</Typography>
              <Typography color="text.secondary" variant="body2">
                Confirm the integration and application schemas. Duplicate scoring and attribute weighting are calculated internally.
              </Typography>
            </Box>

            <Paper variant="outlined" sx={{ p: 2.5 }}>
              <Typography fontWeight={700}>{name}</Typography>
              <Typography variant="body2" color="text.secondary">
                Connector: {selectedConnector?.displayName ?? connectorType} · {enabled ? "Enabled" : "Disabled"}
              </Typography>
            </Paper>

            {applications.map((applicationItem, index) => (
              <Paper key={`${applicationItem.name}-${index}`} variant="outlined" sx={{ p: 2.5, borderRadius: 2 }}>
                <Typography fontWeight={700}>{applicationItem.name}</Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
                  {applicationItem.attributes.length} schema attributes · {applicationItem.enabled ? "Enabled" : "Disabled"}
                </Typography>
                <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap">
                  {applicationItem.attributes.map((attribute) => (
                    <Box key={attribute.name} sx={{ px: 1.25, py: 0.6, border: 1, borderColor: "divider", borderRadius: 2, fontSize: 13 }}>
                      {attribute.name} · {attribute.dataType}
                    </Box>
                  ))}
                </Stack>
              </Paper>
            ))}

            <Alert severity="info">
              After the integration is saved, the backend determines which attributes are useful for duplicate detection and calculates the internal scoring model automatically. Those internal weights are not part of the integrator workflow.
            </Alert>
          </Stack>
        )}

        <Box sx={{ display: "flex", justifyContent: "space-between", mt: 4, pt: 3, borderTop: 1, borderColor: "divider" }}>
          <Button disabled={activeStep === 0 || saving || detectingSchema} onClick={() => {
            setError("");
            setActiveStep((current) => Math.max(0, current - 1));
          }}>
            Back
          </Button>
          <Stack direction="row" spacing={1.5}>
            <Button variant="outlined" disabled={saving || detectingSchema} onClick={() => navigate("/integrations")}>Cancel</Button>
            {activeStep < steps.length - 1 ? (
              <Button variant="contained" disabled={detectingSchema} onClick={goNext}>Next</Button>
            ) : (
              <Button variant="contained" startIcon={<SaveIcon />} disabled={saving || detectingSchema} onClick={() => void handleSave()}>
                {saving ? "Saving..." : editing ? "Update Integration" : "Create Integration"}
              </Button>
            )}
          </Stack>
        </Box>
      </Paper>
    </PageContainer>
  );
};

export default AddIntegration;
