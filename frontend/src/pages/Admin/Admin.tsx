import { Box, Paper, Stack, Tab, Tabs, Typography } from "@mui/material";
import { useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import { useAuth } from "../../auth/AuthContext";
import BrandingSettings from "./BrandingSettings";
import RoleManagement from "./RoleManagement";
import UserManagement from "./UserManagement";

type AdminTab = "users" | "roles" | "branding";

export default function Admin() {
  const { hasPermission } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const canUsers = hasPermission("user.view");
  const canRoles = hasPermission("role.view");
  const canBranding = hasPermission("settings.manage");

  const allowedTabs = useMemo<AdminTab[]>(() => {
    const tabs: AdminTab[] = [];
    if (canUsers) tabs.push("users");
    if (canRoles) tabs.push("roles");
    if (canBranding) tabs.push("branding");
    return tabs;
  }, [canUsers, canRoles, canBranding]);

  const routeTab = location.pathname.split("/").filter(Boolean).at(-1) as AdminTab | undefined;
  const defaultTab = allowedTabs.includes(routeTab as AdminTab)
    ? (routeTab as AdminTab)
    : allowedTabs[0] ?? "users";
  const [tab, setTab] = useState<AdminTab>(defaultTab);

  useEffect(() => {
    if (routeTab && allowedTabs.includes(routeTab)) {
      setTab(routeTab);
    } else if (!allowedTabs.includes(tab) && allowedTabs[0]) {
      setTab(allowedTabs[0]);
    }
  }, [allowedTabs, routeTab, tab]);

  const handleTabChange = (_event: React.SyntheticEvent, value: AdminTab) => {
    setTab(value);
    navigate(`/platform-admin/${value}`);
  };

  return (
    <Box>
      <Stack spacing={0.5} sx={{ mb: 3 }}>
        <Typography variant="h5" fontWeight={700}>Platform Administration</Typography>
        <Typography color="text.secondary">
          Manage IdentityAI users, roles, permissions, and global branding.
        </Typography>
      </Stack>

      <Paper variant="outlined" sx={{ mb: 3 }}>
        <Tabs value={tab} onChange={handleTabChange} variant="scrollable" scrollButtons="auto">
          {canUsers && <Tab value="users" label="Users" />}
          {canRoles && <Tab value="roles" label="Roles & Permissions" />}
          {canBranding && <Tab value="branding" label="Branding" />}
        </Tabs>
      </Paper>

      {tab === "users" && canUsers && <UserManagement />}
      {tab === "roles" && canRoles && <RoleManagement />}
      {tab === "branding" && canBranding && <BrandingSettings />}
    </Box>
  );
}
