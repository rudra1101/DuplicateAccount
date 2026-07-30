import DashboardIcon from "@mui/icons-material/Dashboard";
import SearchIcon from "@mui/icons-material/Search";
import AssessmentIcon from "@mui/icons-material/Assessment";
import AdminPanelSettingsIcon from "@mui/icons-material/AdminPanelSettings";
import SettingsIcon from "@mui/icons-material/Settings";
import { SvgIconComponent } from "@mui/icons-material";

export interface NavigationItem {
  id: number;
  title: string;
  path: string;
  icon: SvgIconComponent;
}

export const navigationItems: NavigationItem[] = [
  {
    id: 1,
    title: "Dashboard",
    path: "/",
    icon: DashboardIcon,
  },
  {
    id: 2,
    title: "Duplicate Detection",
    path: "/duplicates",
    icon: SearchIcon,
  },
  {
    id: 3,
    title: "Reports",
    path: "/reports",
    icon: AssessmentIcon,
  },
  {
    id: 4,
    title: "Admin",
    path: "/admin",
    icon: AdminPanelSettingsIcon,
  },
  {
    id: 5,
    title: "Settings",
    path: "/settings",
    icon: SettingsIcon,
  },
];