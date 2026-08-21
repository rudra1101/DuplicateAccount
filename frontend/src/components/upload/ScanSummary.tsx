import {
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Grid,
  Typography,
} from "@mui/material";

import GroupsIcon from "@mui/icons-material/Groups";
import AppsIcon from "@mui/icons-material/Apps";
import BadgeIcon from "@mui/icons-material/Badge";
import VerifiedIcon from "@mui/icons-material/Verified";
import TimerIcon from "@mui/icons-material/Timer";
import ArrowForwardIcon from "@mui/icons-material/ArrowForward";
import { formatDateTime } from "../../utils/dateTime";

export interface ScanSummaryData {
  accountsScanned: number;
  applications: number;
  duplicateGroups: number;
  duplicateAccounts: number;
  highConfidence: number;
  lastScan: string | null;
}

interface Props {
  summary: ScanSummaryData;
  onReview: () => void;
}

type SummaryKey =
  | "accountsScanned"
  | "applications"
  | "duplicateGroups"
  | "highConfidence";

interface SummaryCard {
  title: string;
  key: SummaryKey;
  icon: React.ReactNode;
}

const cards: SummaryCard[] = [
  {
    title: "Accounts Uploaded",
    key: "accountsScanned",
    icon: <GroupsIcon color="primary" />,
  },
  {
    title: "Applications",
    key: "applications",
    icon: <AppsIcon color="secondary" />,
  },
  {
    title: "Duplicate Groups",
    key: "duplicateGroups",
    icon: <BadgeIcon color="warning" />,
  },
  {
    title: "High Confidence",
    key: "highConfidence",
    icon: <VerifiedIcon color="success" />,
  },
];

const ScanSummary = ({
  summary,
  onReview,
}: Props) => {
  return (
    <Box sx={{ mt: 5 }}>
      <Box
        sx={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: 2,
          mb: 3,
        }}
      >
        <Typography variant="h5" fontWeight={700}>
          Scan Summary
        </Typography>

        <Chip
          color="success"
          label="Completed"
          size="small"
        />
      </Box>

      <Grid container spacing={3}>
        {cards.map((card) => (
          <Grid
            key={card.key}
            size={{
              xs: 12,
              sm: 6,
              lg: 3,
            }}
          >
            <Card
              variant="outlined"
              sx={{
                borderRadius: 3,
                height: "100%",
              }}
            >
              <CardContent>
                <Box
                  sx={{
                    width: 42,
                    height: 42,
                    borderRadius: 2,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    backgroundColor: "action.hover",
                    mb: 2,
                  }}
                >
                  {card.icon}
                </Box>

                <Typography
                  variant="body2"
                  color="text.secondary"
                >
                  {card.title}
                </Typography>

                <Typography
                  variant="h4"
                  fontWeight={700}
                  sx={{ mt: 0.5 }}
                >
                  {Number(
                    summary[card.key] ?? 0
                  ).toLocaleString()}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      <Card
        variant="outlined"
        sx={{
          mt: 4,
          borderRadius: 3,
        }}
      >
        <CardContent>
          <Box
            sx={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: {
                xs: "flex-start",
                sm: "center",
              },
              flexDirection: {
                xs: "column",
                sm: "row",
              },
              gap: 3,
            }}
          >
            <Box>
              <Typography
                variant="h6"
                fontWeight={700}
              >
                Scan Completed Successfully
              </Typography>

              <Box
                sx={{
                  display: "flex",
                  alignItems: "center",
                  gap: 1,
                  mt: 1,
                }}
              >
                <TimerIcon
                  fontSize="small"
                  color="action"
                />

                <Typography
                  variant="body2"
                  color="text.secondary"
                >
                  Last Scan:{" "}
                  {summary.lastScan
                    ? formatDateTime(summary.lastScan)
                    : "Not available"}
                </Typography>
              </Box>

              <Typography
                variant="body2"
                color="text.secondary"
                sx={{ mt: 1 }}
              >
                {Number(
                  summary.duplicateAccounts ?? 0
                ).toLocaleString()}{" "}
                possible duplicate accounts detected.
              </Typography>
            </Box>

            <Button
              variant="contained"
              endIcon={<ArrowForwardIcon />}
              onClick={onReview}
              disabled={
                summary.duplicateGroups === 0
              }
            >
              Review Duplicate Accounts
            </Button>
          </Box>
        </CardContent>
      </Card>
    </Box>
  );
};

export default ScanSummary;
