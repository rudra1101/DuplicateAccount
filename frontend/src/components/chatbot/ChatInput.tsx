import { useState } from "react";
import {
  Box,
  TextField,
  IconButton,
} from "@mui/material";
import SendIcon from "@mui/icons-material/Send";

interface Props {
  onSend: (message: string) => void;
}

const ChatInput = ({ onSend }: Props) => {
  const [message, setMessage] = useState("");

  const handleSend = () => {
    if (!message.trim()) return;

    onSend(message);
    setMessage("");
  };

  return (
    <Box
      sx={{
        display: "flex",
        gap: 1,
        p: 2,
        borderTop: "1px solid #e0e0e0",
      }}
    >
      <TextField
        fullWidth
        size="small"
        placeholder="Ask IdentityAI..."
        value={message}
        onChange={(e) => setMessage(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter") {
            handleSend();
          }
        }}
      />

      <IconButton
        color="primary"
        onClick={handleSend}
      >
        <SendIcon />
      </IconButton>
    </Box>
  );
};

export default ChatInput;