import SmartToyIcon from "@mui/icons-material/SmartToy";
import { Fab, Tooltip } from "@mui/material";

const FloatingChat = () => {
  return (
    <Tooltip title="AI Assistant">
      <Fab
        color="primary"
        sx={{
          position: "fixed",
          bottom: 30,
          right: 30,
          zIndex: 9999,
        }}
      >
        <SmartToyIcon />
      </Fab>
    </Tooltip>
  );
};

export default FloatingChat;