import {
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  Alert,
  Box,
  Button,
  CircularProgress,
  FormControl,
  FormControlLabel,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  Stack,
  Switch,
  TextField,
  Typography,
} from "@mui/material";

import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import SaveIcon from "@mui/icons-material/Save";

import {
  useNavigate,
  useParams,
} from "react-router-dom";

import PageContainer from "../../components/common/PageContainer";
import DynamicConnectorForm from "../../components/integrations/DynamicConnectorForm";

import {
  createIntegration,
  getConnectorTypes,
  getIntegration,
  updateIntegration,
  type ConnectorType,
} from "../../services/integrationService";

const AddIntegration = () => {
  const navigate = useNavigate();

  const { integrationId } = useParams<{
    integrationId: string;
  }>();

  const editing = Boolean(integrationId);

  const [connectorTypes, setConnectorTypes] =
    useState<ConnectorType[]>([]);

  const [connectorType, setConnectorType] =
    useState("");

  const [name, setName] = useState("");
  const [description, setDescription] =
    useState("");

  const [enabled, setEnabled] = useState(true);

  const [configuration, setConfiguration] =
    useState<Record<string, unknown>>({});

  const [fieldErrors, setFieldErrors] =
    useState<Record<string, string>>({});

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const selectedConnector = useMemo(
    () =>
      connectorTypes.find(
        (item) => item.type === connectorType
      ) ?? null,
    [connectorTypes, connectorType]
  );

  useEffect(() => {
    const loadPage = async () => {
      try {
        setLoading(true);
        setError("");

        const types = await getConnectorTypes();

        setConnectorTypes(types);

        if (editing && integrationId) {
          const integration = await getIntegration(
            Number(integrationId)
          );

          setName(integration.name);
          setDescription(
            integration.description ?? ""
          );
          setConnectorType(
            integration.connectorType
          );
          setConfiguration(
            integration.configuration
          );
          setEnabled(integration.enabled);
        } else if (types.length > 0) {
          const firstConnector = types[0];

          setConnectorType(firstConnector.type);

          const defaults =
            firstConnector.configurationSchema.fields.reduce<
              Record<string, unknown>
            >((result, field) => {
              if (field.default !== undefined) {
                result[field.name] = field.default;
              }

              return result;
            }, {});

          setConfiguration(defaults);
        }
      } catch (loadError) {
        setError(
          loadError instanceof Error
            ? loadError.message
            : "Unable to load integration form."
        );
      } finally {
        setLoading(false);
      }
    };

    loadPage();
  }, [editing, integrationId]);

  const handleConnectorTypeChange = (
    nextConnectorType: string
  ) => {
    setConnectorType(nextConnectorType);

    const connector = connectorTypes.find(
      (item) => item.type === nextConnectorType
    );

    const defaults =
      connector?.configurationSchema.fields.reduce<
        Record<string, unknown>
      >((result, field) => {
        if (field.default !== undefined) {
          result[field.name] = field.default;
        }

        return result;
      }, {}) ?? {};

    setConfiguration(defaults);
    setFieldErrors({});
  };

  const validate = (): boolean => {
    const errors: Record<string, string> = {};

    if (!name.trim()) {
      errors.name = "Integration name is required.";
    }

    if (!connectorType) {
      errors.connectorType =
        "Connector type is required.";
    }

    selectedConnector?.configurationSchema.fields.forEach(
      (field) => {
        const value = configuration[field.name];

        if (
          field.required &&
          (value === undefined ||
            value === null ||
            value === "")
        ) {
          errors[field.name] =
            `${field.label} is required.`;
        }
      }
    );

    setFieldErrors(errors);

    return Object.keys(errors).length === 0;
  };

  const handleSave = async () => {
    if (!validate()) {
      return;
    }

    try {
      setSaving(true);
      setError("");

      if (editing && integrationId) {
        await updateIntegration(
          Number(integrationId),
          {
            name: name.trim(),
            description:
              description.trim() || null,
            configuration,
            enabled,
          }
        );
      } else {
        await createIntegration({
          name: name.trim(),
          connectorType,
          description:
            description.trim() || null,
          configuration,
          enabled,
        });
      }

      navigate("/integrations");
    } catch (saveError) {
      setError(
        saveError instanceof Error
          ? saveError.message
          : "Unable to save integration."
      );
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <PageContainer title="Integration">
        <Box
          sx={{
            minHeight: 400,
            display: "flex",
            justifyContent: "center",
            alignItems: "center",
          }}
        >
          <CircularProgress />
        </Box>
      </PageContainer>
    );
  }

  return (
    <PageContainer
      title={
        editing
          ? "Edit Integration"
          : "Add Integration"
      }
    >
      <Box
        sx={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
          flexWrap: "wrap",
          gap: 2,
          mb: 4,
        }}
      >
        <Box>
          <Typography variant="h5" fontWeight={700}>
            {editing
              ? "Edit Integration"
              : "Create File Integration"}
          </Typography>

          <Typography
            color="text.secondary"
            sx={{ mt: 1 }}
          >
            Select a connector type and configure its
            source details.
          </Typography>
        </Box>

        <Button
          variant="outlined"
          startIcon={<ArrowBackIcon />}
          onClick={() => navigate("/integrations")}
        >
          Back
        </Button>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      <Paper
        variant="outlined"
        sx={{
          p: {
            xs: 2,
            md: 4,
          },
          borderRadius: 3,
          maxWidth: 900,
        }}
      >
        <Stack spacing={3}>
          <TextField
            fullWidth
            label="Integration Name"
            value={name}
            required
            error={Boolean(fieldErrors.name)}
            helperText={fieldErrors.name}
            onChange={(event) =>
              setName(event.target.value)
            }
          />

          <TextField
            fullWidth
            multiline
            minRows={3}
            label="Description"
            value={description}
            onChange={(event) =>
              setDescription(event.target.value)
            }
          />

          <FormControl
            fullWidth
            disabled={editing}
            error={Boolean(
              fieldErrors.connectorType
            )}
          >
            <InputLabel>Connector Type</InputLabel>

            <Select
              label="Connector Type"
              value={connectorType}
              onChange={(event) =>
                handleConnectorTypeChange(
                  event.target.value
                )
              }
            >
              {connectorTypes.map((connector) => (
                <MenuItem
                  key={connector.type}
                  value={connector.type}
                >
                  {connector.displayName}
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          {selectedConnector && (
            <>
              <Alert severity="info">
                {selectedConnector.description}
              </Alert>

              <DynamicConnectorForm
                connector={selectedConnector}
                values={configuration}
                errors={fieldErrors}
                onChange={(fieldName, value) =>
                  setConfiguration((current) => ({
                    ...current,
                    [fieldName]: value,
                  }))
                }
              />
            </>
          )}

          <FormControlLabel
            control={
              <Switch
                checked={enabled}
                onChange={(event) =>
                  setEnabled(event.target.checked)
                }
              />
            }
            label="Enable integration"
          />

          <Box
            sx={{
              display: "flex",
              justifyContent: "flex-end",
              gap: 2,
            }}
          >
            <Button
              variant="outlined"
              onClick={() =>
                navigate("/integrations")
              }
            >
              Cancel
            </Button>

            <Button
              variant="contained"
              startIcon={<SaveIcon />}
              disabled={saving}
              onClick={handleSave}
            >
              {saving
                ? "Saving..."
                : editing
                  ? "Update Integration"
                  : "Create Integration"}
            </Button>
          </Box>
        </Stack>
      </Paper>
    </PageContainer>
  );
};

export default AddIntegration;