import { useEffect, useState } from "react";

import {
  Alert,
  Box,
  Button,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Grid,
  Snackbar,
  Typography,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import { useNavigate } from "react-router-dom";

import { useAuth } from "../../auth/AuthContext";
import PageContainer from "../../components/common/PageContainer";
import IntegrationCard from "../../components/integrations/IntegrationCard";
import ScheduleDialog from "../../components/integrations/ScheduleDialog";
import ExecutionHistoryDrawer from "../../components/integrations/ExecutionHistoryDrawer";
import {
  deleteIntegration,
  getIntegrationSchedule,
  getIntegrations,
  runIntegration,
  testIntegration,
  type Integration,
  type JobSchedule,
} from "../../services/integrationService";

const Integrations = () => {
  const navigate = useNavigate();
  const { isAdmin } = useAuth();

  const [integrations, setIntegrations] = useState<Integration[]>([]);
  const [schedules, setSchedules] = useState<Record<number, JobSchedule | null>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [testingId, setTestingId] = useState<number | null>(null);
  const [runningId, setRunningId] = useState<number | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<Integration | null>(null);
  const [scheduleTarget, setScheduleTarget] = useState<Integration | null>(null);
  const [historyTarget, setHistoryTarget] = useState<Integration | null>(null);
  const [message, setMessage] = useState("");
  const [messageType, setMessageType] = useState<"success" | "error">("success");

  const loadIntegrations = async () => {
    try {
      setLoading(true);
      setError("");
      const data = await getIntegrations();
      setIntegrations(data);

      const scheduleResults = await Promise.all(
        data.map(async (integration) => {
          try {
            return {
              integrationId: integration.id,
              schedule: await getIntegrationSchedule(integration.id),
            };
          } catch {
            return { integrationId: integration.id, schedule: null };
          }
        }),
      );

      const scheduleMap: Record<number, JobSchedule | null> = {};
      scheduleResults.forEach((result) => {
        scheduleMap[result.integrationId] = result.schedule;
      });
      setSchedules(scheduleMap);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Unable to load integrations.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadIntegrations();
  }, []);

  const handleTest = async (integration: Integration) => {
    if (!isAdmin) return;

    try {
      setTestingId(integration.id);
      const result = await testIntegration(integration.id);
      setMessage(result.message);
      setMessageType(result.success ? "success" : "error");
    } catch (testError) {
      setMessage(testError instanceof Error ? testError.message : "Connection test failed.");
      setMessageType("error");
    } finally {
      setTestingId(null);
    }
  };

  const handleRun = async (integration: Integration) => {
    try {
      setRunningId(integration.id);
      const result = await runIntegration(integration.id);
      setMessage(
        `${result.sourceFileName ?? "File"} processed successfully. ` +
          `${result.accountsScanned.toLocaleString()} accounts scanned, ` +
          `${result.duplicateGroups.toLocaleString()} duplicate groups found.`,
      );
      setMessageType("success");

      try {
        const updatedSchedule = await getIntegrationSchedule(integration.id);
        setSchedules((current) => ({ ...current, [integration.id]: updatedSchedule }));
      } catch {
        // An integration can be run without a schedule.
      }
    } catch (runError) {
      setMessage(runError instanceof Error ? runError.message : "Integration execution failed.");
      setMessageType("error");
    } finally {
      setRunningId(null);
    }
  };

  const confirmDelete = async () => {
    if (!isAdmin || !deleteTarget) return;

    try {
      await deleteIntegration(deleteTarget.id);
      setIntegrations((current) => current.filter((item) => item.id !== deleteTarget.id));
      setSchedules((current) => {
        const updated = { ...current };
        delete updated[deleteTarget.id];
        return updated;
      });
      setMessage("Integration deleted successfully.");
      setMessageType("success");
    } catch (deleteError) {
      setMessage(deleteError instanceof Error ? deleteError.message : "Unable to delete integration.");
      setMessageType("error");
    } finally {
      setDeleteTarget(null);
    }
  };

  const handleScheduleSaved = (integrationId: number, schedule: JobSchedule | null) => {
    setSchedules((current) => ({ ...current, [integrationId]: schedule }));
    setMessage(schedule ? "Schedule saved successfully." : "Schedule deleted successfully.");
    setMessageType("success");
  };

  return (
    <PageContainer title="Integrations">
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
            File Integrations
          </Typography>
          <Typography color="text.secondary" sx={{ mt: 1 }}>
            Run and schedule configured account-source integrations.
          </Typography>
        </Box>

        {isAdmin && (
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => navigate("/integrations/new")}
          >
            Add Integration
          </Button>
        )}
      </Box>

      {error && <Alert severity="error" sx={{ mb: 3 }}>{error}</Alert>}

      {loading ? (
        <Box sx={{ minHeight: 350, display: "flex", justifyContent: "center", alignItems: "center" }}>
          <CircularProgress />
        </Box>
      ) : integrations.length === 0 ? (
        <Alert severity="info">No integrations are configured yet.</Alert>
      ) : (
        <Grid container spacing={3}>
          {integrations.map((integration) => (
            <Grid
              key={integration.id}
              size={{ xs: 12, md: 6, xl: 4 }}
              sx={{ minWidth: 0, display: "flex" }}
            >
              <IntegrationCard
                integration={integration}
                schedule={schedules[integration.id]}
                testing={testingId === integration.id}
                running={runningId === integration.id}
                canManage={isAdmin}
                onRun={handleRun}
                onTest={handleTest}
                onSchedule={setScheduleTarget}
                onHistory={setHistoryTarget}
                onEdit={(item) => navigate(`/integrations/${item.id}/edit`)}
                onDelete={setDeleteTarget}
              />
            </Grid>
          ))}
        </Grid>
      )}

      <ScheduleDialog
        open={Boolean(scheduleTarget)}
        integration={scheduleTarget}
        onClose={() => setScheduleTarget(null)}
        onSaved={handleScheduleSaved}
      />

      <ExecutionHistoryDrawer
        open={Boolean(historyTarget)}
        integration={historyTarget}
        schedule={historyTarget ? schedules[historyTarget.id] : null}
        onClose={() => setHistoryTarget(null)}
      />

      {isAdmin && (
        <Dialog open={Boolean(deleteTarget)} onClose={() => setDeleteTarget(null)}>
          <DialogTitle>Delete Integration</DialogTitle>
          <DialogContent>
            Are you sure you want to delete <strong>{deleteTarget?.name}</strong>?
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setDeleteTarget(null)}>Cancel</Button>
            <Button color="error" variant="contained" onClick={confirmDelete}>
              Delete
            </Button>
          </DialogActions>
        </Dialog>
      )}

      <Snackbar open={Boolean(message)} autoHideDuration={5000} onClose={() => setMessage("")}>
        <Alert
          severity={messageType}
          onClose={() => setMessage("")}
          variant="filled"
        >
          {message}
        </Alert>
      </Snackbar>
    </PageContainer>
  );
};

export default Integrations;
