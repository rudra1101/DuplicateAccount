import {
  Alert,
  Box,
  Chip,
  Divider,
  Drawer,
  IconButton,
  Paper,
  Stack,
  Typography,
} from "@mui/material";

import CloseIcon from "@mui/icons-material/Close";
import DescriptionOutlinedIcon from "@mui/icons-material/DescriptionOutlined";
import FingerprintIcon from "@mui/icons-material/Fingerprint";
import GroupsOutlinedIcon from "@mui/icons-material/GroupsOutlined";
import ScheduleIcon from "@mui/icons-material/Schedule";
import TimerOutlinedIcon from "@mui/icons-material/TimerOutlined";

import type { OperationExecution } from "../../services/operationsService";
import { formatDateTime } from "../../utils/dateTime";

interface Props {
  open: boolean;
  execution: OperationExecution | null;
  onClose: () => void;
}

function getStatusColor(
  status: string
): "success" | "error" | "info" | "warning" | "default" {
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

function calculateDetailedDuration(
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

  const milliseconds = Math.max(
    0,
    end.getTime() - start.getTime()
  );

  if (milliseconds < 1000) {
    return `${milliseconds} ms`;
  }

  const totalSeconds = milliseconds / 1000;

  if (totalSeconds < 60) {
    return `${totalSeconds.toFixed(2)} sec`;
  }

  const minutes = Math.floor(totalSeconds / 60);
  const seconds = Math.floor(totalSeconds % 60);

  if (minutes < 60) {
    return `${minutes} min ${seconds} sec`;
  }

  const hours = Math.floor(minutes / 60);
  const remainingMinutes = minutes % 60;

  return `${hours} hr ${remainingMinutes} min`;
}

interface DetailRowProps {
  label: string;
  value: React.ReactNode;
}

const DetailRow = ({
  label,
  value,
}: DetailRowProps) => {
  return (
    <Box>
      <Typography
        variant="caption"
        color="text.secondary"
      >
        {label}
      </Typography>

      <Typography
        variant="body2"
        fontWeight={600}
        sx={{
          mt: 0.25,
          overflowWrap: "anywhere",
        }}
      >
        {value}
      </Typography>
    </Box>
  );
};

const ExecutionDetailsDrawer = ({
  open,
  execution,
  onClose,
}: Props) => {
  const duration = execution
    ? calculateDetailedDuration(
        execution.startedAt,
        execution.completedAt
      )
    : "-";

  return (
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
                Execution Details
              </Typography>

              <Typography
                variant="body2"
                color="text.secondary"
                sx={{ mt: 0.5 }}
              >
                {execution
                  ? `Execution #${execution.executionId}`
                  : "Execution"}
              </Typography>
            </Box>

            <IconButton onClick={onClose}>
              <CloseIcon />
            </IconButton>
          </Stack>
        </Box>

        <Box
          sx={{
            flex: 1,
            overflowY: "auto",
            p: 3,
          }}
        >
          {!execution ? (
            <Alert severity="info">
              No execution selected.
            </Alert>
          ) : (
            <Stack spacing={3}>
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
                    alignItems="center"
                    spacing={2}
                  >
                    <Chip
                      label={execution.status}
                      color={getStatusColor(
                        execution.status
                      )}
                    />

                    {execution.scanId && (
                      <Chip
                        variant="outlined"
                        label={`Scan #${execution.scanId}`}
                      />
                    )}
                  </Stack>

                  <Divider />

                  <Stack spacing={2}>
                    <DetailRow
                      label="Integration"
                      value={execution.integrationName}
                    />

                    <DetailRow
                      label="Connector Type"
                      value={execution.connectorType}
                    />

                    <DetailRow
                      label="Trigger Type"
                      value="Manual or Scheduled"
                    />
                  </Stack>
                </Stack>
              </Paper>

              <Paper
                variant="outlined"
                sx={{
                  p: 2.5,
                  borderRadius: 2.5,
                }}
              >
                <Stack spacing={2}>
                  <Typography
                    variant="subtitle1"
                    fontWeight={700}
                  >
                    Timing
                  </Typography>

                  <Stack
                    direction="row"
                    spacing={1.5}
                    alignItems="flex-start"
                  >
                    <ScheduleIcon color="action" />

                    <Box>
                      <DetailRow
                        label="Started At"
                        value={formatDateTime(
                          execution.startedAt
                        )}
                      />

                      <Box sx={{ mt: 2 }}>
                        <DetailRow
                          label="Completed At"
                          value={formatDateTime(
                            execution.completedAt
                          )}
                        />
                      </Box>
                    </Box>
                  </Stack>

                  <Stack
                    direction="row"
                    spacing={1.5}
                    alignItems="center"
                  >
                    <TimerOutlinedIcon color="action" />

                    <DetailRow
                      label="Duration"
                      value={duration}
                    />
                  </Stack>
                </Stack>
              </Paper>

              <Paper
                variant="outlined"
                sx={{
                  p: 2.5,
                  borderRadius: 2.5,
                }}
              >
                <Stack spacing={2}>
                  <Typography
                    variant="subtitle1"
                    fontWeight={700}
                  >
                    Source
                  </Typography>

                  <Stack
                    direction="row"
                    spacing={1.5}
                    alignItems="flex-start"
                  >
                    <DescriptionOutlinedIcon color="action" />

                    <Box sx={{ minWidth: 0 }}>
                      <DetailRow
                        label="Source File"
                        value={
                          execution.sourceFileName ??
                          "Not available"
                        }
                      />

                      <Box sx={{ mt: 2 }}>
                        <DetailRow
                          label="Source Path"
                          value={
                            execution.sourcePath ??
                            "Not available"
                          }
                        />
                      </Box>
                    </Box>
                  </Stack>

                  <Stack
                    direction="row"
                    spacing={1.5}
                    alignItems="flex-start"
                  >
                    <FingerprintIcon color="action" />

                    <DetailRow
                      label="Checksum"
                      value={
                        execution.fileChecksum ??
                        "Not available"
                      }
                    />
                  </Stack>
                </Stack>
              </Paper>

              <Paper
                variant="outlined"
                sx={{
                  p: 2.5,
                  borderRadius: 2.5,
                }}
              >
                <Stack spacing={2}>
                  <Typography
                    variant="subtitle1"
                    fontWeight={700}
                  >
                    Processing Results
                  </Typography>

                  <Stack
                    direction="row"
                    spacing={1.5}
                    alignItems="center"
                  >
                    <GroupsOutlinedIcon color="action" />

                    <Box>
                      <DetailRow
                        label="Accounts Scanned"
                        value={execution.accountsScanned.toLocaleString()}
                      />

                      <Box sx={{ mt: 2 }}>
                        <DetailRow
                          label="Duplicate Groups"
                          value={execution.duplicateGroups.toLocaleString()}
                        />
                      </Box>

                      <Box sx={{ mt: 2 }}>
                        <DetailRow
                          label="Duplicate Accounts"
                          value={execution.duplicateAccounts.toLocaleString()}
                        />
                      </Box>
                    </Box>
                  </Stack>
                </Stack>
              </Paper>

              {execution.errorMessage && (
                <Alert severity="error">
                  <Typography fontWeight={700}>
                    Execution Error
                  </Typography>

                  <Typography
                    variant="body2"
                    sx={{ mt: 0.5 }}
                  >
                    {execution.errorMessage}
                  </Typography>
                </Alert>
              )}
            </Stack>
          )}
        </Box>
      </Box>
    </Drawer>
  );
};

export default ExecutionDetailsDrawer;