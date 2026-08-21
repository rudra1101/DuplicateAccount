import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Divider,
  Drawer,
  IconButton,
  Paper,
  Stack,
  Tooltip,
  Typography,
} from "@mui/material";

import CloseIcon from "@mui/icons-material/Close";
import RefreshIcon from "@mui/icons-material/Refresh";
import DescriptionOutlinedIcon from "@mui/icons-material/DescriptionOutlined";
import GroupsOutlinedIcon from "@mui/icons-material/GroupsOutlined";
import WarningAmberOutlinedIcon from "@mui/icons-material/WarningAmberOutlined";
import TimerOutlinedIcon from "@mui/icons-material/TimerOutlined";
import VisibilityOutlinedIcon from "@mui/icons-material/VisibilityOutlined";

import {
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  getIntegrationExecutions,
  type Integration,
  type IntegrationExecution,
  type JobSchedule,
} from "../../services/integrationService";

import {
  formatDateTime,
} from "../../utils/dateTime";
import ScanAccountsDrawer from "./ScanAccountsDrawer";

interface Props {
  open: boolean;
  integration: Integration | null;
  schedule: JobSchedule | null | undefined;
  onClose: () => void;
}

type StatusColor =
  | "success"
  | "error"
  | "warning"
  | "info"
  | "default";

function getStatusColor(
  status: string
): StatusColor {
  if (status === "COMPLETED") {
    return "success";
  }

  if (status === "FAILED") {
    return "error";
  }

  if (status === "RUNNING") {
    return "info";
  }

  return "warning";
}

function calculateDuration(
  startedAt: string | null,
  completedAt: string | null
): string {
  if (!startedAt) {
    return "-";
  }

  if (!completedAt) {
    return "In progress";
  }

  const start = new Date(startedAt);
  const end = new Date(completedAt);

  if (
    Number.isNaN(start.getTime()) ||
    Number.isNaN(end.getTime())
  ) {
    return "-";
  }

  const durationMilliseconds =
    end.getTime() - start.getTime();

  if (durationMilliseconds < 0) {
    return "-";
  }

  const totalSeconds = Math.floor(
    durationMilliseconds / 1000
  );

  if (totalSeconds < 60) {
    return `${totalSeconds} sec`;
  }

  const minutes = Math.floor(
    totalSeconds / 60
  );

  const seconds =
    totalSeconds % 60;

  if (minutes < 60) {
    return `${minutes} min ${seconds} sec`;
  }

  const hours = Math.floor(
    minutes / 60
  );

  const remainingMinutes =
    minutes % 60;

  return `${hours} hr ${remainingMinutes} min`;
}

interface ExecutionItemProps {
  execution: IntegrationExecution;
  timezone: string;
  onViewAccounts: (scanId: number) => void;
}

