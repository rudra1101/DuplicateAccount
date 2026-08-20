import { useEffect, useState } from "react";
import {
  Alert, Box, Button, Dialog, DialogActions, DialogContent, DialogTitle,
  MenuItem, Paper, Stack, Table, TableBody, TableCell, TableHead, TableRow,
  TextField, Typography
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import type { AuthUser, UserRole } from "../../auth/types";
import { createUser, getUsers } from "../../services/userService";

const blank = {
  username: "", email: "", fullName: "", password: "", role: "USER" as UserRole
};

export default function UserManagement() {
  const [users, setUsers] = useState<AuthUser[]>([]);
  const [form, setForm] = useState(blank);
  const [open, setOpen] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    getUsers().then(setUsers).catch(e => setError(e.message));
  }, []);

  const submit = async () => {
    try {
      setError("");
      const user = await createUser(form);
      setUsers(current => [...current, user]);
      setForm(blank);
      setOpen(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unable to create user.");
    }
  };

  return (
    <Box>
      <Stack direction="row" justifyContent="space-between" sx={{ mb: 3 }}>
        <Box>
          <Typography variant="h5" fontWeight={700}>User Management</Typography>
          <Typography color="text.secondary">Create USER and ADMIN accounts.</Typography>
        </Box>
        <Button variant="contained" startIcon={<AddIcon />} onClick={() => setOpen(true)}>
          Create Account
        </Button>
      </Stack>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      <Paper variant="outlined">
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Username</TableCell><TableCell>Name</TableCell>
              <TableCell>Email</TableCell><TableCell>Role</TableCell><TableCell>Status</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {users.map(user => (
              <TableRow key={user.id}>
                <TableCell>{user.username}</TableCell>
                <TableCell>{user.fullName}</TableCell>
                <TableCell>{user.email}</TableCell>
                <TableCell>{user.role}</TableCell>
                <TableCell>{user.isActive ? "Active" : "Disabled"}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Paper>

      <Dialog open={open} onClose={() => setOpen(false)} fullWidth maxWidth="sm">
        <DialogTitle>Create Account</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            <TextField label="Username" value={form.username} onChange={e => setForm({...form, username:e.target.value})} />
            <TextField label="Full name" value={form.fullName} onChange={e => setForm({...form, fullName:e.target.value})} />
            <TextField label="Email" value={form.email} onChange={e => setForm({...form, email:e.target.value})} />
            <TextField label="Temporary password" type="password" value={form.password} onChange={e => setForm({...form, password:e.target.value})} helperText="Minimum 12 characters" />
            <TextField select label="Role" value={form.role} onChange={e => setForm({...form, role:e.target.value as UserRole})}>
              <MenuItem value="USER">USER</MenuItem>
              <MenuItem value="ADMIN">ADMIN</MenuItem>
            </TextField>
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpen(false)}>Cancel</Button>
          <Button variant="contained" onClick={submit}>Create</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
