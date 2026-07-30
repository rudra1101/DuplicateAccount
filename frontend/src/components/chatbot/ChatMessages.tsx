import { Box } from "@mui/material";
import { ChatMessage } from "../../models/chat";
import MessageBubble from "./MessageBubble";

interface Props {
  messages: ChatMessage[];
}

const ChatMessages = ({
  messages,
}: Props) => {
  return (
    <Box
      sx={{
        flex: 1,
        overflowY: "auto",
        p: 2,
      }}
    >
      {messages.map((msg) => (
        <MessageBubble
          key={msg.id}
          message={msg.content}
          role={msg.role}
        />
      ))}
    </Box>
  );
};

export default ChatMessages;