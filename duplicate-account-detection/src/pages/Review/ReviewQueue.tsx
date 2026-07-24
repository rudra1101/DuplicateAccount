import { useEffect, useState } from "react";
import {
  Box,
  CircularProgress,
  Alert,
  Typography,
} from "@mui/material";

import PageContainer from "../../components/common/PageContainer";
import ReviewQueueTable, {
  DuplicateRecord,
} from "../../components/review/ReviewQueueTable";

const ReviewQueue = () => {
  const [data, setData] = useState<DuplicateRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    loadReviewQueue();
  }, []);

  const loadReviewQueue = async () => {
    try {
      setLoading(true);

      const response = await fetch(
        "http://127.0.0.1:8000/api/review/"
      );

      if (!response.ok) {
        throw new Error("Failed to fetch review queue.");
      }

      const result: DuplicateRecord[] = await response.json();

      console.log("Review Queue API:", result);

      setData(result);
    } catch (err) {
      console.error(err);
      setError("Unable to load review queue.");
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <PageContainer title="Review Queue">
        <Box
          display="flex"
          justifyContent="center"
          mt={8}
        >
          <CircularProgress />
        </Box>
      </PageContainer>
    );
  }

  if (error) {
    return (
      <PageContainer title="Review Queue">
        <Alert severity="error">{error}</Alert>
      </PageContainer>
    );
  }

  return (
    <PageContainer title="Review Queue">
      <Typography
        variant="h5"
        sx={{ mb: 3, fontWeight: 700 }}
      >
        Duplicate Review Queue
      </Typography>

      <ReviewQueueTable data={data} />
    </PageContainer>
  );
};

export default ReviewQueue;