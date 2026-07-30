import {
    Box,
    Paper,
    Typography,
} from "@mui/material";

interface Props {
    message: string;
    role: "user" | "assistant";
}

const MessageBubble = ({
    message,
    role,
}: Props) => {

    const isUser = role === "user";

    return (
        <Box
            display="flex"
            justifyContent={
                isUser
                    ? "flex-end"
                    : "flex-start"
            }
            mb={2}
        >
            <Paper
                sx={{
                    p: 2,
                    maxWidth: "80%",
                    bgcolor: isUser
                        ? "#1976d2"
                        : "#f5f5f5",
                    color: isUser
                        ? "white"
                        : "black",
                    borderRadius: 3,
                }}
            >
                <Typography
                    variant="body2"
                    whiteSpace="pre-line"
                >
                    {message}
                </Typography>
            </Paper>
        </Box>
    );
};

export default MessageBubble;