const ExecutionItem = ({
  execution,
  timezone,
  onViewAccounts,
}: ExecutionItemProps) => {
  const duration = calculateDuration(
    execution.startedAt,
    execution.completedAt
  );

  return (
    <Paper
      variant="outlined"
      sx={{
        p: 2.5,
        borderRadius: 2.5,
      }}
    >
      <Stack spacing={2}>
        <Stack
          direction="row"
          justifyContent="space-between"
          alignItems="flex-start"
          spacing={2}
        >
          <Box>
            <Stack
              direction="row"
              spacing={1}
              alignItems="center"
              useFlexGap
              flexWrap="wrap"
            >
              <Chip
                size="small"
                label={execution.status}
                color={getStatusColor(
                  execution.status
                )}
              />

              {execution.scanId && (
                <Chip
                  size="small"
                  variant="outlined"
                  label={`Scan #${execution.scanId}`}
                />
              )}
            </Stack>

            <Typography
              variant="body2"
              fontWeight={700}
              sx={{ mt: 1.25 }}
            >
              {formatDateTime(
                execution.startedAt,
                timezone
              )}
            </Typography>
          </Box>

          <Box textAlign="right">
            <Typography
              variant="caption"
              color="text.secondary"
            >
              Duration
            </Typography>

            <Typography
              variant="body2"
              fontWeight={700}
            >
              {duration}
            </Typography>
          </Box>
        </Stack>

        <Divider />

        <Stack spacing={1.25}>
          <Stack
            direction="row"
            spacing={1}
            alignItems="flex-start"
          >
            <DescriptionOutlinedIcon
              fontSize="small"
              color="action"
            />

            <Box sx={{ minWidth: 0 }}>
              <Typography
                variant="caption"
                color="text.secondary"
              >
                Source file
              </Typography>

              <Typography
                variant="body2"
                fontWeight={600}
                sx={{
                  overflowWrap: "anywhere",
                }}
              >
                {execution.sourceFileName ||
                  "Not available"}
              </Typography>
            </Box>
          </Stack>

          <Stack
            direction="row"
            spacing={1}
            alignItems="center"
          >
            <GroupsOutlinedIcon
              fontSize="small"
              color="action"
            />

            <Typography variant="body2">
              {Number(
                execution.accountsScanned ?? 0
              ).toLocaleString()}{" "}
              accounts scanned
            </Typography>
          </Stack>

          <Stack
            direction="row"
            spacing={1}
            alignItems="center"
          >
            <WarningAmberOutlinedIcon
              fontSize="small"
              color="action"
            />

            <Typography variant="body2">
              {Number(
                execution.duplicateGroups ?? 0
              ).toLocaleString()}{" "}
              duplicate groups ·{" "}
              {Number(
                execution.duplicateAccounts ?? 0
              ).toLocaleString()}{" "}
              duplicate accounts
            </Typography>
          </Stack>

          <Stack
            direction="row"
            spacing={1}
            alignItems="center"
          >
            <TimerOutlinedIcon
              fontSize="small"
              color="action"
            />

            <Typography variant="body2">
              Completed:{" "}
              {formatDateTime(
                execution.completedAt,
                timezone
              )}
            </Typography>
          </Stack>
        </Stack>

        {execution.scanId && execution.status === "COMPLETED" && (
          <Button
            variant="outlined"
            size="small"
            startIcon={<VisibilityOutlinedIcon />}
            onClick={() => onViewAccounts(execution.scanId as number)}
            sx={{ alignSelf: "flex-start" }}
          >
            View Scanned Accounts
          </Button>
        )}

        {execution.errorMessage && (
          <Alert severity="error">
            {execution.errorMessage}
          </Alert>
        )}

        {execution.sourcePath && (
          <Box
            sx={{
              p: 1.5,
              borderRadius: 2,
              backgroundColor: "action.hover",
            }}
          >
            <Typography
              variant="caption"
              color="text.secondary"
            >
              Source path
            </Typography>

            <Typography
              variant="body2"
              fontFamily="monospace"
              sx={{
                mt: 0.5,
                overflowWrap: "anywhere",
              }}
            >
              {execution.sourcePath}
            </Typography>
          </Box>
        )}
      </Stack>
    </Paper>
  );
};

