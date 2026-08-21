import {
  Checkbox,
  FormControl,
  FormControlLabel,
  FormHelperText,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  TextField,
} from "@mui/material";

import type {
  ConnectorField,
  ConnectorType,
} from "../../services/integrationService";

interface Props {
  connector: ConnectorType;
  values: Record<string, unknown>;
  errors: Record<string, string>;
  onChange: (fieldName: string, value: unknown) => void;
}

const DynamicConnectorForm = ({ connector, values, errors, onChange }: Props) => {
  const resolvedValue = (fieldName: string): unknown => {
    if (values[fieldName] !== undefined && values[fieldName] !== null) {
      return values[fieldName];
    }
    return connector.configurationSchema.fields.find((item) => item.name === fieldName)?.default ?? "";
  };

  const isVisible = (field: ConnectorField): boolean => {
    if (!field.visibleWhen) return true;

    return Object.entries(field.visibleWhen).every(([dependency, allowedValues]) => {
      const current = resolvedValue(dependency);
      return allowedValues.map(String).includes(String(current));
    });
  };

  const renderField = (field: ConnectorField): React.ReactNode => {
    if (!isVisible(field)) return null;

    const value = values[field.name] ?? field.default ?? (field.type === "boolean" ? false : "");

    if (field.type === "select") {
      return (
        <FormControl key={field.name} fullWidth error={Boolean(errors[field.name])}>
          <InputLabel>{field.label}</InputLabel>
          <Select
            label={field.label}
            value={String(value)}
            onChange={(event) => onChange(field.name, event.target.value)}
          >
            {field.options?.map((option) => (
              <MenuItem key={String(option.value)} value={String(option.value)}>
                {option.label}
              </MenuItem>
            ))}
          </Select>
          <FormHelperText>{errors[field.name] || field.helpText}</FormHelperText>
        </FormControl>
      );
    }

    if (field.type === "boolean") {
      return (
        <FormControlLabel
          key={field.name}
          control={
            <Checkbox
              checked={Boolean(value)}
              onChange={(event) => onChange(field.name, event.target.checked)}
            />
          }
          label={field.label}
        />
      );
    }

    return (
      <TextField
        key={field.name}
        fullWidth
        type={field.type === "password" ? "password" : field.type === "number" ? "number" : "text"}
        label={field.label}
        value={value}
        placeholder={field.placeholder}
        required={field.required}
        error={Boolean(errors[field.name])}
        helperText={errors[field.name] || field.helpText}
        onChange={(event) =>
          onChange(
            field.name,
            field.type === "number" ? Number(event.target.value) : event.target.value,
          )
        }
      />
    );
  };

  return <Stack spacing={3}>{connector.configurationSchema.fields.map(renderField)}</Stack>;
};

export default DynamicConnectorForm;
