import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import {
  Grid,
  Typography,
  CircularProgress,
  Box,
} from "@mui/material";

import DuplicatePairList from "../../components/review/DuplicatePairList";
import AccountComparison from "../../components/review/AccountComparison";

import { DuplicatePair } from "../../components/review/DuplicatePairCard";

import {
  getDuplicatePairs,
  getDuplicateDetails,
} from "../../api/reviewApi";

const ApplicationDetails = () => {
  const { application } = useParams();

  const [loadingPairs, setLoadingPairs] = useState(true);
  const [loadingDetails, setLoadingDetails] = useState(false);

  const [pairs, setPairs] = useState<DuplicatePair[]>([]);
  const [selectedPair, setSelectedPair] =
    useState<DuplicatePair | null>(null);

  const [details, setDetails] = useState<any>(null);

  // Load duplicate pairs for selected application
  useEffect(() => {
    if (!application) return;

    setLoadingPairs(true);

    getDuplicatePairs(application)
      .then((data) => {
        setPairs(data);

        // Auto-select first pair
        if (data.length > 0) {
          setSelectedPair(data[0]);
        }
      })
      .catch((err) => {
        console.error(err);
      })
      .finally(() => {
        setLoadingPairs(false);
      });
  }, [application]);

  // Load selected pair details
  useEffect(() => {
    if (!selectedPair) return;

    setLoadingDetails(true);

    getDuplicateDetails(selectedPair.groupId)
      .then((data) => {
        setDetails(data);
      })
      .catch((err) => {
        console.error(err);
      })
      .finally(() => {
        setLoadingDetails(false);
      });
  }, [selectedPair]);

  return (
    <>
      <Typography
        variant="h4"
        fontWeight={700}
        mb={4}
      >
        {application}
      </Typography>

      <Grid container spacing={3}>

        {/* LEFT PANEL */}

        <Grid size={{ xs: 12, md: 4 }}>
          {loadingPairs ? (
            <Box
              display="flex"
              justifyContent="center"
              mt={10}
            >
              <CircularProgress />
            </Box>
          ) : (
            <DuplicatePairList
              pairs={pairs}
              selectedId={selectedPair?.groupId ?? null}
              onSelect={setSelectedPair}
            />
          )}
        </Grid>

        {/* RIGHT PANEL */}

        <Grid size={{ xs: 12, md: 8 }}>
          {loadingDetails ? (
            <Box
              display="flex"
              justifyContent="center"
              mt={10}
            >
              <CircularProgress />
            </Box>
          ) : (
            <AccountComparison
              pair={selectedPair}
              details={details}
            />
          )}
        </Grid>

      </Grid>
    </>
  );
};

export default ApplicationDetails;