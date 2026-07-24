import { useState } from "react";
import {
  Fab,
  Tooltip,
} from "@mui/material";
import SmartToyIcon from "@mui/icons-material/SmartToy";

import ChatBot from "./ChatBot";

const FloatingChat = () => {
  const [open, setOpen] = useState(false);

  return (
    <>
      <Tooltip title="IdentityAI Copilot">
        <Fab
          color="primary"
          sx={{
            position: "fixed",
            bottom: 25,
            right: 25,
          }}
          onClick={() => setOpen(true)}
        >
          <SmartToyIcon />
        </Fab>
      </Tooltip>

      <ChatBot
        open={open}
        onClose={() => setOpen(false)}
      />
    </>
  );
};

export default FloatingChat;