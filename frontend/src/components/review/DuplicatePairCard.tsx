import {
  Card,
  CardContent,
  Chip,
  Stack,
  Typography,
} from "@mui/material";

import GroupsOutlinedIcon from "@mui/icons-material/GroupsOutlined";

import type { DuplicateGroup } from "../../services/reviewService";

export type DuplicatePair = DuplicateGroup;

interface Props {
  pair: DuplicatePair;
  selected: boolean;
  onClick: () => void;
}

const getConfidenceColor = (
  confidence: number
): "success" | "warning" | "error" => {
  if (confidence >= 95) {
    return "success";
  }

  if (confidence >= 80) {
    return "warning";
  }

  return "error";
};

const DuplicatePairCard = ({
  pair,
  selected,
  onClick,
}: Props) => {
  return (
    <Card
      onClick={onClick}
      sx={{
        mb: 2,
        cursor: "pointer",
        borderRadius: 3,
        border: selected
          ? "2px solid"
          : "1px solid",
        borderColor: selected
          ? "primary.main"
          : "divider",
        backgroundColor: selected
          ? "action.selected"
          : "background.paper",
        transition: "transform 0.2s, box-shadow 0.2s",
        "&:hover": {
          transform: "translateY(-2px)",
          boxShadow: 4,
        },
      }}
    >
      <CardContent>
        <Stack
          direction="row"
          justifyContent="space-between"
          alignItems="flex-start"
          spacing={2}
        >
          <Typography
            fontWeight={700}
            sx={{ wordBreak: "break-word" }}
          >
            {pair.primaryAccount}
          </Typography>

          <Chip
            label={`${pair.highestConfidence}%`}
            color={getConfidenceColor(
              pair.highestConfidence
            )}
            size="small"
          />
        </Stack>

        <Stack
          direction="row"
          alignItems="center"
          spacing={1}
          mt={2}
        >
          <GroupsOutlinedIcon
            fontSize="small"
            color="action"
          />

          <Typography
            variant="body2"
            color="text.secondary"
          >
            {pair.duplicates} duplicate account
            {pair.duplicates === 1 ? "" : "s"}
          </Typography>
        </Stack>
      </CardContent>
    </Card>
  );
};

export default DuplicatePairCard;