import { Card, CardContent, Typography } from "@mui/material";

interface KpiCardProps {
  title: string;
  value: string | number;
  color?: string;
}

const KpiCard = ({
  title,
  value,
  color = "#1976d2",
}: KpiCardProps) => {
  return (
    <Card
      elevation={3}
      sx={{
        borderRadius: 3,
        borderLeft: `6px solid ${color}`,
        minHeight: 120,
      }}
    >
      <CardContent>
        <Typography
          variant="body2"
          color="text.secondary"
        >
          {title}
        </Typography>

        <Typography
          variant="h4"
          sx={{
            mt: 2,
            fontWeight: 700,
          }}
        >
          {value}
        </Typography>
      </CardContent>
    </Card>
  );
};

export default KpiCard;
