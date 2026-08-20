import LogoutIcon from "@mui/icons-material/Logout";
import {
  AppBar,
  Box,
  Button,
  Chip,
  Stack,
  Toolbar,
  Typography,
} from "@mui/material";
import { useNavigate } from "react-router-dom";

import { useAuth } from "../../auth/AuthContext";

const Header = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate("/login", { replace: true });
  };

  return (
    <AppBar
      position="sticky"
      elevation={0}
      sx={{
        zIndex: (theme) => theme.zIndex.drawer + 1,
        backgroundColor: "#0f172a",
        color: "#FFFFFF",
        borderBottom: "1px solid #1e293b",
      }}
    >
      <Toolbar
        sx={{
          minHeight: { xs: 64, sm: 70 },
          gap: 2,
          px: { xs: 2, md: 3 },
        }}
      >
        <Box
          component="img"
          src="/nusummit-logo.svg"
          alt="NuSummit Cybersecurity"
          sx={{
            height: { xs: 38, sm: 44 },
            width: "auto",
            maxWidth: { xs: 190, sm: 240 },
            objectFit: "contain",
          }}
        />

        <Box sx={{ flex: 1 }} />

        {user && (
          <Stack direction="row" spacing={1.5} alignItems="center">
            <Box sx={{ textAlign: "right", display: { xs: "none", sm: "block" } }}>
              <Typography variant="body2" fontWeight={700} sx={{ color: "#FFFFFF" }}>
                {user.fullName}
              </Typography>
              <Typography variant="caption" sx={{ color: "#94a3b8" }}>
                {user.username}
              </Typography>
            </Box>

            <Chip
              size="small"
              label={user.role}
              variant="outlined"
              sx={{
                color: "#FFFFFF",
                borderColor: "#64748b",
                backgroundColor: "rgba(255,255,255,0.04)",
                fontWeight: 700,
              }}
            />

            <Button
              color="inherit"
              startIcon={<LogoutIcon />}
              onClick={handleLogout}
              sx={{
                textTransform: "none",
                color: "#FFFFFF",
                borderRadius: 2,
                px: 1.5,
                "&:hover": {
                  backgroundColor: "#1e293b",
                },
              }}
            >
              Logout
            </Button>
          </Stack>
        )}
      </Toolbar>
    </AppBar>
  );
};

export default Header;
