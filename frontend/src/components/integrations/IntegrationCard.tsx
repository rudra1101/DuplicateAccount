import {
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Divider,
  Stack,
  Typography,
} from "@mui/material";
import StorageIcon from "@mui/icons-material/Storage";
import SettingsEthernetIcon from "@mui/icons-material/SettingsEthernet";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";
import EditOutlinedIcon from "@mui/icons-material/EditOutlined";
import PlayCircleOutlineIcon from "@mui/icons-material/PlayCircleOutline";
import RocketLaunchOutlinedIcon from "@mui/icons-material/RocketLaunchOutlined";
import ScheduleIcon from "@mui/icons-material/Schedule";
import HistoryIcon from "@mui/icons-material/History";

import type { Integration, JobSchedule } from "../../services/integrationService";
import { formatDateTime } from "../../utils/dateTime";

interface Props {
  integration: Integration;
  schedule: JobSchedule | null | undefined;
  testing: boolean;
  running: boolean;
  canRun: boolean;
  canSchedule: boolean;
  canViewHistory: boolean;
  canTest: boolean;
  canEdit: boolean;
  canDelete: boolean;
  onEdit: (integration: Integration) => void;
  onDelete: (integration: Integration) => void;
  onTest: (integration: Integration) => void;
  onRun: (integration: Integration) => void;
  onSchedule: (integration: Integration) => void;
  onHistory: (integration: Integration) => void;
}

function connectorIcon(connectorType: string): React.ReactNode {
  if (connectorType === "LOCAL") return <StorageIcon color="primary" />;
  return <SettingsEthernetIcon color="primary" />;
}

function getStatusColor(status: string | null | undefined): "success" | "error" | "warning" | "default" {
  if (status === "COMPLETED") return "success";
  if (status === "FAILED") return "error";
  if (status === "RUNNING" || status === "SKIPPED") return "warning";
  return "default";
}

const IntegrationCard = ({
  integration,
  schedule,
  testing,
  running,
  canRun,
  canSchedule,
  canViewHistory,
  canTest,
  canEdit,
  canDelete,
  onEdit,
  onDelete,
  onTest,
  onRun,
  onSchedule,
  onHistory,
}: Props) => {
  const folderPath =
    integration.connectorType === "LOCAL"
      ? String(integration.configuration.folderPath ?? "Folder not configured")
      : "Connector configuration saved";

  return (
    <Card
      variant="outlined"
      sx={{
        width: "100%",
        minWidth: 0,
        height: "100%",
        borderRadius: 3,
        display: "flex",
        flexDirection: "column",
        transition: "transform 0.2s, box-shadow 0.2s",
        "&:hover": { transform: "translateY(-3px)", boxShadow: 3 },
      }}
    >
      <CardContent sx={{ p: 3, display: "flex", flexDirection: "column", flex: 1, "&:last-child": { pb: 3 } }}>
        <Stack direction="row" justifyContent="space-between" alignItems="flex-start" spacing={2}>
          <Stack direction="row" spacing={1.5} alignItems="center" sx={{ minWidth: 0, flex: 1 }}>
            <Box sx={{ width: 44, height: 44, borderRadius: 2, flexShrink: 0, backgroundColor: "action.hover", display: "flex", alignItems: "center", justifyContent: "center" }}>
              {connectorIcon(integration.connectorType)}
            </Box>
            <Box sx={{ minWidth: 0 }}>
              <Typography fontWeight={700} noWrap>{integration.name}</Typography>
              <Typography variant="body2" color="text.secondary">{integration.connectorType}</Typography>
            </Box>
          </Stack>
          <Chip size="small" label={integration.enabled ? "Enabled" : "Disabled"} color={integration.enabled ? "success" : "default"} />
        </Stack>

        <Typography variant="body2" color="text.secondary" sx={{ mt: 3, minHeight: 42 }}>
          {integration.description || "No description provided."}
        </Typography>

        <Box sx={{ mt: 2, p: 1.75, borderRadius: 2, backgroundColor: "action.hover" }}>
          <Typography variant="caption" color="text.secondary">Configuration</Typography>
          <Typography variant="body2" fontWeight={600} title={folderPath} sx={{ mt: 0.5, lineHeight: 1.5, overflowWrap: "anywhere" }}>
            {folderPath}
          </Typography>
        </Box>

        <Divider sx={{ my: 2 }} />

        <Box>
          <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1.5 }}>
            <Typography variant="subtitle2" fontWeight={700}>Schedule</Typography>
            {schedule ? (
              <Chip size="small" label={schedule.enabled ? "Active" : "Disabled"} color={schedule.enabled ? "success" : "default"} variant="outlined" />
            ) : (
              <Chip size="small" label="Not configured" variant="outlined" />
            )}
          </Stack>

          {schedule ? (
            <Stack spacing={1.5}>
              <Box>
                <Typography variant="caption" color="text.secondary">Timezone</Typography>
                <Typography variant="body2" fontWeight={600}>{schedule.timezone}</Typography>
              </Box>
              <Box>
                <Typography variant="caption" color="text.secondary">Next run</Typography>
                <Typography variant="body2" fontWeight={600}>
                  {schedule.enabled ? formatDateTime(schedule.nextRunAt, schedule.timezone) : "Schedule disabled"}
                </Typography>
              </Box>
              <Box>
                <Typography variant="caption" color="text.secondary">Last run</Typography>
                <Stack direction="row" spacing={1} alignItems="center" useFlexGap flexWrap="wrap">
                  <Typography variant="body2" fontWeight={600}>{formatDateTime(schedule.lastRunAt, schedule.timezone)}</Typography>
                  {schedule.lastRunStatus && <Chip size="small" label={schedule.lastRunStatus} color={getStatusColor(schedule.lastRunStatus)} />}
                </Stack>
              </Box>
            </Stack>
          ) : (
            <Typography variant="body2" color="text.secondary">No schedule configured.</Typography>
          )}
        </Box>

        <Box sx={{ flex: 1 }} />

        <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap" sx={{ mt: 3 }}>
          {canRun && (
            <Button size="small" variant="contained" color="success" startIcon={<RocketLaunchOutlinedIcon />} onClick={() => onRun(integration)} disabled={running || testing || !integration.enabled}>
              {running ? "Running..." : "Run Now"}
            </Button>
          )}

          {canSchedule && (
            <Button size="small" variant="outlined" startIcon={<ScheduleIcon />} onClick={() => onSchedule(integration)} disabled={running}>
              Schedule
            </Button>
          )}

          {canViewHistory && (
            <Button size="small" variant="outlined" startIcon={<HistoryIcon />} onClick={() => onHistory(integration)}>
              History
            </Button>
          )}

          {canTest && (
            <Button size="small" variant="outlined" startIcon={<PlayCircleOutlineIcon />} onClick={() => onTest(integration)} disabled={testing || running}>
              {testing ? "Testing..." : "Test"}
            </Button>
          )}

          {canEdit && (
            <Button size="small" variant="outlined" startIcon={<EditOutlinedIcon />} onClick={() => onEdit(integration)} disabled={running}>
              Edit
            </Button>
          )}

          {canDelete && (
            <Button size="small" color="error" startIcon={<DeleteOutlineIcon />} onClick={() => onDelete(integration)} disabled={running}>
              Delete
            </Button>
          )}
        </Stack>
      </CardContent>
    </Card>
  );
};

export default IntegrationCard;
