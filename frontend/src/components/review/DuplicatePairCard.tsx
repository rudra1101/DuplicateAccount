import { Card, CardContent, Typography, Chip, Stack } from "@mui/material";

export interface DuplicatePair {
  id: number;
  account1: string;
  account2: string;
  confidence: number;
}

interface Props {
  pair: DuplicatePair;
  selected: boolean;
  onClick: () => void;
}

const DuplicatePairCard = ({ pair, selected, onClick }: Props) => {
  return (
    <Card
      onClick={onClick}
      sx={{
        mb: 2,
        cursor: "pointer",
        borderRadius: 2,
        border: selected ? "2px solid #1976d2" : "1px solid #e0e0e0",
        transition: "0.2s",
        "&:hover": {
          boxShadow: 4,
        },
      }}
    >
      <CardContent>
        <Stack
          direction="row"
          justifyContent="space-between"
          alignItems="center"
        >
          <Typography fontWeight={600}>{pair.account1}</Typography>

          <Chip
            label={`${pair.confidence}%`}
            color={
              pair.confidence >= 90
                ? "success"
                : pair.confidence >= 80
                  ? "warning"
                  : "default"
            }
            size="small"
          />
        </Stack>

        <Typography variant="body2" color="text.secondary" mt={1}>
          ↔ {pair.account2}
        </Typography>
      </CardContent>
    </Card>
  );
};

export default DuplicatePairCard;
