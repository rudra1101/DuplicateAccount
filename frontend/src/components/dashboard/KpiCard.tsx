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
      elevation={2}
      sx={{
        borderRadius: 3,
        minHeight: 120,
        border: `1px solid ${color}55`,
        borderTop: `5px solid ${color}`,
        background: `linear-gradient(135deg, ${color}12 0%, ${color}2E 100%)`,
        transition: "transform 0.2s ease, box-shadow 0.2s ease",
        "&:hover": {
          transform: "translateY(-2px)",
          boxShadow: 4,
        },
      }}
    >
      <CardContent>
        <Typography
          variant="body2"
          sx={{
            color: "text.secondary",
            fontWeight: 600,
          }}
        >
          {title}
        </Typography>

        <Typography
          variant="h4"
          sx={{
            mt: 2,
            fontWeight: 800,
            color,
          }}
        >
          {value}
        </Typography>
      </CardContent>
    </Card>
  );
};

export default KpiCard;
