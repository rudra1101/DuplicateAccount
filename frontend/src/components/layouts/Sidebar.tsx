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
import TaskAltIcon from "@mui/icons-material/TaskAlt";
import AssessmentIcon from "@mui/icons-material/Assessment";
import AdminPanelSettingsIcon from "@mui/icons-material/AdminPanelSettings";
import SettingsIcon from "@mui/icons-material/Settings";
import CloudUploadIcon from "@mui/icons-material/CloudUpload";
import CableIcon from "@mui/icons-material/Cable";
import ManageAccountsIcon from "@mui/icons-material/ManageAccounts";
import MonitorHeartOutlinedIcon from "@mui/icons-material/MonitorHeartOutlined";
import ModelTrainingIcon from "@mui/icons-material/ModelTraining";
import AnalyticsOutlinedIcon from "@mui/icons-material/AnalyticsOutlined";
import { MenuBookOutlined } from "@mui/icons-material";

import { Link, useLocation } from "react-router-dom";
import { useAuth } from "../../auth/AuthContext";

const drawerWidth = 250;
const ACCOUNT_INTELLIGENCE_PERMISSION = "domain.account_intelligence.view";

const menuItems = [
  {
    text: "Dashboard",
    icon: <DashboardIcon />,
    path: "/account-intelligence/dashboard",
    permissions: ["dashboard.view"],
    domainPermission: ACCOUNT_INTELLIGENCE_PERMISSION,
  },
  {
    text: "Duplicate Detection",
    icon: <SearchIcon />,
    path: "/account-intelligence/duplicates",
    permissions: ["duplicate.view"],
    domainPermission: ACCOUNT_INTELLIGENCE_PERMISSION,
  },
  {
    text: "Review Accounts",
    icon: <FactCheckIcon />,
    path: "/account-intelligence/review",
    permissions: ["duplicate.review"],
    domainPermission: ACCOUNT_INTELLIGENCE_PERMISSION,
  },
  {
    text: "Remediation",
    icon: <TaskAltIcon />,
    path: "/account-intelligence/remediation",
    permissions: ["remediation.view", "remediation.history.view"],
    domainPermission: ACCOUNT_INTELLIGENCE_PERMISSION,
  },
  {
    text: "Reports",
    icon: <AssessmentIcon />,
    path: "/account-intelligence/reports",
    permissions: ["report.view"],
    domainPermission: ACCOUNT_INTELLIGENCE_PERMISSION,
  },
  {
    text: "Upload Accounts",
    icon: <CloudUploadIcon />,
    path: "/account-intelligence/upload",
    permissions: ["upload.manage"],
    domainPermission: ACCOUNT_INTELLIGENCE_PERMISSION,
  },
  {
    text: "Integrations",
    path: "/account-intelligence/integrations",
    icon: <CableIcon />,
    permissions: ["integration.view"],
    domainPermission: ACCOUNT_INTELLIGENCE_PERMISSION,
  },
  {
    text: "Accounts",
    path: "/account-intelligence/accounts",
    icon: <ManageAccountsIcon />,
    permissions: ["integration.view"],
    domainPermission: ACCOUNT_INTELLIGENCE_PERMISSION,
  },
  { text: "Admin", icon: <AdminPanelSettingsIcon />, path: "/admin", permissions: ["user.view", "role.view"] },
  { text: "Operations", path: "/operations", icon: <MonitorHeartOutlinedIcon />, permissions: ["operations.view"] },
  { text: "Settings", icon: <SettingsIcon />, path: "/settings", permissions: ["settings.manage"] },
  { text: "ML Training", path: "/ml-training", icon: <ModelTrainingIcon />, permissions: ["ml.view"] },
  { text: "Model Evaluation", path: "/ml-evaluation", icon: <AnalyticsOutlinedIcon />, permissions: ["ml.analytics.view", "ml.calibration.view"] },
  { text: "Knowledge Base", path: "/knowledge", icon: <MenuBookOutlined />, permissions: ["knowledge.view"] },
];

const Sidebar = () => {
  const location = useLocation();
  const { hasPermission } = useAuth();

  const visibleItems = menuItems.filter((item) => {
    if (item.domainPermission && !hasPermission(item.domainPermission)) {
      return false;
    }
    return item.permissions.some((permission) => hasPermission(permission));
  });

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
        <Box
          component={Link}
          to="/home"
          aria-label="Return to IdentityAI home"
          sx={{
            display: "block",
            color: "inherit",
            textDecoration: "none",
            borderRadius: 1.5,
            px: 0.5,
            py: 0.5,
            "&:hover": { opacity: 0.9 },
          }}
        >
          <Typography variant="h6" sx={{ fontWeight: 700, color: "#fff" }}>
            IdentityAI
          </Typography>
          <Typography variant="caption" sx={{ color: "#94a3b8" }}>
            Account Intelligence Platform
          </Typography>
        </Box>
      </Toolbar>

      <List sx={{ mt: 2 }}>
        {visibleItems.map((item) => (
          <ListItemButton
            key={item.text}
            component={Link}
            to={item.path}
            selected={
              location.pathname === item.path ||
              location.pathname.startsWith(`${item.path}/`)
            }
            sx={{
              mx: 1,
              borderRadius: 2,
              mb: 0.5,
              "&.Mui-selected": { backgroundColor: "#1976d2" },
              "&.Mui-selected:hover": { backgroundColor: "#1565c0" },
              "&:hover": { backgroundColor: "#1e293b" },
            }}
          >
            <ListItemIcon sx={{ color: "inherit", minWidth: 40 }}>
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
