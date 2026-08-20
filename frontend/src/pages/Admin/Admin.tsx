import { Box, Paper, Stack, Tab, Tabs, Typography } from "@mui/material";
import { useState } from "react";

import { useAuth } from "../../auth/AuthContext";
import RoleManagement from "./RoleManagement";
import UserManagement from "./UserManagement";

export default function Admin() {
  const { hasPermission } = useAuth();
  const canUsers = hasPermission("user.view");
  const canRoles = hasPermission("role.view");
  const [tab, setTab] = useState(canUsers ? "users" : "roles");

  return (
    <Box>
      <Stack spacing={0.5} sx={{ mb: 3 }}>
        <Typography variant="h5" fontWeight={700}>Administration</Typography>
        <Typography color="text.secondary">
          Manage application users, roles, and privileges.
        </Typography>
      </Stack>

      <Paper variant="outlined" sx={{ mb: 3 }}>
        <Tabs value={tab} onChange={(_, value) => setTab(value)}>
          {canUsers && <Tab value="users" label="Users" />}
          {canRoles && <Tab value="roles" label="Roles & Permissions" />}
        </Tabs>
      </Paper>

      {tab === "users" && canUsers && <UserManagement />}
      {tab === "roles" && canRoles && <RoleManagement />}
    </Box>
  );
}
