import {
  useState,
} from "react";

import {
  Box,
  IconButton,
  TextField,
} from "@mui/material";

import SendIcon from "@mui/icons-material/Send";

interface Props {
  onSend: (
    message: string,
  ) => void | Promise<void>;

  disabled?: boolean;
}

const ChatInput = ({
  onSend,
  disabled = false,
}: Props) => {
  const [
    message,
    setMessage,
  ] = useState("");

  const handleSend = async () => {
    const normalizedMessage =
      message.trim();

    if (
      !normalizedMessage
      || disabled
    ) {
      return;
    }

    setMessage("");

    await onSend(
      normalizedMessage,
    );
  };

  return (
    <Box
      sx={{
        display: "flex",
        alignItems: "flex-end",
        gap: 1,
        p: 2,
        borderTop: 1,
        borderColor: "divider",
        backgroundColor:
          "background.paper",
      }}
    >
      <TextField
        fullWidth
        multiline
        maxRows={5}
        size="small"
        placeholder={
          disabled
            ? "Rudrix is responding..."
            : "Ask Rudrix..."
        }
        value={message}
        disabled={disabled}
        onChange={(event) =>
          setMessage(
            event.target.value,
          )
        }
        onKeyDown={(event) => {
          if (
            event.key === "Enter"
            && !event.shiftKey
          ) {
            event.preventDefault();

            void handleSend();
          }
        }}
      />

      <IconButton
        color="primary"
        disabled={
          disabled
          || !message.trim()
        }
        onClick={() => {
          void handleSend();
        }}
        aria-label="Send message"
      >
        <SendIcon />
      </IconButton>
    </Box>
  );
};

export default ChatInput;