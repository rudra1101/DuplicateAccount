import { useEffect, useMemo, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Checkbox,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  FormControlLabel,
  List,
  ListItemButton,
  ListItemText,
  Paper,
  Stack,
  TextField,
  Typography,
} from "@mui/material";

import { useAuth } from "../../auth/AuthContext";
import {
  createRole,
  getPermissions,
  getRoles,
  updateRolePermissions,
  type PermissionItem,
  type RoleItem,
} from "../../services/roleService";

export default function RoleManagement() {
  const { hasPermission } = useAuth();
  const [roles, setRoles] = useState<RoleItem[]>([]);
  const [permissions, setPermissions] = useState<PermissionItem[]>([]);
  const [selectedRoleId, setSelectedRoleId] = useState<number | null>(null);
  const [selectedPermissions, setSelectedPermissions] = useState<string[]>([]);
  const [error, setError] = useState("");
  const [createOpen, setCreateOpen] = useState(false);
  const [newRoleName, setNewRoleName] = useState("");
  const [newRoleDescription, setNewRoleDescription] = useState("");

  const load = async () => {
    try {
      setError("");
      const [roleData, permissionData] = await Promise.all([getRoles(), getPermissions()]);
      setRoles(roleData);
      setPermissions(permissionData);
      const initial = roleData.find((item) => item.name !== "OWNER") ?? roleData[0];
      if (initial) {
        setSelectedRoleId(initial.id);
        setSelectedPermissions(initial.permissions);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unable to load roles.");
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const selectedRole = roles.find((item) => item.id === selectedRoleId) ?? null;

  const grouped = useMemo(() => {
    const result: Record<string, PermissionItem[]> = {};
    permissions.forEach((permission) => {
      (result[permission.category] ??= []).push(permission);
    });
    return result;
  }, [permissions]);

  const selectRole = (role: RoleItem) => {
    setSelectedRoleId(role.id);
    setSelectedPermissions(role.permissions);
  };

  const togglePermission = (code: string) => {
    setSelectedPermissions((current) =>
      current.includes(code)
        ? current.filter((item) => item !== code)
        : [...current, code],
    );
  };

  const savePermissions = async () => {
    if (!selectedRole) return;
    try {
      const updated = await updateRolePermissions(selectedRole.id, selectedPermissions);
      setRoles((current) => current.map((item) => (item.id === updated.id ? updated : item)));
      setSelectedPermissions(updated.permissions);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unable to save permissions.");
    }
  };

  const submitRole = async () => {
    try {
      const created = await createRole({
        name: newRoleName,
        description: newRoleDescription,
        permissions: [],
      });
      setRoles((current) => [...current, created].sort((a, b) => a.name.localeCompare(b.name)));
      selectRole(created);
      setNewRoleName("");
      setNewRoleDescription("");
      setCreateOpen(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unable to create role.");
    }
  };

  return (
    <Box>
      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
        <Box>
          <Typography variant="h6" fontWeight={700}>Roles & Permissions</Typography>
          <Typography color="text.secondary">
            Configure reusable roles without changing application code.
          </Typography>
        </Box>
        {hasPermission("role.create") && (
          <Button variant="contained" onClick={() => setCreateOpen(true)}>Create Role</Button>
        )}
      </Stack>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      <Stack direction={{ xs: "column", md: "row" }} spacing={2} alignItems="stretch">
        <Paper variant="outlined" sx={{ width: { xs: "100%", md: 280 }, flexShrink: 0 }}>
          <List disablePadding>
            {roles.map((role) => (
              <ListItemButton
                key={role.id}
                selected={role.id === selectedRoleId}
                onClick={() => selectRole(role)}
              >
                <ListItemText
                  primary={role.name}
                  secondary={role.isSystem ? "System role" : "Custom role"}
                />
              </ListItemButton>
            ))}
          </List>
        </Paper>

        <Paper variant="outlined" sx={{ flex: 1, p: 3 }}>
          {!selectedRole ? (
            <Typography color="text.secondary">Select a role.</Typography>
          ) : (
            <>
              <Typography variant="h6" fontWeight={700}>{selectedRole.name}</Typography>
              <Typography color="text.secondary" sx={{ mb: 2 }}>{selectedRole.description}</Typography>
              <Divider sx={{ mb: 2 }} />

              {selectedRole.name === "OWNER" ? (
                <Alert severity="info">OWNER always has unrestricted access and cannot have permissions removed.</Alert>
              ) : (
                <Stack spacing={3}>
                  {Object.entries(grouped).map(([category, items]) => (
                    <Box key={category}>
                      <Typography fontWeight={700} sx={{ mb: 1 }}>{category}</Typography>
                      <Stack>
                        {items.map((permission) => (
                          <FormControlLabel
                            key={permission.code}
                            control={
                              <Checkbox
                                checked={selectedPermissions.includes(permission.code)}
                                onChange={() => togglePermission(permission.code)}
                                disabled={!hasPermission("role.manage_permissions")}
                              />
                            }
                            label={`${permission.name} (${permission.code})`}
                          />
                        ))}
                      </Stack>
                    </Box>
                  ))}

                  {hasPermission("role.manage_permissions") && (
                    <Box>
                      <Button variant="contained" onClick={savePermissions}>Save Permissions</Button>
                    </Box>
                  )}
                </Stack>
              )}
            </>
          )}
        </Paper>
      </Stack>

      <Dialog open={createOpen} onClose={() => setCreateOpen(false)} fullWidth maxWidth="sm">
        <DialogTitle>Create Role</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            <TextField label="Role name" value={newRoleName} onChange={(e) => setNewRoleName(e.target.value)} />
            <TextField label="Description" multiline minRows={3} value={newRoleDescription} onChange={(e) => setNewRoleDescription(e.target.value)} />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCreateOpen(false)}>Cancel</Button>
          <Button variant="contained" onClick={submitRole} disabled={!newRoleName.trim()}>Create</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
