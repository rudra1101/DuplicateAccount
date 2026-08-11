import {
  useEffect,
  useState,
} from "react";

import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Stack,
  TextField,
  Typography,
} from "@mui/material";

import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import CancelIcon from "@mui/icons-material/Cancel";
import HelpOutlineIcon from "@mui/icons-material/HelpOutline";
import SaveIcon from "@mui/icons-material/Save";

import {
  type CandidateDecisionResponse,
  type ReviewDecision,
  submitCandidateDecision,
} from "../../services/reviewService";

import { formatDateTime } from "../../utils/dateTime";


interface Props {
  candidateRecordId: number;
  currentDecision?: ReviewDecision | null;
  currentComment?: string | null;
  currentReviewerName?: string | null;
  reviewedAt?: string | null;

  onDecisionSaved?: (
    response: CandidateDecisionResponse,
  ) => void;
}


function getDecisionColor(
  decision: ReviewDecision | null,
): "success" | "error" | "warning" | "default" {
  if (decision === "DUPLICATE") {
    return "success";
  }

  if (decision === "NOT_DUPLICATE") {
    return "error";
  }

  if (decision === "UNCERTAIN") {
    return "warning";
  }

  return "default";
}


function getDecisionLabel(
  decision: ReviewDecision | null,
): string {
  if (decision === "DUPLICATE") {
    return "Confirmed Duplicate";
  }

  if (decision === "NOT_DUPLICATE") {
    return "Keep Separate";
  }

  if (decision === "UNCERTAIN") {
    return "Needs Review";
  }

  return "Not Reviewed";
}


const CandidateDecisionPanel = ({
  candidateRecordId,
  currentDecision = null,
  currentComment = null,
  currentReviewerName = null,
  reviewedAt = null,
  onDecisionSaved,
}: Props) => {
  const [decision, setDecision] =
    useState<ReviewDecision | null>(
      currentDecision,
    );

  const [comment, setComment] =
    useState(currentComment ?? "");

  const [reviewerName, setReviewerName] =
    useState(
      currentReviewerName ?? "Rudra",
    );

  const [savedReviewedAt, setSavedReviewedAt] =
    useState(reviewedAt);

  const [saving, setSaving] =
    useState(false);

  const [error, setError] =
    useState("");

  const [success, setSuccess] =
    useState("");


  useEffect(() => {
    setDecision(currentDecision);
    setComment(currentComment ?? "");
    setReviewerName(
      currentReviewerName ?? "Rudra",
    );
    setSavedReviewedAt(reviewedAt);
  }, [
    currentDecision,
    currentComment,
    currentReviewerName,
    reviewedAt,
  ]);


  const saveDecision = async (
    selectedDecision: ReviewDecision,
  ) => {
    try {
      setSaving(true);
      setError("");
      setSuccess("");

      const response =
        await submitCandidateDecision(
          candidateRecordId,
          {
            decision: selectedDecision,
            comment:
              comment.trim() || null,
            reviewerName:
              reviewerName.trim() || null,
          },
        );

      setDecision(response.decision);
      setComment(response.comment ?? "");
      setReviewerName(
        response.reviewerName ?? "",
      );
      setSavedReviewedAt(
        response.reviewedAt,
      );

      setSuccess(
        "Reviewer decision saved successfully.",
      );

      onDecisionSaved?.(response);
    } catch (saveError) {
      console.error(
        "Failed to save decision:",
        saveError,
      );

      setError(
        saveError instanceof Error
          ? saveError.message
          : "Unable to save decision.",
      );
    } finally {
      setSaving(false);
    }
  };


  return (
    <Card
      sx={{
        borderRadius: 3,
        boxShadow: 2,
      }}
    >
      <CardContent>
        <Stack spacing={3}>
          <Box
            sx={{
              display: "flex",
              justifyContent:
                "space-between",
              alignItems: "center",
              flexWrap: "wrap",
              gap: 1,
            }}
          >
            <Box>
              <Typography
                variant="h6"
                fontWeight={700}
              >
                Reviewer Decision
              </Typography>

              <Typography
                variant="body2"
                color="text.secondary"
              >
                Save your decision and
                automatically add it to the ML
                training dataset.
              </Typography>
            </Box>

            <Chip
              label={getDecisionLabel(
                decision,
              )}
              color={getDecisionColor(
                decision,
              )}
            />
          </Box>

          {error && (
            <Alert severity="error">
              {error}
            </Alert>
          )}

          {success && (
            <Alert severity="success">
              {success}
            </Alert>
          )}

          <TextField
            label="Reviewer Name"
            value={reviewerName}
            onChange={(event) =>
              setReviewerName(
                event.target.value,
              )
            }
            fullWidth
            disabled={saving}
          />

          <TextField
            label="Review Comment"
            value={comment}
            onChange={(event) =>
              setComment(
                event.target.value,
              )
            }
            placeholder="Explain why these accounts should be merged, kept separate, or reviewed further."
            multiline
            minRows={3}
            fullWidth
            disabled={saving}
          />

          <Stack
            direction={{
              xs: "column",
              md: "row",
            }}
            spacing={2}
          >
            <Button
              variant={
                decision === "DUPLICATE"
                  ? "contained"
                  : "outlined"
              }
              color="success"
              startIcon={
                saving
                  ? (
                    <CircularProgress
                      size={18}
                      color="inherit"
                    />
                  )
                  : <CheckCircleIcon />
              }
              onClick={() =>
                saveDecision(
                  "DUPLICATE",
                )
              }
              disabled={saving}
              fullWidth
            >
              Confirm Duplicate
            </Button>

            <Button
              variant={
                decision ===
                "NOT_DUPLICATE"
                  ? "contained"
                  : "outlined"
              }
              color="error"
              startIcon={
                saving
                  ? (
                    <CircularProgress
                      size={18}
                      color="inherit"
                    />
                  )
                  : <CancelIcon />
              }
              onClick={() =>
                saveDecision(
                  "NOT_DUPLICATE",
                )
              }
              disabled={saving}
              fullWidth
            >
              Keep Separate
            </Button>

            <Button
              variant={
                decision === "UNCERTAIN"
                  ? "contained"
                  : "outlined"
              }
              color="warning"
              startIcon={
                saving
                  ? (
                    <CircularProgress
                      size={18}
                      color="inherit"
                    />
                  )
                  : <HelpOutlineIcon />
              }
              onClick={() =>
                saveDecision(
                  "UNCERTAIN",
                )
              }
              disabled={saving}
              fullWidth
            >
              Needs Review
            </Button>
          </Stack>

          {decision && (
            <Alert
              severity={
                decision === "DUPLICATE"
                  ? "success"
                  : decision ===
                      "NOT_DUPLICATE"
                    ? "error"
                    : "warning"
              }
              icon={<SaveIcon />}
            >
              Decision saved as{" "}
              <strong>
                {getDecisionLabel(
                  decision,
                )}
              </strong>
              {savedReviewedAt
                ? ` on ${formatDateTime(
                    savedReviewedAt,
                  )}`
                : ""}
              .
            </Alert>
          )}
        </Stack>
      </CardContent>
    </Card>
  );
};

export default CandidateDecisionPanel;