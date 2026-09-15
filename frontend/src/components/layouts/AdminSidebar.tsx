import AdminPanelSettingsOutlinedIcon from "@mui/icons-material/AdminPanelSettingsOutlined";
import BrandingWatermarkOutlinedIcon from "@mui/icons-material/BrandingWatermarkOutlined";
import HomeOutlinedIcon from "@mui/icons-material/HomeOutlined";
import ManageAccountsOutlinedIcon from "@mui/icons-material/ManageAccountsOutlined";
import SecurityOutlinedIcon from "@mui/icons-material/SecurityOutlined";
import {
  Box,
  Divider,
  Drawer,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Toolbar,
  Typography,
} from "@mui/material";
import { Link, useLocation } from "react-router-dom";

import { useAuth } from "../../auth/AuthContext";

const drawerWidth = 250;

const adminItems = [
  {
    text: "Users",
    path: "/platform-admin/users",
    icon: <ManageAccountsOutlinedIcon />,
    permission: "user.view",
  },
  {
    text: "Roles & Permissions",
    path: "/platform-admin/roles",
    icon: <SecurityOutlinedIcon />,
    permission: "role.view",
  },
  {
    text: "Branding",
    path: "/platform-admin/branding",
    icon: <BrandingWatermarkOutlinedIcon />,
    permission: "settings.manage",
  },
];

export default function AdminSidebar() {
  const location = useLocation();
  const { hasPermission } = useAuth();
  const visibleItems = adminItems.filter((item) => hasPermission(item.permission));

  return (
    <Drawer
      variant="permanent"
      sx={{
        width: drawerWidth,
        flexShrink: 0,
        "& .MuiDrawer-paper": {
          width: drawerWidth,
          boxSizing: "border-box",
          backgroundColor: "var(--identityai-navigation, #0F172A)",
          color: "var(--identityai-navigation-text, #FFFFFF)",
        },
      }}
    >
      <Toolbar>
        <Box
          component={Link}
          to="/home"
          aria-label="Return to IdentityAI home"
          sx={{ color: "inherit", textDecoration: "none", px: 0.5, py: 0.5 }}
        >
          <Typography variant="h6" fontWeight={700}>
            IdentityAI
          </Typography>
          <Typography variant="caption" sx={{ opacity: 0.7 }}>
            Platform Administration
          </Typography>
        </Box>
      </Toolbar>

      <Divider sx={{ borderColor: "rgba(255,255,255,0.12)" }} />

      <Box sx={{ px: 2, pt: 2, pb: 0.5, display: "flex", alignItems: "center", gap: 1 }}>
        <AdminPanelSettingsOutlinedIcon fontSize="small" />
        <Typography variant="overline" fontWeight={800} sx={{ opacity: 0.72, letterSpacing: 1 }}>
          Administration
        </Typography>
      </Box>

      <List sx={{ pt: 1 }}>
        {visibleItems.map((item) => {
          const selected = location.pathname === item.path;
          return (
            <ListItemButton
              key={item.path}
              component={Link}
              to={item.path}
              selected={selected}
              sx={{
                mx: 1,
                mb: 0.5,
                borderRadius: 2,
                "&.Mui-selected": { backgroundColor: "primary.main", color: "primary.contrastText" },
                "&.Mui-selected:hover": { backgroundColor: "primary.dark" },
                "&:hover": { backgroundColor: "rgba(255,255,255,0.08)" },
              }}
            >
              <ListItemIcon sx={{ color: "inherit", minWidth: 40 }}>{item.icon}</ListItemIcon>
              <ListItemText primary={item.text} />
            </ListItemButton>
          );
        })}
      </List>

      <Box sx={{ mt: "auto", p: 1 }}>
        <ListItemButton
          component={Link}
          to="/home"
          sx={{ borderRadius: 2, "&:hover": { backgroundColor: "rgba(255,255,255,0.08)" } }}
        >
          <ListItemIcon sx={{ color: "inherit", minWidth: 40 }}><HomeOutlinedIcon /></ListItemIcon>
          <ListItemText primary="Back to Home" />
        </ListItemButton>
      </Box>
    </Drawer>
  );
}
