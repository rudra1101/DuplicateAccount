import {
  Box,
  Card,
  CardContent,
  Chip,
  Stack,
  Typography,
} from "@mui/material";

import PersonSearchIcon from "@mui/icons-material/PersonSearch";

import type {
  DuplicateCandidate,
} from "../../services/reviewService";

interface Props {
  candidates: DuplicateCandidate[];
  selectedCandidateId: number | null;
  onSelect: (candidate: DuplicateCandidate) => void;
}

const getConfidenceColor = (
  confidence: number
): "success" | "warning" | "error" => {
  if (confidence >= 95) {
    return "success";
  }

  if (confidence >= 80) {
    return "warning";
  }

  return "error";
};

const DuplicateCandidateList = ({
  candidates,
  selectedCandidateId,
  onSelect,
}: Props) => {
  if (candidates.length === 0) {
    return (
      <Typography color="text.secondary">
        No duplicate candidates found.
      </Typography>
    );
  }

  return (
    <Box>
      <Typography
        variant="subtitle2"
        color="text.secondary"
        sx={{ mb: 2 }}
      >
        {candidates.length} possible duplicate
        {candidates.length === 1 ? "" : "s"}
      </Typography>

      <Stack spacing={1.5}>
        {candidates.map((candidate) => {
          const selected =
            selectedCandidateId === candidate.id;

          return (
            <Card
              key={candidate.id}
              variant="outlined"
              onClick={() => onSelect(candidate)}
              sx={{
                cursor: "pointer",
                borderRadius: 2,
                borderWidth: selected ? 2 : 1,
                borderColor: selected
                  ? "primary.main"
                  : "divider",
                backgroundColor: selected
                  ? "action.selected"
                  : "background.paper",
                transition:
                  "transform 0.2s, box-shadow 0.2s",
                "&:hover": {
                  transform: "translateY(-2px)",
                  boxShadow: 2,
                },
              }}
            >
              <CardContent
                sx={{
                  "&:last-child": {
                    pb: 2,
                  },
                }}
              >
                <Stack
                  direction="row"
                  justifyContent="space-between"
                  alignItems="flex-start"
                  spacing={2}
                >
                  <Stack
                    direction="row"
                    spacing={1.5}
                    alignItems="center"
                  >
                    <PersonSearchIcon
                      color={
                        selected
                          ? "primary"
                          : "action"
                      }
                    />

                    <Box>
                      <Typography fontWeight={700}>
                        {candidate.account.username}
                      </Typography>

                      <Typography
                        variant="body2"
                        color="text.secondary"
                      >
                        {candidate.account.displayName ||
                          "Display name unavailable"}
                      </Typography>
                    </Box>
                  </Stack>

                  <Chip
                    label={`${candidate.confidence}%`}
                    color={getConfidenceColor(
                      candidate.confidence
                    )}
                    size="small"
                  />
                </Stack>

                <Stack
                  direction="row"
                  spacing={1}
                  sx={{ mt: 2 }}
                >
                  <Chip
                    label={candidate.recommendation}
                    color={
                      candidate.recommendation ===
                      "MERGE"
                        ? "success"
                        : "warning"
                    }
                    variant="outlined"
                    size="small"
                  />

                  <Chip
                    label={`${candidate.matchedAttributes.length} matches`}
                    variant="outlined"
                    size="small"
                  />
                </Stack>
              </CardContent>
            </Card>
          );
        })}
      </Stack>
    </Box>
  );
};

export default DuplicateCandidateList;