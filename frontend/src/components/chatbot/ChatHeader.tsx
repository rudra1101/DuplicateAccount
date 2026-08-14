import {
  Box,
  IconButton,
  Tooltip,
  Typography,
} from "@mui/material";

import SupportAgentIcon
  from "@mui/icons-material/SupportAgent";
import AddCommentOutlinedIcon
  from "@mui/icons-material/AddCommentOutlined";
import HistoryOutlinedIcon
  from "@mui/icons-material/HistoryOutlined";
import ChatBubbleOutlineOutlinedIcon
  from "@mui/icons-material/ChatBubbleOutlineOutlined";
import CloseIcon
  from "@mui/icons-material/Close";

interface Props {
  historyOpen: boolean;
  disabled?: boolean;
  onNewChat: () => void;
  onToggleHistory: () => void;
  onClose: () => void;
}

const ChatHeader = ({
  historyOpen,
  disabled = false,
  onNewChat,
  onToggleHistory,
  onClose,
}: Props) => {
  return (
    <Box
      sx={{
        display: "flex",
        alignItems: "center",
        gap: 1.25,

        px: 2,
        py: 1.5,

        bgcolor: "primary.main",
        color: "common.white",

        flexShrink: 0,

        boxShadow:
          "0 2px 10px rgba(0, 0, 0, 0.12)",
      }}
    >
      <Box
        sx={{
          width: 38,
          height: 38,

          borderRadius: "50%",

          display: "flex",
          alignItems: "center",
          justifyContent: "center",

          bgcolor:
            "rgba(255,255,255,0.15)",

          flexShrink: 0,
        }}
      >
        <SupportAgentIcon
          fontSize="small"
        />
      </Box>

      <Box
        sx={{
          flex: 1,
          minWidth: 0,
        }}
      >
        <Typography
          fontWeight={700}
          noWrap
          sx={{
            lineHeight: 1.2,
          }}
        >
          Ask Rudrix
        </Typography>

        <Typography
          variant="caption"
          noWrap
          sx={{
            opacity: 0.9,
          }}
        >
          IdentityAI Assistant
        </Typography>
      </Box>

      <Tooltip title="New chat">
        <span>
          <IconButton
            size="small"
            color="inherit"
            onClick={onNewChat}
            disabled={disabled}
            sx={{
              bgcolor:
                "rgba(255,255,255,0.08)",

              "&:hover": {
                bgcolor:
                  "rgba(255,255,255,0.16)",
              },
            }}
          >
            <AddCommentOutlinedIcon
              fontSize="small"
            />
          </IconButton>
        </span>
      </Tooltip>

      <Tooltip
        title={
          historyOpen
            ? "Back to chat"
            : "Chat history"
        }
      >
        <span>
          <IconButton
            size="small"
            color="inherit"
            onClick={onToggleHistory}
            disabled={disabled}
            sx={{
              bgcolor:
                "rgba(255,255,255,0.08)",

              "&:hover": {
                bgcolor:
                  "rgba(255,255,255,0.16)",
              },
            }}
          >
            {historyOpen
              ? (
                <ChatBubbleOutlineOutlinedIcon
                  fontSize="small"
                />
              )
              : (
                <HistoryOutlinedIcon
                  fontSize="small"
                />
              )}
          </IconButton>
        </span>
      </Tooltip>

      <Tooltip title="Close">
        <span>
          <IconButton
            size="small"
            color="inherit"
            onClick={onClose}
            disabled={disabled}
            sx={{
              bgcolor:
                "rgba(255,255,255,0.08)",

              "&:hover": {
                bgcolor:
                  "rgba(255,255,255,0.16)",
              },
            }}
          >
            <CloseIcon
              fontSize="small"
            />
          </IconButton>
        </span>
      </Tooltip>
    </Box>
  );
};

export default ChatHeader;