import { AppBar, Toolbar, Typography } from "@mui/material";

const Header = () => {
    return (
        <AppBar
            position="static"
            elevation={0}
            sx={{
                backgroundColor: "#ffffff",
                color: "#333",
                borderBottom: "1px solid #e0e0e0",
            }}
        >
            <Toolbar>
                <Typography
                    variant="h6"
                    sx={{
                        fontWeight: 600,
                    }}
                >
                    Duplicate Account Detection
                </Typography>
            </Toolbar>
        </AppBar>
    );
};

export default Header;