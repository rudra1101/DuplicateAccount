import { Card, CardContent, Typography, Button, Stack } from "@mui/material";
import ArrowForwardIcon from "@mui/icons-material/ArrowForward";

export interface ApplicationSummary {
  application: string;
  totalAccounts: number;
  duplicateGroups: number;
  duplicateAccounts: number;
  highConfidence: number;
  lastScan: string;
}

interface Props {
  application: ApplicationSummary;
  onView: (application: string) => void;
}

const ApplicationCard = ({ application, onView }: Props) => {
  return (
    <Card
      elevation={2}
      sx={{
        borderRadius: 3,
        height: "100%",
        transition: "0.25s",
        "&:hover": {
          transform: "translateY(-4px)",
          boxShadow: 6,
        },
      }}
    >
      <CardContent>
        <Typography variant="h6" fontWeight={700} gutterBottom>
          {application.application}
        </Typography>

        <Stack spacing={1} sx={{ mt: 3 }}>
          <Typography>
            Accounts
            <strong> {application.totalAccounts.toLocaleString()}</strong>
          </Typography>

          <Typography color="error.main">
            Duplicates
            <strong> {application.duplicateAccounts}</strong>
          </Typography>

          <Typography color="success.main">
            High Confidence
            <strong> {application.highConfidence}</strong>
          </Typography>

          <Typography variant="caption" color="text.secondary">
            Last Scan: {application.lastScan}
          </Typography>
        </Stack>

        <Button
          sx={{ mt: 3 }}
          variant="contained"
          endIcon={<ArrowForwardIcon />}
          fullWidth
          onClick={() => onView(application.application)}
        >
          View Details
        </Button>
      </CardContent>
    </Card>
  );
};

export default ApplicationCard;
