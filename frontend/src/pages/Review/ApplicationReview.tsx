import {
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  Alert,
  Box,
  Breadcrumbs,
  Button,
  Chip,
  CircularProgress,
  FormControl,
  InputAdornment,
  InputLabel,
  Link,
  MenuItem,
  Paper,
  Select,
  Stack,
  TextField,
  Typography,
} from "@mui/material";

import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import RefreshIcon from "@mui/icons-material/Refresh";
import SearchIcon from "@mui/icons-material/Search";
import FilterAltOffIcon from "@mui/icons-material/FilterAltOff";

import {
  Link as RouterLink,
  useNavigate,
  useParams,
  useSearchParams,
} from "react-router-dom";

import PageContainer from "../../components/common/PageContainer";
import DuplicatePairList from "../../components/review/DuplicatePairList";
import AccountComparison from "../../components/review/AccountComparison";
import {
  type DuplicateGroup,
  type DuplicateGroupDetails,
  getDuplicateGroupDetails,
  getDuplicateGroups,
} from "../../services/reviewService";

type ConfidenceFilter = "all" | "95" | "90" | "80" | "70" | "50";
type DuplicateCountFilter = "all" | "1" | "2" | "3";

const WORKSPACE_HEIGHT = "clamp(620px, calc(100dvh - 245px), 860px)";

function parseIntegrationId(value: string | null): number | null {
  if (!value) return null;
  const parsed = Number(value);
  return Number.isInteger(parsed) && parsed > 0 ? parsed : null;
}

