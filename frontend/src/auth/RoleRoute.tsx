import { Navigate, Outlet } from "react-router-dom";

import { useAuth } from "./AuthContext";
import type { UserRole } from "./types";

export default function RoleRoute({ roles }: { roles: UserRole[] }) {
  const { user } = useAuth();

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (!roles.includes(user.role)) {
    return <Navigate to="/" replace />;
  }

  return <Outlet />;
}
