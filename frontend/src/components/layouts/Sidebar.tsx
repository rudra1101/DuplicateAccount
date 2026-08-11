import {
  Drawer,
  Toolbar,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Typography,
  Box,
} from "@mui/material";

import DashboardIcon from "@mui/icons-material/Dashboard";
import SearchIcon from "@mui/icons-material/ManageSearch";
import FactCheckIcon from "@mui/icons-material/FactCheck";
import AssessmentIcon from "@mui/icons-material/Assessment";
import AdminPanelSettingsIcon from "@mui/icons-material/AdminPanelSettings";
import SettingsIcon from "@mui/icons-material/Settings";
import CloudUploadIcon from "@mui/icons-material/CloudUpload";
import CableIcon from "@mui/icons-material/Cable";
import MonitorHeartOutlinedIcon from "@mui/icons-material/MonitorHeartOutlined";
import ModelTrainingIcon from "@mui/icons-material/ModelTraining";

import { Link, useLocation } from "react-router-dom";

const drawerWidth = 250;

const menuItems = [
  {
    text: "Dashboard",
    icon: <DashboardIcon />,
    path: "/",
  },
  {
    text: "Duplicate Detection",
    icon: <SearchIcon />,
    path: "/duplicates",
  },
  {
    text: "Review Queue",
    icon: <FactCheckIcon />,
    path: "/review",
  },
  {
    text: "Reports",
    icon: <AssessmentIcon />,
    path: "/reports",
  },
  {
    text: "Admin",
    icon: <AdminPanelSettingsIcon />,
    path: "/admin",
  },
  {
    text: "Upload Accounts",
    icon: <CloudUploadIcon />,
    path: "/upload",
  },
  {
    text: "Operations",
    path: "/operations",
    icon: <MonitorHeartOutlinedIcon />,
  },
  {
    text: "Settings",
    icon: <SettingsIcon />,
    path: "/settings",
  },
  {
    text: "Integrations",
    path: "/integrations",
    icon: <CableIcon />,
  },
  {
    text: "ML Training",
    path: "/ml-training",
    icon: <ModelTrainingIcon />,
  },
];

const Sidebar = () => {
  const location = useLocation();

  return (
    <Drawer
      variant="permanent"
      sx={{
        width: drawerWidth,
        flexShrink: 0,

        "& .MuiDrawer-paper": {
          width: drawerWidth,
          boxSizing: "border-box",
          backgroundColor: "#0f172a",
          color: "#fff",
        },
      }}
    >
      <Toolbar>
        <Box>
          <Typography
            variant="h6"
            sx={{
              fontWeight: 700,
              color: "#fff",
            }}
          >
            IdentityAI
          </Typography>

          <Typography
            variant="caption"
            sx={{
              color: "#94a3b8",
            }}
          >
            Duplicate Detection Platform
          </Typography>
        </Box>
      </Toolbar>

      <List sx={{ mt: 2 }}>
        {menuItems.map((item) => (
          <ListItemButton
            key={item.text}
            component={Link}
            to={item.path}
            selected={location.pathname === item.path}
            sx={{
              mx: 1,
              borderRadius: 2,
              mb: 0.5,

              "&.Mui-selected": {
                backgroundColor: "#1976d2",
              },

              "&.Mui-selected:hover": {
                backgroundColor: "#1565c0",
              },

              "&:hover": {
                backgroundColor: "#1e293b",
              },
            }}
          >
            <ListItemIcon
              sx={{
                color: "inherit",
                minWidth: 40,
              }}
            >
              {item.icon}
            </ListItemIcon>

            <ListItemText primary={item.text} />
          </ListItemButton>
        ))}
      </List>
    </Drawer>
  );
};

export default Sidebar;
