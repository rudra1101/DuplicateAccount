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
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControl,
  FormControlLabel,
  FormHelperText,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  Switch,
  TextField,
  Typography,
} from "@mui/material";

import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";
import SaveIcon from "@mui/icons-material/Save";

import {
  createIntegrationSchedule,
  deleteIntegrationSchedule,
  getIntegrationSchedule,
  updateIntegrationSchedule,
  type Integration,
  type JobSchedule,
} from "../../services/integrationService";

import {
  formatDateTime,
} from "../../utils/dateTime";

type ScheduleFrequency =
  | "daily"
  | "weekly"
  | "monthly"
  | "custom";

interface Props {
  open: boolean;
  integration: Integration | null;
  onClose: () => void;
  onSaved: (
    integrationId: number,
    schedule: JobSchedule | null
  ) => void;
}

interface FormErrors {
  name?: string;
  time?: string;
  dayOfMonth?: string;
  cronExpression?: string;
  timezone?: string;
}

const WEEKDAYS = [
  {
    label: "Monday",
    value: "mon",
  },
  {
    label: "Tuesday",
    value: "tue",
  },
  {
    label: "Wednesday",
    value: "wed",
  },
  {
    label: "Thursday",
    value: "thu",
  },
  {
    label: "Friday",
    value: "fri",
  },
  {
    label: "Saturday",
    value: "sat",
  },
  {
    label: "Sunday",
    value: "sun",
  },
];

const TIMEZONES = [
  {
    label: "India Standard Time",
    value: "Asia/Kolkata",
  },
  {
    label: "UTC",
    value: "UTC",
  },
  {
    label: "US Eastern",
    value: "America/New_York",
  },
  {
    label: "US Central",
    value: "America/Chicago",
  },
  {
    label: "US Mountain",
    value: "America/Denver",
  },
  {
    label: "US Pacific",
    value: "America/Los_Angeles",
  },
  {
    label: "United Kingdom",
    value: "Europe/London",
  },
  {
    label: "Singapore",
    value: "Asia/Singapore",
  },
];

const DEFAULT_TIME = "02:00";

function buildCronExpression(
  frequency: ScheduleFrequency,
  time: string,
  weekday: string,
  dayOfMonth: number,
  customExpression: string
): string {
  if (frequency === "custom") {
    return customExpression.trim();
  }

  const [hourValue, minuteValue] =
    time.split(":");

  const hour = Number(hourValue);
  const minute = Number(minuteValue);

  if (frequency === "daily") {
    return `${minute} ${hour} * * *`;
  }

  if (frequency === "weekly") {
    return `${minute} ${hour} * * ${weekday}`;
  }

  return `${minute} ${hour} ${dayOfMonth} * *`;
}

function parseCronExpression(
  cronExpression: string
): {
  frequency: ScheduleFrequency;
  time: string;
  weekday: string;
  dayOfMonth: number;
} {
  const parts = cronExpression
    .trim()
    .split(/\s+/);

  if (parts.length !== 5) {
    return {
      frequency: "custom",
      time: DEFAULT_TIME,
      weekday: "mon",
      dayOfMonth: 1,
    };
  }

  const [
    minute,
    hour,
    day,
    month,
    weekday,
  ] = parts;

  const validTime =
    /^\d+$/.test(hour) &&
    /^\d+$/.test(minute);

  const formattedTime = validTime
    ? `${String(Number(hour)).padStart(
        2,
        "0"
      )}:${String(Number(minute)).padStart(
        2,
        "0"
      )}`
    : DEFAULT_TIME;

  if (
    day === "*" &&
    month === "*" &&
    weekday === "*"
  ) {
    return {
      frequency: "daily",
      time: formattedTime,
      weekday: "mon",
      dayOfMonth: 1,
    };
  }

  if (
    day === "*" &&
    month === "*" &&
    weekday !== "*"
  ) {
    return {
      frequency: "weekly",
      time: formattedTime,
      weekday,
      dayOfMonth: 1,
    };
  }

  if (
    /^\d+$/.test(day) &&
    month === "*" &&
    weekday === "*"
  ) {
    return {
      frequency: "monthly",
      time: formattedTime,
      weekday: "mon",
      dayOfMonth: Number(day),
    };
  }

  return {
    frequency: "custom",
    time: formattedTime,
    weekday: "mon",
    dayOfMonth: 1,
  };
}

