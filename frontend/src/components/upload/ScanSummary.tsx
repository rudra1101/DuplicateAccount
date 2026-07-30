import {
  Grid,
  Card,
  CardContent,
  Typography,
  Box,
  Chip,
  Button,
} from "@mui/material";

import GroupsIcon from "@mui/icons-material/Groups";
import AppsIcon from "@mui/icons-material/Apps";
import BadgeIcon from "@mui/icons-material/Badge";
import VerifiedIcon from "@mui/icons-material/Verified";
import TimerIcon from "@mui/icons-material/Timer";
import ArrowForwardIcon from "@mui/icons-material/ArrowForward";

interface Props {
  summary: any;
  onReview: () => void;
}

const cards = [
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

export default function ScanSummary({
  summary,
  onReview,
}: Props) {
  return (
    <Box mt={5}>

      <Box
        display="flex"
        justifyContent="space-between"
        alignItems="center"
        mb={3}
      >
        <Typography variant="h5" fontWeight={700}>
          Scan Summary
        </Typography>

        <Chip
          color="success"
          label="Completed"
        />
      </Box>

      <Grid container spacing={3}>

        {cards.map((card) => (

          <Grid size={{ xs: 12, md: 3 }} key={card.title}>

            <Card
              sx={{
                borderRadius: 3,
                height: "100%",
              }}
            >
              <CardContent>

                {card.icon}

                <Typography
                  mt={2}
                  color="text.secondary"
                >
                  {card.title}
                </Typography>

                <Typography
                  variant="h4"
                  fontWeight={700}
                >
                  {summary[card.key]}
                </Typography>

              </CardContent>
            </Card>

          </Grid>

        ))}

      </Grid>

      <Card
        sx={{
          mt: 4,
          borderRadius: 3,
        }}
      >
        <CardContent>

          <Box
            display="flex"
            justifyContent="space-between"
            alignItems="center"
            flexWrap="wrap"
            gap={2}
          >

            <Box>

              <Typography
                variant="h6"
                fontWeight={700}
              >
                Scan Completed Successfully
              </Typography>

              <Box
                display="flex"
                alignItems="center"
                gap={1}
                mt={1}
              >
                <TimerIcon fontSize="small" />

                <Typography color="text.secondary">
                  Last Scan:
                  {" "}
                  {summary.lastScan
                    ? new Date(summary.lastScan).toLocaleString()
                    : "-"}
                </Typography>

              </Box>

            </Box>

            <Button
              variant="contained"
              endIcon={<ArrowForwardIcon />}
              onClick={onReview}
            >
              Review Duplicate Accounts
            </Button>

          </Box>

        </CardContent>
      </Card>

    </Box>
  );
}