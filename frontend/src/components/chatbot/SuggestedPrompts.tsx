import {
  Box,
  Chip,
  Typography,
} from "@mui/material";

interface Props {
  onSelect: (
    prompt: string,
  ) => void;
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
    <Box
      sx={{
        px: 2,
        py: 1.4,

        borderBottom: 1,
        borderColor: "divider",

        bgcolor:
          "background.paper",

        flexShrink: 0,
      }}
    >
      <Typography
        variant="caption"
        sx={{
          display: "block",
          mb: 1,

          color:
            "text.secondary",

          fontWeight: 600,
        }}
      >
        Suggested
      </Typography>

      <Box
        sx={{
          display: "flex",
          flexWrap: "wrap",
          gap: 0.75,
        }}
      >
        {prompts.map(
          (prompt) => (
            <Chip
              key={prompt}
              label={prompt}
              size="small"
              clickable
              onClick={() =>
                onSelect(prompt)
              }
              sx={{
                borderRadius: 999,

                bgcolor:
                  "action.hover",

                fontSize: 12,

                "&:hover": {
                  bgcolor:
                    "action.selected",
                },
              }}
            />
          ),
        )}
      </Box>
    </Box>
  );
};

export default SuggestedPrompts;