const ExecutionHistoryDrawer = ({
  open,
  integration,
  schedule,
  onClose,
}: Props) => {
  const [
    executions,
    setExecutions,
  ] = useState<IntegrationExecution[]>([]);

  const [loading, setLoading] =
    useState(false);

  const [refreshing, setRefreshing] =
    useState(false);

  const [error, setError] =
    useState("");

  const [selectedScanId, setSelectedScanId] =
    useState<number | null>(null);

  const timezone =
    schedule?.timezone ||
    "Asia/Kolkata";

  const summary = useMemo(() => {
    return executions.reduce(
      (result, execution) => {
        if (
          execution.status ===
          "COMPLETED"
        ) {
          result.completed += 1;
        }

        if (
          execution.status ===
          "FAILED"
        ) {
          result.failed += 1;
        }

        if (
          execution.status ===
          "RUNNING"
        ) {
          result.running += 1;
        }

        return result;
      },
      {
        completed: 0,
        failed: 0,
        running: 0,
      }
    );
  }, [executions]);

  const loadExecutions = async (
    refresh = false
  ) => {
    if (!integration) {
      return;
    }

    try {
      if (refresh) {
        setRefreshing(true);
      } else {
        setLoading(true);
      }

      setError("");

      const data =
        await getIntegrationExecutions(
          integration.id,
          50
        );

      setExecutions(data);
    } catch (loadError) {
      setError(
        loadError instanceof Error
          ? loadError.message
          : "Unable to load execution history."
      );
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    if (open && integration) {
      loadExecutions();
    }

    if (!open) {
      setExecutions([]);
      setError("");
      setSelectedScanId(null);
    }
  }, [open, integration?.id]);

  return (
    <>
      <Drawer
        anchor="right"
        open={open}
        onClose={onClose}
        slotProps={{
          paper: {
            sx: {
              width: {
                xs: "100%",
                sm: 520,
              },
            },
          },
        }}
      >
        <Box
          sx={{
            height: "100%",
            display: "flex",
            flexDirection: "column",
          }}
        >
          <Box
            sx={{
              px: 3,
              py: 2.5,
              borderBottom: 1,
              borderColor: "divider",
            }}
          >
            <Stack
              direction="row"
              justifyContent="space-between"
              alignItems="flex-start"
              spacing={2}
            >
              <Box>
                <Typography
                  variant="h6"
                  fontWeight={700}
                >
                  Execution History
                </Typography>

                <Typography
                  variant="body2"
                  color="text.secondary"
                  sx={{ mt: 0.5 }}
                >
                  {integration?.name ||
                    "Integration"}
                </Typography>
              </Box>

              <Stack direction="row">
                <Tooltip title="Refresh">
                  <span>
                    <IconButton
                      onClick={() =>
                        loadExecutions(true)
                      }
                      disabled={
                        loading || refreshing
                      }
                    >
                      {refreshing ? (
                        <CircularProgress
                          size={20}
                        />
                      ) : (
                        <RefreshIcon />
                      )}
                    </IconButton>
                  </span>
                </Tooltip>

                <IconButton onClick={onClose}>
                  <CloseIcon />
                </IconButton>
              </Stack>
            </Stack>

            <Stack
              direction="row"
              spacing={1}
              useFlexGap
              flexWrap="wrap"
              sx={{ mt: 2 }}
            >
              <Chip
                size="small"
                color="success"
                variant="outlined"
                label={`${summary.completed} completed`}
              />

              <Chip
                size="small"
                color="error"
                variant="outlined"
                label={`${summary.failed} failed`}
              />

              {summary.running > 0 && (
                <Chip
                  size="small"
                  color="info"
                  variant="outlined"
                  label={`${summary.running} running`}
                />
              )}

              <Chip
                size="small"
                variant="outlined"
                label={timezone}
              />
            </Stack>
          </Box>

          <Box
            sx={{
              flex: 1,
              overflowY: "auto",
              p: 3,
            }}
          >
            {error && (
              <Alert
                severity="error"
                sx={{ mb: 2 }}
              >
                {error}
              </Alert>
            )}

            {loading ? (
              <Box
                sx={{
                  minHeight: 300,
                  display: "flex",
                  justifyContent: "center",
                  alignItems: "center",
                }}
              >
                <CircularProgress />
              </Box>
            ) : executions.length === 0 ? (
              <Alert severity="info">
                No executions are available for
                this integration.
              </Alert>
            ) : (
              <Stack spacing={2}>
                {executions.map(
                  (execution) => (
                    <ExecutionItem
                      key={
                        execution.executionId
                      }
                      execution={execution}
                      timezone={timezone}
                      onViewAccounts={setSelectedScanId}
                    />
                  )
                )}
              </Stack>
            )}
          </Box>
        </Box>
      </Drawer>

      <ScanAccountsDrawer
        open={selectedScanId !== null}
        scanId={selectedScanId}
        onClose={() => setSelectedScanId(null)}
      />
    </>
  );
};

export default ExecutionHistoryDrawer;
