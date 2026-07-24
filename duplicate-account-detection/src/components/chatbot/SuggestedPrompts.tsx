import {
  Stack,
  Chip,
} from "@mui/material";

interface Props {
  onSelect: (prompt: string) => void;
}

const prompts = [
  "Find duplicate accounts",
  "Explain AI confidence",
  "Generate audit report",
  "Show AD duplicates",
];

const SuggestedPrompts = ({
  onSelect,
}: Props) => {
  return (
    <Stack
      direction="row"
      spacing={1}
      sx={{
        p: 2,
        flexWrap: "wrap",
      }}
    >
      {prompts.map((prompt) => (
        <Chip
          key={prompt}
          label={prompt}
          clickable
          onClick={() => onSelect(prompt)}
        />
      ))}
    </Stack>
  );
};

export default SuggestedPrompts;