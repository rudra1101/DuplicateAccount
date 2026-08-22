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

import {
  type CandidateDecisionResponse,
  type ReviewDecision,
  submitCandidateDecision,
} from "../../services/reviewService";

import {
  formatDateTime,
} from "../../utils/dateTime";


const BASE_URL = "http://127.0.0.1:8000/api";


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


function getDecisionLabel(
  decision: ReviewDecision | null,
): string {
  if (decision === "DUPLICATE") {
    return "Confirmed Duplicate";
  }

  if (decision === "NOT_DUPLICATE") {
    return "Not Duplicate";
  }

  if (decision === "UNCERTAIN") {
    return "Uncertain";
  }

  return "Not Reviewed";
}


function getDecisionColor(
  decision: ReviewDecision | null,
):
  | "success"
  | "error"
  | "warning"
  | "default" {
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


const CandidateDecisionPanel = ({
  candidateRecordId,
  currentDecision = null,
  currentComment = null,
  currentReviewerName = null,
  reviewedAt = null,
  onDecisionSaved,
}: Props) => {
  const [
    decision,
    setDecision,
  ] = useState<ReviewDecision | null>(
    currentDecision,
  );

  const [
    comment,
    setComment,
  ] = useState(
    currentComment ?? "",
  );

  const [
    reviewerName,
    setReviewerName,
  ] = useState(
    currentReviewerName ?? "Rudra",
  );

  const [
    savedReviewedAt,
    setSavedReviewedAt,
  ] = useState<string | null>(
    reviewedAt,
  );

  const [
    savingDecision,
    setSavingDecision,
  ] = useState<ReviewDecision | null>(
    null,
  );

  const [
    error,
    setError,
  ] = useState("");

  const [
    success,
    setSuccess,
  ] = useState("");


  useEffect(() => {
    setDecision(
      currentDecision,
    );

    setComment(
      currentComment ?? "",
    );

    setReviewerName(
      currentReviewerName
      ?? "Rudra",
    );

    setSavedReviewedAt(
      reviewedAt,
    );

    setError("");
    setSuccess("");
  }, [
    candidateRecordId,
    currentDecision,
    currentComment,
    currentReviewerName,
    reviewedAt,
  ]);


  useEffect(() => {
    let cancelled = false;

    const loadDurableDecision = async () => {
      try {
        const response = await fetch(
          `${BASE_URL}/review/candidates/${candidateRecordId}/durable-decision`,
        );

        if (!response.ok) {
          return;
        }

        const result = await response.json() as {
          decision?: ReviewDecision | null;
        };

        if (
          !cancelled
          && result.decision
        ) {
          setDecision(
            result.decision,
          );
        }
      } catch (loadError) {
        console.warn(
          "Unable to load durable reviewer decision:",
          loadError,
        );
      }
    };

    void loadDurableDecision();

    return () => {
      cancelled = true;
    };
  }, [candidateRecordId]);


  const saveDecision = async (
    selectedDecision: ReviewDecision,
  ) => {
    try {
      setSavingDecision(
        selectedDecision,
      );

      setError("");
      setSuccess("");

      const response =
        await submitCandidateDecision(
          candidateRecordId,
          {
            decision:
              selectedDecision,

            comment:
              comment.trim()
                || null,

            reviewerName:
              reviewerName.trim()
                || null,
          },
        );

      setDecision(
        response.decision,
      );

      setComment(
        response.comment ?? "",
      );

      setReviewerName(
        response.reviewerName
        ?? "",
      );

      setSavedReviewedAt(
        response.reviewedAt,
      );

      setSuccess(
        "Reviewer decision saved successfully.",
      );

      onDecisionSaved?.(
        response,
      );
    } catch (saveError) {
      console.error(
        "Unable to save reviewer decision:",
        saveError,
      );

      setError(
        saveError instanceof Error
          ? saveError.message
          : "Unable to save reviewer decision.",
      );
    } finally {
      setSavingDecision(
        null,
      );
    }
  };


  return (
    <Card
      variant="outlined"
      sx={{
        borderRadius: 3,
      }}
    >
      <CardContent>
        <Stack spacing={2.5}>
          <Box
            sx={{
              display: "flex",
              justifyContent:
                "space-between",
              alignItems: "center",
              flexWrap: "wrap",
              gap: 1.5,
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
                sx={{ mt: 0.5 }}
              >
                Save the reviewer decision
                and add it to the ML
                training dataset.
              </Typography>
            </Box>

            <Chip
              label={
                getDecisionLabel(
                  decision,
                )
              }
              color={
                getDecisionColor(
                  decision,
                )
              }
              variant={
                decision
                  ? "filled"
                  : "outlined"
              }
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
            size="small"
            disabled={
              savingDecision !== null
            }
          />

          <TextField
            label="Review Comment"
            value={comment}
            onChange={(event) =>
              setComment(
                event.target.value,
              )
            }
            placeholder="Explain why the accounts should be confirmed as duplicates, marked not duplicate, or left uncertain."
            multiline
            minRows={3}
            fullWidth
            disabled={
              savingDecision !== null
            }
          />

          <Stack
            direction={{
              xs: "column",
              md: "row",
            }}
            spacing={1.5}
          >
            <Button
              variant={
                decision === "DUPLICATE"
                  ? "contained"
                  : "outlined"
              }
              color="success"
              startIcon={
                savingDecision
                === "DUPLICATE"
                  ? (
                    <CircularProgress
                      size={18}
                      color="inherit"
                    />
                  )
                  : (
                    <CheckCircleIcon />
                  )
              }
              disabled={
                savingDecision !== null
                || decision === "DUPLICATE"
              }
              onClick={() =>
                saveDecision(
                  "DUPLICATE",
                )
              }
              fullWidth
            >
              Confirm Duplicate
            </Button>

            <Button
              variant={
                decision
                === "NOT_DUPLICATE"
                  ? "contained"
                  : "outlined"
              }
              color="error"
              startIcon={
                savingDecision
                === "NOT_DUPLICATE"
                  ? (
                    <CircularProgress
                      size={18}
                      color="inherit"
                    />
                  )
                  : (
                    <CancelIcon />
                  )
              }
              disabled={
                savingDecision !== null
                || decision === "NOT_DUPLICATE"
              }
              onClick={() =>
                saveDecision(
                  "NOT_DUPLICATE",
                )
              }
              fullWidth
            >
              Not Duplicate
            </Button>

            <Button
              variant={
                decision === "UNCERTAIN"
                  ? "contained"
                  : "outlined"
              }
              color="warning"
              startIcon={
                savingDecision
                === "UNCERTAIN"
                  ? (
                    <CircularProgress
                      size={18}
                      color="inherit"
                    />
                  )
                  : (
                    <HelpOutlineIcon />
                  )
              }
              disabled={
                savingDecision !== null
                || decision === "UNCERTAIN"
              }
              onClick={() =>
                saveDecision(
                  "UNCERTAIN",
                )
              }
              fullWidth
            >
              Uncertain
            </Button>
          </Stack>

          {decision && (
            <Alert
              severity={
                decision === "DUPLICATE"
                  ? "success"
                  : decision
                    === "NOT_DUPLICATE"
                    ? "error"
                    : "warning"
              }
            >
              Decision saved as{" "}
              <strong>
                {getDecisionLabel(
                  decision,
                )}
              </strong>

              {savedReviewedAt
                ? (
                  <>
                    {" "}
                    on{" "}
                    {formatDateTime(
                      savedReviewedAt,
                    )}
                  </>
                )
                : null}
              .
            </Alert>
          )}
        </Stack>
      </CardContent>
    </Card>
  );
};


export default CandidateDecisionPanel;