const ApplicationReview = () => {
  const navigate = useNavigate();
  const { application } = useParams<{ application: string }>();
  const [searchParams] = useSearchParams();

  const applicationName = application ? decodeURIComponent(application) : "";
  const integrationId = parseIntegrationId(searchParams.get("integrationId"));
  const integrationName = searchParams.get("integrationName");

  const [groups, setGroups] = useState<DuplicateGroup[]>([]);
  const [selectedGroup, setSelectedGroup] = useState<DuplicateGroup | null>(null);
  const [details, setDetails] = useState<DuplicateGroupDetails | null>(null);
  const [loadingGroups, setLoadingGroups] = useState(true);
  const [loadingDetails, setLoadingDetails] = useState(false);
  const [error, setError] = useState("");
  const [detailsError, setDetailsError] = useState("");
  const [searchText, setSearchText] = useState("");
  const [confidenceFilter, setConfidenceFilter] = useState<ConfidenceFilter>("all");
  const [duplicateCountFilter, setDuplicateCountFilter] = useState<DuplicateCountFilter>("all");

  const loadDetails = useCallback(
    async (group: DuplicateGroup) => {
      try {
        setSelectedGroup(group);
        setDetails(null);
        setDetailsError("");
        setLoadingDetails(true);

        const result = await getDuplicateGroupDetails(
          group.groupId,
          group.integrationId ?? integrationId,
        );
        setDetails(result);
      } catch (loadError) {
        console.error("Unable to load duplicate details:", loadError);
        setDetailsError(
          loadError instanceof Error
            ? loadError.message
            : "Unable to load account comparison details.",
        );
      } finally {
        setLoadingDetails(false);
      }
    },
    [integrationId],
  );

  const loadGroups = useCallback(
    async (preferredGroupId?: number | null) => {
      if (!applicationName) {
        setError("Application name is missing.");
        setLoadingGroups(false);
        return;
      }

      try {
        setLoadingGroups(true);
        setError("");
        setDetailsError("");

        const result = await getDuplicateGroups(applicationName, integrationId);
        const validGroups = Array.isArray(result) ? result : [];
        setGroups(validGroups);

        if (validGroups.length === 0) {
          setSelectedGroup(null);
          setDetails(null);
          return;
        }

        const nextGroup =
          (preferredGroupId
            ? validGroups.find((group) => group.groupId === preferredGroupId)
            : null)
          ?? validGroups[0];

        await loadDetails(nextGroup);
      } catch (loadError) {
        console.error("Unable to load duplicate groups:", loadError);
        setError(
          loadError instanceof Error
            ? loadError.message
            : "Unable to load duplicate groups for this application.",
        );
      } finally {
        setLoadingGroups(false);
      }
    },
    [applicationName, integrationId, loadDetails],
  );

  useEffect(() => {
    void loadGroups();
  }, [loadGroups]);

  const handleReviewStateChanged = useCallback(async () => {
    await loadGroups(selectedGroup?.groupId ?? null);
  }, [loadGroups, selectedGroup?.groupId]);

  const filteredGroups = useMemo(() => {
    const search = searchText.trim().toLowerCase();
    const minimumConfidence = confidenceFilter === "all" ? 0 : Number(confidenceFilter);

    return groups.filter((group) => {
      const matchesSearch =
        search === ""
        || group.primaryAccount.toLowerCase().includes(search)
        || String(group.groupId).includes(search);
      const matchesConfidence = group.highestConfidence >= minimumConfidence;

      let matchesDuplicateCount = true;
      if (duplicateCountFilter !== "all") {
        const expectedCount = Number(duplicateCountFilter);
        matchesDuplicateCount =
          duplicateCountFilter === "3"
            ? group.duplicates >= 3
            : group.duplicates === expectedCount;
      }

      return matchesSearch && matchesConfidence && matchesDuplicateCount;
    });
  }, [groups, searchText, confidenceFilter, duplicateCountFilter]);

  useEffect(() => {
    if (
      selectedGroup
      && !filteredGroups.some((group) => group.groupId === selectedGroup.groupId)
    ) {
      setSelectedGroup(null);
      setDetails(null);
    }
  }, [filteredGroups, selectedGroup]);

  const clearFilters = () => {
    setSearchText("");
    setConfidenceFilter("all");
    setDuplicateCountFilter("all");
  };

  const hasActiveFilters =
    searchText.trim() !== ""
    || confidenceFilter !== "all"
    || duplicateCountFilter !== "all";

  const duplicateAccountCount = groups.reduce(
    (total, group) => total + group.duplicates,
    0,
  );
  const highConfidenceCount = groups.filter(
    (group) => group.highestConfidence >= 95,
  ).length;

  const resolvedIntegrationName =
    details?.integrationName
    ?? selectedGroup?.integrationName
    ?? integrationName
    ?? (integrationId ? `Integration #${integrationId}` : "All integrations");

  return (
    <PageContainer title="Review Duplicate Accounts">
      <Breadcrumbs sx={{ mb: 1.5 }}>
        <Link component={RouterLink} to="/review" underline="hover" color="inherit">
          Review Queue
        </Link>
        <Typography color="text.secondary">{resolvedIntegrationName}</Typography>
        <Typography color="text.primary">{applicationName || "Application"}</Typography>
      </Breadcrumbs>

      <Box
        sx={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
          flexWrap: "wrap",
          gap: 2,
          mb: 2,
        }}
      >
        <Box>
          <Typography variant="h5" fontWeight={700}>{applicationName}</Typography>
          <Typography color="text.secondary" sx={{ mt: 0.75 }}>
            Integration: <strong>{resolvedIntegrationName}</strong>
          </Typography>
          <Typography color="text.secondary" sx={{ mt: 0.5 }}>
            Select a duplicate group to compare its primary account with possible duplicate accounts.
          </Typography>

          <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap" sx={{ mt: 1.5 }}>
            <Chip size="small" label={`${groups.length} groups`} variant="outlined" />
            <Chip size="small" label={`${duplicateAccountCount} duplicate accounts`} variant="outlined" />
            <Chip
              size="small"
              color="success"
              label={`${highConfidenceCount} high confidence`}
              variant="outlined"
            />
            {integrationId && (
              <Chip size="small" label={`Integration #${integrationId}`} variant="outlined" />
            )}
          </Stack>
        </Box>

        <Stack direction="row" spacing={1}>
          <Button
            variant="outlined"
            startIcon={<ArrowBackIcon />}
            onClick={() => navigate("/review")}
          >
            Back
          </Button>
          <Button
            variant="outlined"
            startIcon={<RefreshIcon />}
            onClick={() => void loadGroups(selectedGroup?.groupId ?? null)}
            disabled={loadingGroups || loadingDetails}
          >
            Refresh
          </Button>
        </Stack>
      </Box>

      <Paper variant="outlined" sx={{ p: 2, borderRadius: 3, mb: 2 }}>
        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: {
              xs: "1fr",
              sm: "1fr 1fr",
              lg: "minmax(280px, 2fr) 1fr 1fr auto",
            },
            gap: 2,
            alignItems: "center",
          }}
        >
          <TextField
            fullWidth
            size="small"
            label="Search primary account"
            placeholder="Username or group ID"
            value={searchText}
            onChange={(event) => setSearchText(event.target.value)}
            slotProps={{
              input: {
                startAdornment: (
                  <InputAdornment position="start"><SearchIcon /></InputAdornment>
                ),
              },
            }}
          />

          <FormControl fullWidth size="small">
            <InputLabel>Confidence</InputLabel>
            <Select<ConfidenceFilter>
              label="Confidence"
              value={confidenceFilter}
              onChange={(event) => setConfidenceFilter(event.target.value)}
            >
              <MenuItem value="all">All confidence</MenuItem>
              <MenuItem value="95">95% and above</MenuItem>
              <MenuItem value="90">90% and above</MenuItem>
              <MenuItem value="80">80% and above</MenuItem>
              <MenuItem value="70">70% and above</MenuItem>
              <MenuItem value="50">50% and above</MenuItem>
            </Select>
          </FormControl>

          <FormControl fullWidth size="small">
            <InputLabel>Group Size</InputLabel>
            <Select<DuplicateCountFilter>
              label="Group Size"
              value={duplicateCountFilter}
              onChange={(event) => setDuplicateCountFilter(event.target.value)}
            >
              <MenuItem value="all">All sizes</MenuItem>
              <MenuItem value="1">1 duplicate</MenuItem>
              <MenuItem value="2">2 duplicates</MenuItem>
              <MenuItem value="3">3 or more</MenuItem>
            </Select>
          </FormControl>

          <Button
            color="inherit"
            title="Clear filters"
            onClick={clearFilters}
            disabled={!hasActiveFilters}
            sx={{ minWidth: 44, height: 40 }}
          >
            <FilterAltOffIcon />
          </Button>
        </Box>

        <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 1.5 }}>
          Showing {filteredGroups.length} of {groups.length} groups
        </Typography>
      </Paper>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      {loadingGroups ? (
        <Box sx={{ minHeight: 500, display: "flex", justifyContent: "center", alignItems: "center" }}>
          <CircularProgress />
        </Box>
      ) : groups.length === 0 ? (
        <Alert severity="info">
          No duplicate groups were found for {applicationName} in {resolvedIntegrationName}.
        </Alert>
      ) : (
        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: { xs: "1fr", lg: "300px minmax(0, 1fr)" },
            gap: 2,
            width: "100%",
            height: { xs: "auto", lg: WORKSPACE_HEIGHT },
            minHeight: 0,
            alignItems: "stretch",
            overflow: { xs: "visible", lg: "hidden" },
          }}
        >
          <Paper
            variant="outlined"
            sx={{
              width: "100%",
              height: { xs: 560, lg: "100%" },
              minHeight: 0,
              boxSizing: "border-box",
              borderRadius: 3,
              display: "flex",
              flexDirection: "column",
              overflow: "hidden",
            }}
          >
            <Box
              sx={{
                px: 2,
                py: 1.75,
                borderBottom: 1,
                borderColor: "divider",
                flexShrink: 0,
                backgroundColor: "background.paper",
              }}
            >
              <Typography variant="h6" fontWeight={700}>Duplicate Groups</Typography>
              <Typography variant="caption" color="text.secondary">Select a group to review</Typography>
            </Box>

            <Box sx={{ flex: 1, minHeight: 0, overflowY: "auto", overflowX: "hidden", p: 1.5 }}>
              {filteredGroups.length === 0 ? (
                <Alert severity="info">No groups match the selected filters.</Alert>
              ) : (
                <DuplicatePairList
                  pairs={filteredGroups}
                  selectedId={selectedGroup?.groupId ?? null}
                  onSelect={loadDetails}
                />
              )}
            </Box>
          </Paper>

          <Box
            sx={{
              width: "100%",
              height: { xs: "auto", lg: "100%" },
              minWidth: 0,
              minHeight: 0,
              display: "flex",
              overflow: { xs: "visible", lg: "hidden" },
            }}
          >
            {detailsError ? (
              <Alert severity="error" sx={{ width: "100%" }}>{detailsError}</Alert>
            ) : loadingDetails ? (
              <Paper
                variant="outlined"
                sx={{
                  width: "100%",
                  height: "100%",
                  minHeight: 500,
                  borderRadius: 3,
                  display: "flex",
                  justifyContent: "center",
                  alignItems: "center",
                }}
              >
                <CircularProgress />
              </Paper>
            ) : (
              <AccountComparison
                pair={selectedGroup}
                details={details}
                onReviewStateChanged={handleReviewStateChanged}
              />
            )}
          </Box>
        </Box>
      )}
    </PageContainer>
  );
};

export default ApplicationReview;
