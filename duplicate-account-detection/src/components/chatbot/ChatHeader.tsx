import {
  Box,
  Typography,
} from "@mui/material";
import SmartToyIcon from "@mui/icons-material/SmartToy";

const ChatHeader = () => {
  return (
    <Box
      sx={{
        display: "flex",
        alignItems: "center",
        gap: 1,
        p: 2,
        bgcolor: "primary.main",
        color: "white",
      }}
    >
      <SmartToyIcon />

      <Box>
        <Typography fontWeight={600}>
          IdentityAI Copilot
        </Typography>

        <Typography variant="caption">
          AI Assistant for IAM
        </Typography>
      </Box>
    </Box>
  );
};

export default ChatHeader;