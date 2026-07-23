import { Box, Typography } from "@mui/material";
import { ReactNode } from "react";

interface PageContainerProps {
    title: string;
    subtitle?: string;
    children: ReactNode;
}

const PageContainer = ({
    title,
    subtitle,
    children,
}: PageContainerProps) => {
    return (
        <Box
            sx={{
                p: 4,
                minHeight: "calc(100vh - 64px)",
                bgcolor: "#f5f7fb",
            }}
        >
            <Typography
                variant="h4"
                sx={{
                    fontWeight: 700,
                    mb: 4,
                }}
            >
                {title}
            </Typography>

            {subtitle && (
                <Typography
                    variant="body1"
                    color="text.secondary"
                    sx={{ mb: 4 }}
                >
                    {subtitle}
                </Typography>
            )}

            {children}
        </Box>
    );
};

export default PageContainer;