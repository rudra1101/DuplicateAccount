import { useEffect, useState } from "react";
import AddIcon from "@mui/icons-material/Add";
import {
  Alert,
  Box,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  MenuItem,
  Paper,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from "@mui/material";

import type { AuthUser } from "../../auth/types";
import { useAuth } from "../../auth/AuthContext";
import { getRoles, type RoleItem } from "../../services/roleService";
import { createUser, getUsers, updateUserRole } from "../../services/userService";

const emptyForm = {
  username: "",
  email: "",
  fullName: "",
  password: "",
  role: "USER",
};

export default function UserManagement() {
  const { user: currentUser, hasPermission } = useAuth();
  const [users, setUsers] = useState<AuthUser[]>([]);
  const [roles, setRoles] = useState<RoleItem[]>([]);
  const [form, setForm] = useState(emptyForm);
  const [open, setOpen] = useState(false);
  const [error, setError] = useState("");

  const load = async () => {
    try {
      setError("");
      const [userData, roleData] = await Promise.all([
        getUsers(),
        hasPermission("role.view") ? getRoles() : Promise.resolve([]),
      ]);
      setUsers(userData);
      setRoles(roleData);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Unable to load users.");
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const availableRoles = roles.length
    ? roles.filter((role) => role.name !== "OWNER" || currentUser?.role === "OWNER")
    : [
        { id: 1, name: "ADMIN", description: "", isSystem: true, permissions: [] },
        { id: 2, name: "USER", description: "", isSystem: true, permissions: [] },
      ];

  const handleCreate = async () => {
    try {
      setError("");
      const created = await createUser(form);
      setUsers((current) => [...current, created].sort((a, b) => a.username.localeCompare(b.username)));
      setForm(emptyForm);
      setOpen(false);
    } catch (createError) {
      setError(createError instanceof Error ? createError.message : "Unable to create user.");
    }
  };

  const handleRoleChange = async (target: AuthUser, role: string) => {
    try {
      const updated = await updateUserRole(target.id, role);
      setUsers((current) => current.map((item) => (item.id === updated.id ? updated : item)));
    } catch (roleError) {
      setError(roleError instanceof Error ? roleError.message : "Unable to update role.");
    }
  };

  return (
    <Box>
      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 3 }}>
        <Box>
          <Typography variant="h6" fontWeight={700}>Users</Typography>
          <Typography color="text.secondary">Create accounts and assign configured roles.</Typography>
        </Box>
        {hasPermission("user.create") && (
          <Button variant="contained" startIcon={<AddIcon />} onClick={() => setOpen(true)}>
            Create Account
          </Button>
        )}
      </Stack>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      <Paper variant="outlined">
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Username</TableCell>
              <TableCell>Name</TableCell>
              <TableCell>Email</TableCell>
              <TableCell>Role</TableCell>
              <TableCell>Status</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {users.map((item) => (
              <TableRow key={item.id}>
                <TableCell>{item.username}</TableCell>
                <TableCell>{item.fullName}</TableCell>
                <TableCell>{item.email}</TableCell>
                <TableCell>
                  {hasPermission("user.assign_role") ? (
                    <TextField
                      select
                      size="small"
                      value={item.role}
                      onChange={(event) => void handleRoleChange(item, event.target.value)}
                      disabled={item.role === "OWNER" && currentUser?.role !== "OWNER"}
                      sx={{ minWidth: 150 }}
                    >
                      {availableRoles.map((role) => (
                        <MenuItem key={role.name} value={role.name}>{role.name}</MenuItem>
                      ))}
                    </TextField>
                  ) : item.role}
                </TableCell>
                <TableCell>{item.isActive ? "Active" : "Disabled"}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Paper>

      <Dialog open={open} onClose={() => setOpen(false)} fullWidth maxWidth="sm">
        <DialogTitle>Create Account</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            <TextField label="Username" value={form.username} onChange={(event) => setForm({ ...form, username: event.target.value })} required />
            <TextField label="Full name" value={form.fullName} onChange={(event) => setForm({ ...form, fullName: event.target.value })} required />
            <TextField label="Email" type="email" value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} required />
            <TextField label="Temporary password" type="password" value={form.password} onChange={(event) => setForm({ ...form, password: event.target.value })} helperText="Minimum 12 characters" required />
            <TextField select label="Role" value={form.role} onChange={(event) => setForm({ ...form, role: event.target.value })}>
              {availableRoles.map((role) => (
                <MenuItem key={role.name} value={role.name}>{role.name}</MenuItem>
              ))}
            </TextField>
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpen(false)}>Cancel</Button>
          <Button
            variant="contained"
            onClick={handleCreate}
            disabled={!form.username.trim() || !form.fullName.trim() || !form.email.trim() || form.password.length < 12}
          >
            Create
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