const ScheduleDialog = ({
  open,
  integration,
  onClose,
  onSaved,
}: Props) => {
  const [schedule, setSchedule] =
    useState<JobSchedule | null>(null);

  const [loading, setLoading] =
    useState(false);

  const [saving, setSaving] =
    useState(false);

  const [deleting, setDeleting] =
    useState(false);

  const [error, setError] =
    useState("");

  const [name, setName] =
    useState("");

  const [frequency, setFrequency] =
    useState<ScheduleFrequency>("daily");

  const [time, setTime] =
    useState(DEFAULT_TIME);

  const [weekday, setWeekday] =
    useState("mon");

  const [dayOfMonth, setDayOfMonth] =
    useState(1);

  const [customCron, setCustomCron] =
    useState("");

  const [timezone, setTimezone] =
    useState("Asia/Kolkata");

  const [enabled, setEnabled] =
    useState(true);

  const [formErrors, setFormErrors] =
    useState<FormErrors>({});

  const generatedCron = useMemo(
    () =>
      buildCronExpression(
        frequency,
        time,
        weekday,
        dayOfMonth,
        customCron
      ),
    [
      frequency,
      time,
      weekday,
      dayOfMonth,
      customCron,
    ]
  );

  useEffect(() => {
    if (!open || !integration) {
      return;
    }

    const loadSchedule = async () => {
      try {
        setLoading(true);
        setError("");
        setFormErrors({});

        const result =
          await getIntegrationSchedule(
            integration.id
          );

        setSchedule(result);

        if (result) {
          const parsed =
            parseCronExpression(
              result.cronExpression
            );

          setName(result.name);
          setFrequency(
            parsed.frequency
          );
          setTime(parsed.time);
          setWeekday(parsed.weekday);
          setDayOfMonth(
            parsed.dayOfMonth
          );
          setCustomCron(
            parsed.frequency === "custom"
              ? result.cronExpression
              : ""
          );
          setTimezone(
            result.timezone ||
              "Asia/Kolkata"
          );
          setEnabled(result.enabled);
        } else {
          setName(
            `${integration.name} Schedule`
          );
          setFrequency("daily");
          setTime(DEFAULT_TIME);
          setWeekday("mon");
          setDayOfMonth(1);
          setCustomCron("");
          setTimezone(
            "Asia/Kolkata"
          );
          setEnabled(true);
        }
      } catch (loadError) {
        setError(
          loadError instanceof Error
            ? loadError.message
            : "Unable to load schedule."
        );
      } finally {
        setLoading(false);
      }
    };

    loadSchedule();
  }, [open, integration]);

  const validate = (): boolean => {
    const errors: FormErrors = {};

    if (!name.trim()) {
      errors.name =
        "Schedule name is required.";
    }

    if (!timezone.trim()) {
      errors.timezone =
        "Timezone is required.";
    }

    if (
      frequency !== "custom" &&
      !/^\d{2}:\d{2}$/.test(time)
    ) {
      errors.time =
        "A valid time is required.";
    }

    if (
      frequency === "monthly" &&
      (dayOfMonth < 1 ||
        dayOfMonth > 31)
    ) {
      errors.dayOfMonth =
        "Day must be between 1 and 31.";
    }

    if (
      frequency === "custom" &&
      generatedCron.split(/\s+/)
        .length !== 5
    ) {
      errors.cronExpression =
        "Cron expression must contain five fields.";
    }

    setFormErrors(errors);

    return (
      Object.keys(errors).length === 0
    );
  };

  const handleSave = async () => {
    if (!integration || !validate()) {
      return;
    }

    try {
      setSaving(true);
      setError("");

      const payload = {
        name: name.trim(),
        cronExpression:
          generatedCron,
        timezone,
        enabled,
      };

      const savedSchedule =
        schedule
          ? await updateIntegrationSchedule(
              integration.id,
              payload
            )
          : await createIntegrationSchedule(
              integration.id,
              payload
            );

      setSchedule(savedSchedule);

      onSaved(
        integration.id,
        savedSchedule
      );

      onClose();
    } catch (saveError) {
      setError(
        saveError instanceof Error
          ? saveError.message
          : "Unable to save schedule."
      );
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!integration || !schedule) {
      return;
    }

    const confirmed =
      window.confirm(
        "Delete this schedule? The integration itself will not be deleted."
      );

    if (!confirmed) {
      return;
    }

    try {
      setDeleting(true);
      setError("");

      await deleteIntegrationSchedule(
        integration.id
      );

      setSchedule(null);

      onSaved(
        integration.id,
        null
      );

      onClose();
    } catch (deleteError) {
      setError(
        deleteError instanceof Error
          ? deleteError.message
          : "Unable to delete schedule."
      );
    } finally {
      setDeleting(false);
    }
  };

  return (
    <Dialog
      open={open}
      onClose={
        saving || deleting
          ? undefined
          : onClose
      }
      fullWidth
      maxWidth="sm"
    >
      <DialogTitle>
        {schedule
          ? "Edit Schedule"
          : "Create Schedule"}
      </DialogTitle>

      <DialogContent dividers>
        {loading ? (
          <Box
            sx={{
              minHeight: 320,
              display: "flex",
              justifyContent:
                "center",
              alignItems: "center",
            }}
          >
            <CircularProgress />
          </Box>
        ) : (
          <Stack spacing={3}>
            {integration && (
              <Alert severity="info">
                Configure automatic
                ingestion for{" "}
                <strong>
                  {integration.name}
                </strong>
                .
              </Alert>
            )}

            {error && (
              <Alert severity="error">
                {error}
              </Alert>
            )}

            <TextField
              fullWidth
              required
              label="Schedule Name"
              value={name}
              error={Boolean(
                formErrors.name
              )}
              helperText={
                formErrors.name
              }
              onChange={(event) =>
                setName(
                  event.target.value
                )
              }
            />

            <FormControl fullWidth>
              <InputLabel>
                Frequency
              </InputLabel>

              <Select
                label="Frequency"
                value={frequency}
                onChange={(event) =>
                  setFrequency(
                    event.target
                      .value as ScheduleFrequency
                  )
                }
              >
                <MenuItem value="daily">
                  Daily
                </MenuItem>

                <MenuItem value="weekly">
                  Weekly
                </MenuItem>

                <MenuItem value="monthly">
                  Monthly
                </MenuItem>

                <MenuItem value="custom">
                  Custom Cron
                </MenuItem>
              </Select>
            </FormControl>

            {frequency === "weekly" && (
              <FormControl fullWidth>
                <InputLabel>
                  Day of Week
                </InputLabel>

                <Select
                  label="Day of Week"
                  value={weekday}
                  onChange={(event) =>
                    setWeekday(
                      event.target.value
                    )
                  }
                >
                  {WEEKDAYS.map(
                    (day) => (
                      <MenuItem
                        key={day.value}
                        value={
                          day.value
                        }
                      >
                        {day.label}
                      </MenuItem>
                    )
                  )}
                </Select>
              </FormControl>
            )}

            {frequency ===
              "monthly" && (
              <TextField
                fullWidth
                type="number"
                label="Day of Month"
                value={dayOfMonth}
                error={Boolean(
                  formErrors.dayOfMonth
                )}
                helperText={
                  formErrors.dayOfMonth ??
                  "Enter a value between 1 and 31."
                }
                slotProps={{
                  htmlInput: {
                    min: 1,
                    max: 31,
                  },
                }}
                onChange={(event) =>
                  setDayOfMonth(
                    Number(
                      event.target
                        .value
                    )
                  )
                }
              />
            )}

            {frequency !== "custom" && (
              <TextField
                fullWidth
                type="time"
                label="Run Time"
                value={time}
                error={Boolean(
                  formErrors.time
                )}
                helperText={
                  formErrors.time
                }
                slotProps={{
                  inputLabel: {
                    shrink: true,
                  },
                }}
                onChange={(event) =>
                  setTime(
                    event.target.value
                  )
                }
              />
            )}

            {frequency === "custom" && (
              <TextField
                fullWidth
                label="Cron Expression"
                value={customCron}
                placeholder="0 2 * * *"
                error={Boolean(
                  formErrors.cronExpression
                )}
                helperText={
                  formErrors.cronExpression ??
                  "Format: minute hour day month day-of-week"
                }
                onChange={(event) =>
                  setCustomCron(
                    event.target.value
                  )
                }
              />
            )}

            <FormControl
              fullWidth
              error={Boolean(
                formErrors.timezone
              )}
            >
              <InputLabel>
                Timezone
              </InputLabel>

              <Select
                label="Timezone"
                value={timezone}
                onChange={(event) =>
                  setTimezone(
                    event.target.value
                  )
                }
              >
                {TIMEZONES.map(
                  (item) => (
                    <MenuItem
                      key={item.value}
                      value={item.value}
                    >
                      {item.label} (
                      {item.value})
                    </MenuItem>
                  )
                )}
              </Select>

              <FormHelperText>
                {formErrors.timezone}
              </FormHelperText>
            </FormControl>

            <FormControlLabel
              control={
                <Switch
                  checked={enabled}
                  onChange={(event) =>
                    setEnabled(
                      event.target
                        .checked
                    )
                  }
                />
              }
              label="Enable schedule"
            />

            <Box
              sx={{
                p: 2,
                borderRadius: 2,
                backgroundColor:
                  "action.hover",
              }}
            >
              <Typography
                variant="caption"
                color="text.secondary"
              >
                Generated cron expression
              </Typography>

              <Typography
                fontFamily="monospace"
                fontWeight={700}
                sx={{ mt: 0.5 }}
              >
                {generatedCron ||
                  "Not available"}
              </Typography>
            </Box>

            {schedule && (
              <Box
                sx={{
                  display: "grid",
                  gridTemplateColumns: {
                    xs: "1fr",
                    sm: "1fr 1fr",
                  },
                  gap: 2,
                }}
              >
                <Box>
                  <Typography
                    variant="caption"
                    color="text.secondary"
                  >
                    Next run
                  </Typography>

                  <Typography
                    variant="body2"
                    fontWeight={600}
                  >
                    {formatDateTime(
                      schedule.nextRunAt,
                      schedule.timezone
                    )}
                  </Typography>
                </Box>

                <Box>
                  <Typography
                    variant="caption"
                    color="text.secondary"
                  >
                    Last run
                  </Typography>

                  <Typography
                    variant="body2"
                    fontWeight={600}
                  >
                    {formatDateTime(
                      schedule.lastRunAt,
                      schedule.timezone
                    )}
                  </Typography>
                </Box>

                {schedule.lastError && (
                  <Alert
                    severity="error"
                    sx={{
                      gridColumn:
                        "1 / -1",
                    }}
                  >
                    {schedule.lastError}
                  </Alert>
                )}
              </Box>
            )}
          </Stack>
        )}
      </DialogContent>

      <DialogActions
        sx={{
          justifyContent:
            schedule
              ? "space-between"
              : "flex-end",
          px: 3,
          py: 2,
        }}
      >
        {schedule && (
          <Button
            color="error"
            startIcon={
              <DeleteOutlineIcon />
            }
            disabled={
              saving || deleting
            }
            onClick={handleDelete}
          >
            {deleting
              ? "Deleting..."
              : "Delete Schedule"}
          </Button>
        )}

        <Stack
          direction="row"
          spacing={1}
        >
          <Button
            onClick={onClose}
            disabled={
              saving || deleting
            }
          >
            Cancel
          </Button>

          <Button
            variant="contained"
            startIcon={<SaveIcon />}
            disabled={
              saving ||
              deleting ||
              loading
            }
            onClick={handleSave}
          >
            {saving
              ? "Saving..."
              : schedule
                ? "Update Schedule"
                : "Create Schedule"}
          </Button>
        </Stack>
      </DialogActions>
    </Dialog>
  );
};

export default ScheduleDialog;