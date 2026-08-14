import { useState } from "react";

import {
  Fab,
} from "@mui/material";

import SupportAgentIcon
  from "@mui/icons-material/SupportAgent";

import ChatBot from "./ChatBot";

const FloatingChat = () => {
  const [
    open,
    setOpen,
  ] = useState(false);

  return (
    <>
      {!open && (
        <Fab
          variant="extended"
          color="primary"
          onClick={() =>
            setOpen(true)
          }
          sx={{
            position: "fixed",
            bottom: 24,
            right: 24,

            px: 2.5,
            gap: 1,

            minHeight: 48,

            textTransform: "none",
            fontWeight: 700,
            fontSize: 14,

            borderRadius: 999,

            zIndex: (theme) =>
              theme.zIndex.drawer + 1,

            boxShadow:
              "0 8px 24px rgba(25, 118, 210, 0.28)",

            "&:hover": {
              boxShadow:
                "0 10px 28px rgba(25, 118, 210, 0.36)",
              transform:
                "translateY(-1px)",
            },

            transition:
              "all 0.2s ease",
          }}
        >
          <SupportAgentIcon />

          Ask Rudrix
        </Fab>
      )}

      <ChatBot
        open={open}
        onClose={() =>
          setOpen(false)
        }
      />
    </>
  );
};

export default FloatingChat;